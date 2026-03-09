from datetime import datetime, date
import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, url_for

from dao.student_dao import (
    create_student,
    generate_student_number,
    search_students,
    update_student,
    list_student_documents,  # 新增导入
    add_student_document,
    update_student_document,
    delete_student_document,
    set_primary_document,
    list_doc_types,
    add_doc_type,
)
from dao.class_dao import list_classes_with_counts
from dao.enrollment_dao import list_classes_for_student
from db import get_db

students_bp = Blueprint("students", __name__)


def _build_birthday_from_form(form):
    y = (form.get("birthday_year") or "").strip()
    m = (form.get("birthday_month") or "").strip()
    d = (form.get("birthday_day") or "").strip()

    if y or m or d:
        if not y or not y.isdigit():
            return None

        try:
            year = int(y)
            month = int(m) if m else 0
            day = int(d) if d else 0
        except ValueError:
            return None

        if month < 0 or month > 12 or day < 0 or day > 31:
            return None

        if month == 0 and day > 0:
            return None

        if month > 0 and day > 0:
            try:
                return date(year, month, day).strftime("%Y-%m-%d")
            except ValueError:
                return None

        return f"{year:04d}-{month:02d}-{day:02d}"

    birthday = (form.get("birthday") or "").strip()
    return birthday or None


def _split_birthday_for_form(birthday_value):
    if not birthday_value:
        return "", "", ""

    parts = birthday_value.split("-")
    if len(parts) != 3:
        return "", "", ""

    year, month, day = (parts[0].strip(), parts[1].strip(), parts[2].strip())
    return year, month, day

@students_bp.route('/students')
def index():
    # 从URL查询参数获取筛选数据
    name_id = request.args.get('name_id','').strip()
    name_nick = request.args.get('name_nick','').strip()
    gender  = request.args.get('gender','').strip()
    class_sel = request.args.get('class_id','').strip()

    # 调用通用查询函数
    with get_db() as conn:
        students = search_students(
            conn,
            legal_name = name_id or None,
            display_name = name_nick or None,
            gender = gender or None,
            class_id = int(class_sel) if class_sel.isdigit() else None,
        )
        # 查询每个学生的主证件
        student_list = []
        for stu in students:
            docs = list_student_documents(conn, stu['id'])
            main_doc = docs[0] if docs else None
            student_list.append({
                **dict(stu),
                'main_doc': main_doc
            })
        # load all classes for dropdown
        classes = list_classes_with_counts(conn)
    filters = {
        'name_id':name_id,
        'name_nick':name_nick,
        'gender':gender,
        'class_id': class_sel,
    }
    return render_template('/students/view_students.html', students=student_list, filters=filters, classes=classes)

@students_bp.route('/students/add',methods=['GET','POST'])
def add_student():
    current_year = datetime.now().year
    if request.method == 'GET':
        return render_template('students/add.html',
                               errors=[],
                               form_data=None,
                               current_year = current_year)
    if request.method == 'POST':
        # 获取表单数据
        # auto_number = request.form.get('auto_number') == 'on'  # 学号默认系统自动生成，
        display_name = request.form.get('display_name', '').strip()
        legal_name = request.form.get('legal_name', '').strip()
        age = request.form.get('age', '').strip()
        try:
            age_val = int(age) if age else None
        except ValueError:
            age_val = None
        doc_type = request.form.get('doc_type', '').strip()
        doc_number = request.form.get('doc_number', '').strip()
        gender = request.form.get('gender', '').strip() or None
        birthday = _build_birthday_from_form(request.form)
        
        # 基础校验
        errors = []
        try:
            with get_db() as conn:
                # 自动生成学号
                student_number = generate_student_number(conn)
                
                # 检查学号是否已存在
                if student_number:
                    existing = search_students(conn, student_number=student_number)
                    if existing:
                        errors.append('学号已存在')
                
                # 其他校验
                if not display_name:
                    errors.append('常用称呼不能为空')
                if not legal_name:
                    errors.append('法定姓名不能为空')
                if age_val is None:
                    errors.append('年龄必须填写且为数字')

                if not birthday and (
                    request.form.get("birthday_year")
                    or request.form.get("birthday_month")
                    or request.form.get("birthday_day")
                ):
                    errors.append("出生日期无效")
                
                if errors:
                    return render_template('students/add.html',current_year=current_year, errors=errors, form_data=request.form)
                
                # 插入学生
                student_id = create_student(
                    conn,
                    student_number=student_number,
                    display_name=display_name,
                    legal_name=legal_name,
                    age=age_val,
                    doc_type=doc_type,
                    doc_number=doc_number,
                    gender=gender,
                    birthday=birthday,
                )
                
                conn.commit()
            
            flash(f'学生添加成功！学号：{student_number}，ID：{student_id}', 'success')
            return redirect(url_for('students.index'))
            
        except sqlite3.IntegrityError as e:
            errors.append(f'数据库错误：{str(e)}')
            return render_template('students/add.html', errors=errors, form_data=request.form)
    
    return render_template('students/add.html', errors=[], form_data=None)

