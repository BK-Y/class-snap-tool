from datetime import datetime, date
import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, url_for

from dao.student_dao import (
    create_student,
    generate_student_number,
    search_students,
    update_student,
)
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

@students_bp.route('/students')
def index():
    # 从URL查询参数获取筛选数据
    name_id = request.args.get('name_id','').strip()
    name_nick = request.args.get('name_nick','').strip()
    gender  = request.args.get('gender','').strip()
    # print("Received gender:", repr(gender))  # 查看终端输出

    # 调用通用查询函数
    with get_db() as conn:
        students = search_students(
            conn,
            legal_name = name_id or None,
            display_name = name_nick or None,
            # school = school or None,
            gender = gender or None
        )

    # 将当前筛选条件返回模板，用于保持表单值
    filters = {
        'name_id':name_id,
        'name_nick':name_nick,
        'gender':gender
    }
    # 调用你写的函数，获取所有活跃学员
    return render_template('/students/view_students.html', students=students,filters=filters)

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
    with get_db() as conn:
        student = conn.execute(
            "SELECT * FROM students WHERE student_number = ?",(student_number,)
            ).fetchone()

    if not student:
        return "学员不存在",404

    if request.method == 'POST':
        display_name = request.form.get("display_name", "").strip()
        legal_name = request.form.get("legal_name", "").strip()
        gender = request.form.get("gender", "").strip() or None
        birthday = (request.form.get("birthday") or "").strip() or None
        doc_type = request.form.get("doc_type", "").strip()
        doc_number = request.form.get("doc_number", "").strip()

        errors = []
        if not display_name:
            errors.append("常用称呼不能为空")
        if not legal_name:
            errors.append("法定姓名不能为空")

        if errors:
            return render_template("edit.html", student=student, errors=errors)

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
            return render_template("edit.html", student=student, errors=[f"数据库错误：{e}"])

    # GET 请求：显示编辑表单，雨天当前值
    return render_template('edit.html',student=student)


