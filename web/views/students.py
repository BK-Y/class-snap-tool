from datetime import datetime, date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from dao.student_sa_dao import (
    create_student,
    generate_student_number,
    search_students,
    update_student,
    list_student_documents,
    add_student_document,
    update_student_document,
    delete_student_document,
    set_primary_document,
    list_doc_types,
    add_doc_type,
)
from dao.class_sa_dao import list_classes_with_counts
from dao.enrollment_sa_dao import list_classes_for_student, enroll_student, remove_student

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
    students = search_students(
        display_name = name_nick or None,
        gender = gender or None,
        class_id = int(class_sel) if class_sel.isdigit() else None,
    )
    student_list = []
    for stu in students:
        docs = list_student_documents(stu.id)
        main_doc = docs[0] if docs else None
        student_list.append({
            'id': stu.id,
            'student_number': stu.student_number,
            'display_name': stu.display_name,
            'gender': stu.gender,
            'birthday': stu.birthday,
            'main_doc': main_doc
        })
    classes = list_classes_with_counts()
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
    if request.method == 'POST':
        from flask import jsonify
        display_name = request.form.get('display_name', '').strip()
        doc_type = request.form.get('doc_type', '').strip()
        doc_number = request.form.get('doc_number', '').strip()
        gender = request.form.get('gender', '').strip() or None
        birthday = _build_birthday_from_form(request.form)
        errors = []
        try:
            student_number = generate_student_number()
            if student_number:
                existing = search_students(student_number=student_number)
                if existing:
                    errors.append('学号已存在')
            if not display_name:
                errors.append('常用称呼和法定姓名至少填写一项')
            if not birthday:
                errors.append('出生日期为必填项')
            if not birthday and (
                request.form.get("birthday_year")
                or request.form.get("birthday_month")
                or request.form.get("birthday_day")
            ):
                errors.append("出生日期无效")
            if errors:
                return jsonify({"success": False, "errors": errors})
            student_id = create_student(
                student_number=student_number,
                display_name=display_name,
                gender=gender,
                birthday=birthday,
            )
            # 添加主证件
            if doc_type and doc_number:
                add_student_document(student_id, doc_type, doc_number, request.form.get('doc_name','').strip() or None, is_primary=True)
            return jsonify({"success": True, "student_id": student_id, "student_number": student_number})
        except Exception as e:
            errors.append(f'数据库错误：{str(e)}')
            return jsonify({"success": False, "errors": errors})
    # GET 请求直接返回 405
    return '', 405


