from flask import Blueprint, redirect, url_for,request,render_template
import db
students_bp = Blueprint('students',__name__)

@students_bp.route('/students')
def index():
    # 从URL查询参数获取筛选数据
    name_id = request.args.get('name_id','').strip()
    name_nick = request.args.get('name_nick','').strip()
    school = request.args.get('school','').strip()
    gender  = request.args.get('gender','').strip()
    print("Received gender:", repr(gender))  # 查看终端输出

    # 调用通用查询函数
    students = db.search_students(
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
    return render_template('/student/view_all.html', students=students,filters=filters)

@students_bp.route('/students/add',methods=['GET','POST'])
def add_student():
    if request.method == 'POST':
        # 从表单获取数据
        name_id = request.form['name_id']
        name_nick = request.form['name_nick']
        gender = request.form.get('gender')
        birth_date = request.form.get('birth_date')
        school = request.form.get('school')

        # 调用数据库函数，保存数据
        db.create_student(
                name_id=name_id,
                name_nick = name_nick,
                gender=gender,
                birth_date=birth_date,
                school=school
        )

        # 保存后跳回首页
        return redirect(url_for('students.index'))

    # GET请求：显示空表达
    return render_template('add.html')

@students_bp.route('/edit/<int:student_id>',methods=['GET','POST'])
def edit_student(student_id):
    with db.get_db_connection() as conn:
        student = conn.execute(
            "SELECT * FROM students WHERE id = ?",(student_id,)
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


