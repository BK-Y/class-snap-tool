import sqlite3
from uuid import uuid4

from flask import Blueprint, flash, redirect, render_template, request, url_for

from dao.class_dao import create_class, get_class_by_id, list_classes_with_counts
from dao.enrollment_dao import (
    enroll_student_with_log,
    list_available_students_for_class,
    list_enrollment_logs_by_class,
    list_students_in_class,
    remove_student_with_log,
)

from db import get_db

classes_bp = Blueprint('classes',__name__,url_prefix='/classes')

REGULAR_LEVELS = {"U9B", "U9A", "U12B", "U12A"}
JBC_EVENTS = {
    "新秀级-城市挑战赛",
    "新秀级-亚洲分会",
    "新秀级-国际大会（中国）",
    "进阶级-城市挑战赛",
    "进阶级-亚洲分会",
    "进阶级-国际大会（中国）",
}
CLASS_STATUS_VALUES = {"planned", "active", "completed"}


def _parse_class_form(form):
    class_type_mode = (form.get('class_type_mode') or '').strip()
    group_number_raw = (form.get('group_number') or '').strip()
    class_status = (form.get('class_status') or '').strip()

    errors = []

    class_type = None
    level = None

    if class_status not in CLASS_STATUS_VALUES:
        errors.append('请选择有效的班级状态')

    if class_type_mode == 'regular':
        class_type = '常规班'
        regular_level = (form.get('regular_level') or '').strip()
        if regular_level not in REGULAR_LEVELS:
            errors.append('请选择有效的常规班级别')
        else:
            level = regular_level
    elif class_type_mode == 'competition':
        class_type = '竞赛集训'
        competition_item_mode = (form.get('competition_item_mode') or '').strip()
        competition_event_mode = (form.get('competition_event_mode') or '').strip()

        if competition_item_mode == 'jbc':
            competition_item = 'JBC'
        elif competition_item_mode == 'makex_inspire':
            competition_item = 'MakeX Inspire'
        elif competition_item_mode == 'makex_explorer':
            competition_item = 'MakeX Explorer'
        elif competition_item_mode == 'custom':
            competition_item = (form.get('competition_item_custom') or '').strip()
            if not competition_item:
                errors.append('请填写自定义赛项')
        else:
            competition_item = None
            errors.append('请选择赛项')

        if competition_event_mode == 'jbc_preset':
            competition_event = (form.get('jbc_event') or '').strip()
            if competition_event not in JBC_EVENTS:
                errors.append('请选择有效的 JBC 赛事级别')
        elif competition_event_mode == 'custom':
            competition_event = (form.get('competition_event_custom') or '').strip()
            if not competition_event:
                errors.append('请填写赛事级别')
        else:
            competition_event = None
            errors.append('请选择赛事级别录入方式')

        if competition_item and competition_event:
            level = f'{competition_item} - {competition_event}'
    elif class_type_mode == 'custom':
        class_type = (form.get('class_type_custom') or '').strip()
        level = (form.get('custom_level') or '').strip()
        if not class_type:
            errors.append('请填写自定义班级类型')
        if not level:
            errors.append('请填写自定义级别')
    else:
        errors.append('请选择班级类型')

    try:
        group_number = int(group_number_raw)
        if group_number <= 0:
            errors.append('期数必须为正整数')
    except ValueError:
        group_number = None
        errors.append('期数必须为整数')

    return class_type, level, group_number, class_status, errors

@classes_bp.route('/', methods=['GET', 'POST'])
def list_classes():
    errors = []

    if request.method == 'POST':
        class_type, level, group_number, class_status, errors = _parse_class_form(request.form)

        if not errors:
            try:
                with get_db() as conn:
                    create_class(
                        conn,
                        class_type=class_type,
                        level=level,
                        group_number=group_number,
                        status=class_status,
                    )
                    conn.commit()
                flash('班级创建成功', 'success')
                return redirect(url_for('classes.list_classes'))
            except sqlite3.IntegrityError:
                errors.append('同类型/同级别/同期数班级已存在')

    with get_db() as conn:
        classes = list_classes_with_counts(conn)
    return render_template('classes/list.html', classes=classes, errors=errors)


@classes_bp.route('/<int:class_id>/students', methods=['GET', 'POST'])
def manage_class_students(class_id):
    with get_db() as conn:
        class_item = get_class_by_id(conn, class_id)

    if not class_item:
        return '班级不存在', 404

    if request.method == 'POST':
        action = request.form.get('action', '').strip()
        student_id_raw = request.form.get('student_id', '').strip()
        reason = request.form.get('reason', '').strip() or None
        operator_id = request.form.get('operator_id', '').strip() or 'web-admin'
        request_id = str(uuid4())

        try:
            student_id = int(student_id_raw)
        except ValueError:
            flash('学员参数无效', 'error')
            return redirect(url_for('classes.manage_class_students', class_id=class_id))

        with get_db() as conn:
            if action == 'enroll':
                created = enroll_student_with_log(
                    conn,
                    class_id=class_id,
                    student_id=student_id,
                    operator_id=operator_id,
                    reason=reason,
                    source='web',
                    request_id=request_id,
                )
                if created:
                    flash('学员已加入班级', 'success')
                else:
                    flash('学员已在班级中', 'success')
            elif action == 'remove':
                removed = remove_student_with_log(
                    conn,
                    class_id=class_id,
                    student_id=student_id,
                    operator_id=operator_id,
                    reason=reason,
                    source='web',
                    request_id=request_id,
                )
                if removed:
                    flash('学员已移出班级', 'success')
                else:
                    flash('学员当前不在该班级', 'error')
            else:
                flash('未知操作', 'error')
            conn.commit()

        return redirect(url_for('classes.manage_class_students', class_id=class_id))

    with get_db() as conn:
        enrolled_students = list_students_in_class(conn, class_id=class_id)
        available_students = list_available_students_for_class(conn, class_id=class_id)
        enrollment_logs = list_enrollment_logs_by_class(conn, class_id=class_id, limit=50)

    return render_template(
        'classes/manage_students.html',
        class_item=class_item,
        enrolled_students=enrolled_students,
        available_students=available_students,
        enrollment_logs=enrollment_logs,
    )

# @bp.route('/',methods = ['POST'])
