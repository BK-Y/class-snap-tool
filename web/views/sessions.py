"""Views for session management and scoring."""

from datetime import date, datetime
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from dao.session_dao import (
    create_schedule_pattern,
    list_schedule_patterns_for_class,
    update_schedule_pattern,
    delete_schedule_pattern,
    get_schedule_pattern,
    get_pattern_history,
    create_session,
    list_sessions_for_class,
    update_session,
    cancel_session,
    mark_session_held,
    delete_session,
    create_score,
    list_scores_for_session,
    list_scores_for_student,
    batch_create_scores,
    get_class_session_stats,
)
from dao.session_query_examples import (
    get_class_schedule_vs_actual,
    get_class_score_summary,
)
from dao.class_sa_dao import get_class_by_id
from dao.student_sa_dao import search_students
from dao.enrollment_sa_dao import list_students_in_class

sessions_bp = Blueprint('sessions', __name__, url_prefix='/classes/<int:class_id>/sessions')


@sessions_bp.route('/')
def list_class_sessions(class_id):
    """List sessions and schedule patterns for a class."""
    class_item = get_class_by_id(class_id)
    if not class_item:
        return '班级不存在', 404
    
    # Get data
    patterns = list_schedule_patterns_for_class(class_id, active_only=False)
    sessions = list_sessions_for_class(class_id, limit=50)
    stats = get_class_session_stats(class_id)
    schedule_data = get_class_schedule_vs_actual(class_id)
    score_summary = get_class_score_summary(class_id)
    
    # Get enrolled students for scoring
    enrolled = list_students_in_class(class_id)
    students = []
    for s, _ in enrolled:
        students.append({
            'id': s.id,
            'name': s.display_name or (s.documents[0].doc_name if s.documents else s.student_number),
            'student_number': s.student_number,
        })
    
    return render_template('sessions/list.html',
        class_item=class_item,
        patterns=patterns,
        sessions=sessions,
        stats=stats,
        schedule_data=schedule_data,
        score_summary=score_summary,
        students=students,
    )


@sessions_bp.route('/patterns', methods=['POST'])
def add_pattern(class_id):
    """Add a schedule pattern."""
    class_item = get_class_by_id(class_id)
    if not class_item:
        return jsonify({'success': False, 'error': '班级不存在'}), 404
    
    try:
        weekday = int(request.form.get('weekday'))
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        repeat_interval = int(request.form.get('repeat_interval') or 1)
        valid_from = request.form.get('valid_from') or None
        valid_to = request.form.get('valid_to') or None
        note = request.form.get('note') or None
        
        if not (0 <= weekday <= 6):
            return jsonify({'success': False, 'error': '星期几必须为 0-6'}), 400
        if not start_time or not end_time:
            return jsonify({'success': False, 'error': '请填写开始和结束时间'}), 400
        
        pattern_id = create_schedule_pattern(
            class_id=class_id,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            repeat_interval=repeat_interval,
            valid_from=date.fromisoformat(valid_from) if valid_from else None,
            valid_to=date.fromisoformat(valid_to) if valid_to else None,
            note=note,
        )
        return jsonify({'success': True, 'pattern_id': pattern_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@sessions_bp.route('/patterns/<int:pattern_id>', methods=['DELETE'])
def delete_pattern(class_id, pattern_id):
    """Delete a schedule pattern."""
    if delete_schedule_pattern(pattern_id):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '未找到规则'}), 404


@sessions_bp.route('/patterns/<int:pattern_id>/edit', methods=['POST'])
def edit_pattern(class_id, pattern_id):
    """Edit a schedule pattern with history tracking."""
    class_item = get_class_by_id(class_id)
    if not class_item:
        return jsonify({'success': False, 'error': '班级不存在'}), 404

    pattern = get_schedule_pattern(pattern_id)
    if not pattern:
        return jsonify({'success': False, 'error': '未找到规则'}), 404

    try:
        weekday = request.form.get('weekday')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        repeat_interval = request.form.get('repeat_interval')
        valid_from = request.form.get('valid_from') or None
        valid_to = request.form.get('valid_to') or None
        note = request.form.get('note') or None
        change_reason = request.form.get('change_reason') or None

        success = update_schedule_pattern(
            pattern_id=pattern_id,
            weekday=int(weekday) if weekday else None,
            start_time=start_time or None,
            end_time=end_time or None,
            repeat_interval=int(repeat_interval) if repeat_interval else None,
            valid_from=date.fromisoformat(valid_from) if valid_from else None,
            valid_to=date.fromisoformat(valid_to) if valid_to else None,
            note=note,
            change_reason=change_reason,
            changed_by='web',
        )
        
        if success:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': '更新失败'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@sessions_bp.route('/patterns/<int:pattern_id>/history', methods=['GET'])