@students_bp.route('/students/edit/<student_number>',methods=['GET','POST'])
def edit_student(student_number):
    current_year = datetime.now().year
    # 保持 POST 行为以兼容旧表单提交，但 GET 直接重定向到新的详情/编辑页
    if request.method == 'GET':
        return redirect(url_for('students.student_detail', student_number=student_number))

    with get_db() as conn:
        student = conn.execute(
            "SELECT * FROM students WHERE student_number = ?",(student_number,)
            ).fetchone()

    if not student:
        return "学员不存在",404

    birthday_year, birthday_month, birthday_day = _split_birthday_for_form(student["birthday"])
    default_form_data = {
        "student_number": student["student_number"],
        "display_name": student["display_name"] or "",
        "legal_name": student["legal_name"] or "",
        "gender": student["gender"] or "",
        "birthday": student["birthday"] or "",
        "birthday_year": birthday_year,
        "birthday_month": birthday_month,
        "birthday_day": birthday_day,
        "doc_type": student["doc_type"] or "",
        "doc_number": student["doc_number"] or "",
    }

    if request.method == 'POST':
        display_name = request.form.get("display_name", "").strip()
        legal_name = request.form.get("legal_name", "").strip()
        gender = request.form.get("gender", "").strip() or None
        birthday = _build_birthday_from_form(request.form)
        doc_type = request.form.get("doc_type", "").strip()
        doc_number = request.form.get("doc_number", "").strip()

        errors = []
        if not display_name:
            errors.append("常用称呼不能为空")
        if not legal_name:
            errors.append("法定姓名不能为空")

        if not birthday and (
            request.form.get("birthday_year")
            or request.form.get("birthday_month")
            or request.form.get("birthday_day")
        ):
            errors.append("出生日期无效")

        if errors:
            return render_template(
                "edit.html",
                student=student,
                errors=errors,
                form_data=request.form,
                current_year=current_year,
            )

        try:
            with get_db() as conn:
                update_student(
                    conn,
                    student_number=student_number,
                    display_name=display_name,
                    legal_name=legal_name,
                    gender=gender,
                    birthday=birthday,
                    doc_type=doc_type,
                    doc_number=doc_number,
                )
                conn.commit()

            flash("学员信息更新成功", "success")
            return redirect(url_for("students.index"))
        except sqlite3.IntegrityError as e:
            return render_template(
                "edit.html",
                student=student,
                errors=[f"数据库错误：{e}"],
                form_data=request.form,
                current_year=current_year,
            )

    # GET 请求：显示编辑表单，雨天当前值
    return render_template(
        'edit.html',
        student=student,
        form_data=default_form_data,
        current_year=current_year,
    )

@students_bp.route('/students/detail/<student_number>', methods=['GET', 'POST'])
def student_detail(student_number):
    current_year = datetime.now().year
    with get_db() as conn:
        student = conn.execute(
            "SELECT * FROM students WHERE student_number = ?", (student_number,)
        ).fetchone()
        if not student:
            return "学员不存在", 404
        documents = list_student_documents(conn, student['id'])
        # also load class enrollment info for display
        student_classes = list_classes_for_student(conn, student['id'])
        # load types for use in page (will refresh after modifications below)
        doc_types = []
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'edit_basic':
                display_name = request.form.get('display_name', '').strip()
                legal_name = request.form.get('legal_name', '').strip()
                gender = request.form.get('gender', '').strip() or None
                birthday = request.form.get('birthday', '').strip() or None
                if display_name and legal_name:
                    update_student(
                        conn,
                        student_number=student_number,
                        display_name=display_name,
                        legal_name=legal_name,
                        gender=gender,
                        birthday=birthday,
                    )
                    conn.commit()
                    # 刷新 student
                    student = conn.execute(
                        "SELECT * FROM students WHERE student_number = ?", (student_number,)
                    ).fetchone()
            elif action == 'add_doc':
                doc_type = request.form.get('doc_type', '').strip()
                doc_number = request.form.get('doc_number', '').strip()
                # new requirement: every new document becomes primary
                is_primary = True
                if doc_type and doc_number:
                    # ensure doc_type exists in doc_types table
                    try:
                        label = doc_type
                        if doc_type.startswith('PASSPORT-'):
                            country = doc_type.split('-',1)[1]
                            label = f'护照-{country}'
                        add_doc_type(conn, doc_type, label)
                    except Exception:
                        pass
                    add_student_document(conn, student['id'], doc_type, doc_number, is_primary)
                    conn.commit()
            elif action == 'delete_doc':
                doc_id = request.form.get('doc_id')
                if doc_id:
                    delete_student_document(conn, int(doc_id))
                    conn.commit()
            elif action == 'set_primary':
                doc_id = request.form.get('doc_id')
                if doc_id:
                    set_primary_document(conn, int(doc_id))
                    conn.commit()
            elif action == 'update_doc':
                doc_id = request.form.get('doc_id')
                doc_type = request.form.get('doc_type','').strip()
                doc_number = request.form.get('doc_number','').strip()
                if doc_id and doc_type and doc_number:
                    try:
                        update_student_document(conn, int(doc_id), doc_type, doc_number, False)
                        conn.commit()
                    except sqlite3.IntegrityError:
                        flash('同类型证件已存在，无法修改', 'error')
            # 操作后刷新数据
            documents = list_student_documents(conn, student['id'])
            # 更新学生班级列表也有必要（虽然添加证件不会影响）
            student_classes = list_classes_for_student(conn, student['id'])
            # 操作后重新读取证件类型
            doc_types = [dict(r) for r in list_doc_types(conn)]
    birthday_year, birthday_month, birthday_day = _split_birthday_for_form(student["birthday"])
    default_form_data = {
        "student_number": student["student_number"],
        "display_name": student["display_name"] or "",
        "legal_name": student["legal_name"] or "",
        "gender": student["gender"] or "",
        "birthday": student["birthday"] or "",
        "birthday_year": birthday_year,
        "birthday_month": birthday_month,
        "birthday_day": birthday_day,
    }
    # ensure types loaded even on GET
    if not doc_types:
        with get_db() as conn2:
            doc_types = [dict(r) for r in list_doc_types(conn2)]
    return render_template(
        "students/detail.html",
        student=student,
        documents=documents,
        student_classes=student_classes,
        doc_types=doc_types,
        form_data=default_form_data,
        current_year=current_year,
    )


