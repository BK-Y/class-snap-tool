from uuid import uuid4

from flask import Blueprint, flash, redirect, render_template, request, url_for

from dao.class_sa_dao import create_class, get_class_by_id, list_classes_with_counts
from dao.enrollment_sa_dao import (
    enroll_student,
    list_enrollment_logs_by_class,
    list_students_in_class,
    remove_student,
    list_classes_for_student,
)
from dao.student_sa_dao import search_students

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
    """Primary class management page.

    Handles both the full-screen management UI (for normal browser requests)
    and the legacy AJAX modal content (when ``X-Requested-With`` header is
    present).  This consolidates the previous ``manage_page`` and
    ``list_classes`` endpoints so that ``/classes`` is the top‑level URL.
    """
    errors = []

    if request.method == 'POST':
        class_type, level, group_number, class_status, errors = _parse_class_form(request.form)

        if not errors:
            try:
                teacher = (request.form.get('teacher') or '').strip() or None
                class_time = (request.form.get('class_time') or '').strip() or None
                start_date = (request.form.get('start_date') or '').strip() or None
                create_class(
                    class_type=class_type,
                    level=level,
                    group_number=group_number,
                    status=class_status,
                    teacher=teacher,
                    class_time=class_time,
                    start_date=start_date,
                )
                flash('班级创建成功', 'success')
                return redirect(url_for('classes.list_classes'))
            except Exception:
                errors.append('同类型/同级别/同期数班级已存在')

    raw = list_classes_with_counts()
    classes = []
    for cls, cnt in raw:
        classes.append({
            'id': cls.id,
            'type': cls.type,
            'level': cls.level,
            'group_number': cls.group_number,
            'status': cls.status,
            'teacher': getattr(cls, 'teacher', None),
            'class_time': getattr(cls, 'class_time', None),
            'start_date': getattr(cls, 'start_date', None),
            'student_count': cnt,
        })
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('classes/_modal_content.html', classes=classes, errors=errors)
    # normal browser request: render the full management page
    return render_template('classes/manage.html', classes=classes, errors=errors)



# ``/classes/manage`` is retained only for legacy redirects; the
# real management UI lives at ``/classes/`` now.  Keep the view around so
# old links don't break, but simply forward to the new handler.
@classes_bp.route('/manage', methods=['GET', 'POST'])
def manage_page():
    return redirect(url_for('classes.list_classes'))


@classes_bp.route('/<int:class_id>/students', methods=['GET', 'POST'])
def manage_class_students(class_id):
    class_item = get_class_by_id(class_id)

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

        if action == 'enroll':
            enroll_student(
                class_id=class_id,
                student_id=student_id,
                operator_id=operator_id,
                reason=reason,
                source='web',
                request_id=request_id,
            )
            flash('学员已加入班级', 'success')
        elif action == 'remove':
            remove_student(
                class_id=class_id,
                student_id=student_id,
                operator_id=operator_id,
                reason=reason,
                source='web',
                request_id=request_id,
            )
            flash('学员已移出班级', 'success')
        else:
            flash('未知操作', 'error')

        return redirect(url_for('classes.manage_class_students', class_id=class_id))

    # keep the raw tuples returned by DAO (student, enrolled_at)
    enrolled_students = list_students_in_class(class_id)
    # forward enrollment logs to template; available_students removed (search modal handles it)
    enrollment_logs = list_enrollment_logs_by_class(class_id, limit=50)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template(
            'classes/_class_detail.html',
            class_item=class_item,
            enrolled_students=enrolled_students,
            enrollment_logs=enrollment_logs,
        )

    return render_template(
        'classes/manage_students.html',
        class_item=class_item,
        enrolled_students=enrolled_students,
        enrollment_logs=enrollment_logs,
    )


@classes_bp.route('/<int:class_id>/search', methods=['GET'])
def search_students_for_class(class_id):
    """Return JSON of students not enrolled in the class.

    Query params:
    * q - optional search string (name or student number)
    * page - page number (1-based)

    Response: {results:[...], total:, page:, per_page:}
    """
    q = request.args.get('q', '').strip()
    try:
        page = max(int(request.args.get('page', '1')), 1)
    except ValueError:
        page = 1
    per_page = 10

    # compute enrolled IDs
    enrolled = set()
    for row in list_students_in_class(class_id):
        student_obj = row[0] if isinstance(row, (tuple, list)) else row
        if hasattr(student_obj, 'id'):
            enrolled.add(student_obj.id)

    # gather candidates
    if q:
        candidates = []
        candidates.extend(search_students(display_name=q) or [])
        candidates.extend(search_students(student_number=q) or [])
        # dedupe while filtering
        seen = set()
        filtered = []
        for s in candidates:
            if s.id in seen:
                continue
            seen.add(s.id)
            if s.id not in enrolled:
                filtered.append(s)
    else:
        from db.models import Student
        filtered = Student.query.filter(~Student.id.in_(enrolled)).all()

    total = len(filtered)
    start = (page - 1) * per_page
    page_items = filtered[start:start+per_page]

    def compute_name(s):
        if getattr(s, 'display_name', None):
            return s.display_name
        # inspect documents if available
        for doc in getattr(s, 'documents', []) or []:
            if getattr(doc, 'doc_name', None):
                return doc.doc_name
        return getattr(s, 'student_number', '') or ''

    data = [
        {'id': s.id,
         'name': compute_name(s),
         'gender': s.gender}
        for s in page_items
    ]
    from flask import jsonify
    return jsonify({'results': data, 'total': total, 'page': page, 'per_page': per_page})

# @bp.route('/',methods = ['POST'])