def get_pattern_history_view(class_id, pattern_id):
    """Get modification history for a pattern."""
    pattern = get_schedule_pattern(pattern_id)
    if not pattern:
        return jsonify({'success': False, 'error': '未找到规则'}), 404

    history = get_pattern_history(pattern_id)
    return jsonify({
        'success': True,
        'history': [
            {
                'id': h.id,
                'changed_at': h.changed_at.isoformat() if h.changed_at else None,
                'changed_by': h.changed_by,
                'change_reason': h.change_reason,
                'old': {
                    'weekday': h.old_weekday,
                    'start_time': h.old_start_time,
                    'end_time': h.old_end_time,
                    'repeat_interval': h.old_repeat_interval,
                    'valid_from': h.old_valid_from.isoformat() if h.old_valid_from else None,
                    'valid_to': h.old_valid_to.isoformat() if h.old_valid_to else None,
                    'note': h.old_note,
                },
                'new': {
                    'weekday': h.new_weekday,
                    'start_time': h.new_start_time,
                    'end_time': h.new_end_time,
                    'repeat_interval': h.new_repeat_interval,
                    'valid_from': h.new_valid_from.isoformat() if h.new_valid_from else None,
                    'valid_to': h.new_valid_to.isoformat() if h.new_valid_to else None,
                    'note': h.new_note,
                },
                'affected_sessions_count': h.affected_sessions_count,
            }
            for h in history
        ]
    })


@sessions_bp.route('/create', methods=['POST'])
def create_class_session(class_id):
    """Create a new session."""
    class_item = get_class_by_id(class_id)
    if not class_item:
        return jsonify({'success': False, 'error': '班级不存在'}), 404
    
    try:
        session_date_str = request.form.get('session_date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        session_index = request.form.get('session_index')
        topic = request.form.get('topic')
        teacher = request.form.get('teacher')
        is_extra = request.form.get('is_extra') == 'on'
        schedule_pattern_id = request.form.get('schedule_pattern_id') or None
        
        session_date = date.fromisoformat(session_date_str)
        
        session_id = create_session(
            class_id=class_id,
            session_date=session_date,
            schedule_pattern_id=int(schedule_pattern_id) if schedule_pattern_id else None,
            start_time=start_time or None,
            end_time=end_time or None,
            session_index=int(session_index) if session_index else None,
            topic=topic or None,
            teacher=teacher or None,
            is_extra=is_extra,
        )
        return jsonify({'success': True, 'session_id': session_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@sessions_bp.route('/<int:session_id>/status', methods=['POST'])
def update_session_status(class_id, session_id):
    """Update session status (held/canceled)."""
    action = request.form.get('action')
    
    if action == 'held':
        success = mark_session_held(session_id)
    elif action == 'cancel':
        reason = request.form.get('cancel_reason', '')
        success = cancel_session(session_id, reason)
    else:
        return jsonify({'success': False, 'error': '未知操作'}), 400
    
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '更新失败'}), 500


@sessions_bp.route('/<int:session_id>/scores', methods=['GET', 'POST'])
def manage_session_scores(class_id, session_id):
    """Manage scores for a session."""
    if request.method == 'POST':
        # Batch create/update scores
        try:
            scores_data = request.json.get('scores', [])
            recorded_by = request.json.get('recorded_by', 'web')
            
            # Delete existing scores for this session first (simple approach)
            from db.sa_db import db
            from db.models import SessionScore
            SessionScore.query.filter_by(session_id=session_id).delete()
            db.session.commit()
            
            # Create new scores
            created = batch_create_scores(session_id, scores_data, recorded_by)
            return jsonify({'success': True, 'count': len(created)})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET: return existing scores
    scores = list_scores_for_session(session_id)
    return jsonify({
        'scores': [
            {
                'student_id': s.student_id,
                'score_type': s.score_type,
                'score': s.score,
                'comment': s.comment,
            }
            for s in scores
        ]
    })


@sessions_bp.route('/<int:session_id>/delete', methods=['POST'])
def delete_class_session(class_id, session_id):
    """Delete a session."""
    if delete_session(session_id):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '未找到课次'}), 404