@students_bp.route('/students/detail/<student_number>', methods=['GET', 'POST'])
def student_detail(student_number):
    current_year = datetime.now().year
    student = next(iter(search_students(student_number=student_number)), None)
    if not student:
        return "学员不存在", 404
    documents = list_student_documents(student.id)
    raw_classes = list_classes_for_student(student.id)
    # normalize to dicts for easier templating
    student_classes = []
    for cls, enrolled_at in raw_classes:
        student_classes.append({
            'id': cls.id,
            'type': cls.type,
            'level': cls.level,
            'group_number': cls.group_number,
            'status': cls.status,
            'enrolled_at': enrolled_at.strftime('%Y-%m-%d %H:%M') if enrolled_at else None,
            'teacher': getattr(cls, 'teacher', None),
            'class_time': getattr(cls, 'class_time', None),
            'start_date': getattr(cls, 'start_date', None),
        })
    # for transfer dropdown, also normalize
    raw_all = list_classes_with_counts()
    all_classes = []
    for cls, count in raw_all:
        all_classes.append({
            'id': cls.id,
            'type': cls.type,
            'level': cls.level,
            'group_number': cls.group_number,
            'status': cls.status,
            'student_count': count,
            'teacher': getattr(cls, 'teacher', None),
            'class_time': getattr(cls, 'class_time', None),
            'start_date': getattr(cls, 'start_date', None),
        })
    doc_types = []
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'edit_basic':
            display_name = request.form.get('display_name', '').strip()
            gender = request.form.get('gender', '').strip() or None
            birthday = request.form.get('birthday', '').strip() or None
            if display_name:
                update_student(
                    student_number=student_number,
                    display_name=display_name,
                    gender=gender,
                    birthday=birthday,
                )
            else:
                flash('请填写常用称呼或法定姓名', 'error')
        elif action == 'add_doc':
            doc_type = request.form.get('doc_type', '').strip()
            doc_number = request.form.get('doc_number', '').strip()
            # checkbox 值为 "on" 时表示勾选
            is_primary = request.form.get('is_primary') == 'on'
            docs = list_student_documents(student.id)
            # first document for this student should always be primary
            if not docs:
                is_primary = True
            else:
                # if a primary already exists, ignore any attempt to set another one
                if any(d.is_primary for d in docs):
                    is_primary = False
            if doc_type and doc_number:
                # prevent duplicate type
                existing = [d for d in docs if d.doc_type == doc_type]
                if existing:
                    flash('该类型证件已存在，无法添加', 'error')
                else:
                    try:
                        label = doc_type
                        if doc_type.startswith('PASSPORT-'):
                            country = doc_type.split('-',1)[1]
                            label = f'护照-{country}'
                        add_doc_type(doc_type, label)
                    except Exception:
                        pass
                    add_student_document(
                        student.id,
                        doc_type,
                        doc_number,
                        request.form.get('doc_name','').strip() or None,
                        is_primary
                    )
        elif action == 'delete_doc':
            doc_id = request.form.get('doc_id')
            if doc_id:
                # prevent removal of primary doc
                docs = list_student_documents(student.id)
                target = next((d for d in docs if d.id == int(doc_id)), None)
                if target and target.is_primary:
                    flash('主证件不能被删除', 'error')
                else:
                    delete_student_document(int(doc_id))
        elif action == 'set_primary':
            doc_id = request.form.get('doc_id')
            if doc_id:
                set_primary_document(int(doc_id))
        elif action == 'update_doc':
            doc_id = request.form.get('doc_id')
            doc_type = request.form.get('doc_type','').strip()
            doc_number = request.form.get('doc_number','').strip()
            doc_name = request.form.get('doc_name','').strip() or None
            is_primary = request.form.get('is_primary') == 'on'
            docs = list_student_documents(student.id)
            if doc_id and doc_type and doc_number:
                current = next((d for d in docs if d.id == int(doc_id)), None)
                if current is None:
                    flash('未找到证件记录', 'error')
                else:
                    # disallow unsetting primary
                    if current.is_primary and not is_primary:
                        flash('主证件不能取消设定', 'error')
                    # disallow replacing primary with another
                    elif is_primary and any(d.is_primary and d.id != int(doc_id) for d in docs):
                        flash('主证件已经存在，无法替换', 'error')
                    else:
                        # check duplicates excluding self
                        others = [d for d in docs if d.id != int(doc_id) and d.doc_type == doc_type]
                        if others:
                            flash('该类型证件已存在，无法修改', 'error')
                        else:
                            try:
                                update_student_document(
                                    int(doc_id),
                                    doc_type,
                                    doc_number,
                                    doc_name,
                                    is_primary
                                )
                            except Exception:
                                flash('更新证件时发生错误', 'error')
        elif action == 'remove_class':
            cid = request.form.get('class_id')
            if cid:
                try:
                    remove_student(int(cid), student.id)
                    flash('已将学员从班级移除', 'success')
                except Exception:
                    flash('移除班级时出错', 'error')
        elif action == 'transfer_class':
            from_c = request.form.get('from_class_id')
            to_c = request.form.get('to_class_id')
            if from_c and to_c and from_c != to_c:
                try:
                    remove_student(int(from_c), student.id)
                    enroll_student(int(to_c), student.id)
                    flash('已将学员转班', 'success')
                except Exception:
                    flash('转班时发生错误', 'error')
        # 操作后刷新数据，重新查询 student 及相关数据
        student = next(iter(search_students(student_number=student_number)), None)
        documents = list_student_documents(student.id)
        student_classes = list_classes_for_student(student.id)
        doc_types = list_doc_types()
    birthday_year, birthday_month, birthday_day = _split_birthday_for_form(student.birthday)
    default_form_data = {
        "student_number": student.student_number,
        "display_name": student.display_name or "",
        # 兼容多证件，主证件姓名字段已无，若有主证件则用主证件号码，否则空
        "legal_name": (student.documents[0].doc_number if student.documents else ""),
        "gender": student.gender or "",
        "birthday": student.birthday or "",
        "birthday_year": birthday_year,
        "birthday_month": birthday_month,
        "birthday_day": birthday_day,
    }
    # ensure types loaded even on GET
    if not doc_types:
        doc_types = list_doc_types()
    ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    # always use the modal-style fragment; when accessed directly it will
    # simply embed the content inside the page body (the surrounding
    # <div class="modal"> is harmless). This avoids maintaining two
    # nearly-identical templates.
    return render_template(
        "students/_detail_modal_content.html",
        student=student,
        documents=documents,
        student_classes=student_classes,
        all_classes=all_classes,
        doc_types=doc_types,
        form_data=default_form_data,
        current_year=current_year,
        ajax=ajax,
    )


