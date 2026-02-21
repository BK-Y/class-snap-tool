from flask import Blueprint, redirect, url_for,request,render_template,flash
from dao.student_dao import (
        search_students,
        create_student,
        generate_student_number,
        )
from db import get_db
from datetime import datetime
import sqlite3
students_bp = Blueprint('students',__name__)

@students_bp.route('/students')
def index():
    # 从URL查询参数获取筛选数据
    name_id = request.args.get('name_id','').strip()
    name_nick = request.args.get('name_nick','').strip()
    school = request.args.get('school','').strip()
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
        'school':school,
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
                # if not doc_type:
                #     errors.append('证件类型不能为空')
                # if not doc_number:
                #     errors.append('证件号码不能为空')
                
                if errors:
                    return render_template('students/add.html',current_year=current_year, errors=errors, form_data=request.form)
                
                # 插入学生
                student_number = create_student(
                    conn,
                    student_number=student_number,
                    display_name=display_name,
                    legal_name=legal_name,
                    doc_type=doc_type,
                    doc_number=doc_number,
                    gender=gender,
                )
                
                conn.commit()
            
            flash(f'学生添加成功！学号：{student_number}', 'success')
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
        # 获取表达数据 ：
        name_id = request.form['name_id']
        name_nick = request.form['name_nick']
        gender = request.form.get('gender')
        birth_date = request.form.get('birth_date')
        school = request.form.get('school')

        # 调用更新函数
        db.update_student(
                student_id = student_id,
                name_id=name_id,
                name_nick=name_nick,
                gender=gender,
                birth_date=birth_date,
                school=school
                )
        return redirect(url_for('students.index'))
    # GET 请求：显示编辑表单，雨天当前值
    return render_template('edit.html',student=student)


