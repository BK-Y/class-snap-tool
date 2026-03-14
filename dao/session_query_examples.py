"""Query examples for the three-table session model.

This module demonstrates typical queries as described in docs/design.md:
1. All class records for a student
2. Schedule patterns vs actual sessions comparison for a class
3. Score trends and statistics
"""

from datetime import date
from typing import List, Dict, Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from db.models import (
    ClassSchedulePattern,
    ClassSession,
    SessionScore,
    Class,
    Student,
)
from db.sa_db import db


def get_student_all_session_records(
    student_id: int,
    class_id: Optional[int] = None,
    status_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Get all class session records for a student.
    
    This query answers: "在哪些班级、哪些节课、打了哪些分"
    
    Args:
        student_id: The student ID
        class_id: Optional class filter
        status_filter: Optional session status filter (e.g., ['held'])
    
    Returns:
        List of dicts with session and score details
    """
    q = db.session.query(
        ClassSession.id.label('session_id'),
        ClassSession.session_date,
        ClassSession.start_time,
        ClassSession.end_time,
        ClassSession.session_index,
        ClassSession.session_stage,
        ClassSession.status,
        ClassSession.topic,
        ClassSession.teacher.label('session_teacher'),
        Class.id.label('class_id'),
        Class.type.label('class_type'),
        Class.level.label('class_level'),
        Class.group_number.label('class_group'),
        Class.teacher.label('class_teacher'),
        SessionScore.id.label('score_id'),
        SessionScore.score_type,
        SessionScore.score,
        SessionScore.comment,
        SessionScore.recorded_by,
        SessionScore.created_at.label('score_created_at'),
    ).join(Class).join(SessionScore)\
     .filter(SessionScore.student_id == student_id)\
     .filter(ClassSession.status == 'held')
    
    if class_id:
        q = q.filter(ClassSession.class_id == class_id)
    
    if status_filter:
        q = q.filter(ClassSession.status.in_(status_filter))
    
    results = q.order_by(
        ClassSession.session_date.desc(),
        ClassSession.start_time,
        SessionScore.created_at,
    ).all()
    
    # Group scores by session
    sessions_dict = {}
    for row in results:
        sid = row.session_id
        if sid not in sessions_dict:
            sessions_dict[sid] = {
                'session_id': sid,
                'session_date': row.session_date.isoformat() if row.session_date else None,
                'start_time': row.start_time,
                'end_time': row.end_time,
                'session_index': row.session_index,
                'session_stage': row.session_stage,
                'status': row.status,
                'topic': row.topic,
                'teacher': row.session_teacher or row.class_teacher,  # Prefer session teacher
                'class': {
                    'id': row.class_id,
                    'type': row.class_type,
                    'level': row.class_level,
                    'group_number': row.class_group,
                },
                'scores': [],
            }
        if row.score_id:
            sessions_dict[sid]['scores'].append({
                'score_id': row.score_id,
                'score_type': row.score_type,
                'score': row.score,
                'comment': row.comment,
                'recorded_by': row.recorded_by,
                'created_at': row.score_created_at.isoformat() if row.score_created_at else None,
            })
    
    return list(sessions_dict.values())


def get_class_schedule_vs_actual(
    class_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> Dict[str, Any]:
    """Compare scheduled patterns vs actual sessions for a class.
    
    This query answers: "排课与实际课次对比"
    
    Args:
        class_id: The class ID
        date_from: Optional start date filter
        date_to: Optional end date filter
    
    Returns:
        Dict with schedule patterns and actual session counts
    """
    # Get schedule patterns
    patterns_q = ClassSchedulePattern.query.filter_by(class_id=class_id)
    if date_from:
        patterns_q = patterns_q.filter(
            db.or_(
                ClassSchedulePattern.valid_from.is_(None),
                ClassSchedulePattern.valid_from <= date_to,
            ),
        )
    if date_to:
        patterns_q = patterns_q.filter(
            db.or_(
                ClassSchedulePattern.valid_to.is_(None),
                ClassSchedulePattern.valid_to >= date_from,
            ),
        )
    patterns = patterns_q.all()
    
    patterns_data = []
    for p in patterns:
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        patterns_data.append({
            'id': p.id,
            'weekday': weekday_names[p.weekday] if 0 <= p.weekday <= 6 else p.weekday,
            'weekday_num': p.weekday,
            'start_time': p.start_time,
            'end_time': p.end_time,
            'repeat_interval': p.repeat_interval,
            'valid_from': p.valid_from.isoformat() if p.valid_from else None,
            'valid_to': p.valid_to.isoformat() if p.valid_to else None,
            'note': p.note,
        })
    
    # Get actual sessions count by status
    sessions_q = db.session.query(
        ClassSession.status,
        func.count(ClassSession.id).label('count'),
    ).filter(ClassSession.class_id == class_id)
    
    if date_from:
        sessions_q = sessions_q.filter(ClassSession.session_date >= date_from)
    if date_to:
        sessions_q = sessions_q.filter(ClassSession.session_date <= date_to)
    
    sessions_by_status = sessions_q.group_by(ClassSession.status).all()
    
    # Get detailed sessions list
    sessions_detail = ClassSession.query.filter_by(class_id=class_id)\
        .options(joinedload(ClassSession.schedule_pattern))\
        .order_by(ClassSession.session_date.desc())\
        .all()
    
    if date_from:
        sessions_detail = [s for s in sessions_detail if s.session_date >= date_from]
    if date_to:
        sessions_detail = [s for s in sessions_detail if s.session_date <= date_to]
    
    sessions_data = []
    for s in sessions_detail:
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        sessions_data.append({
            'id': s.id,
            'session_date': s.session_date.isoformat() if s.session_date else None,
            'weekday': weekday_names[s.session_date.weekday()] if s.session_date else None,
            'start_time': s.start_time,
            'end_time': s.end_time,
            'session_index': s.session_index,
            'session_stage': s.session_stage,
            'status': s.status,
            'cancel_reason': s.cancel_reason,
            'is_extra': s.is_extra,
            'topic': s.topic,
            'teacher': s.teacher,
            'schedule_pattern_id': s.schedule_pattern_id,
        })
    
    # Calculate expected sessions based on patterns
    expected_count = 0
    for p in patterns:
        # Simple calculation: count weeks in date range
        if date_from and date_to:
            weeks = (date_to - date_from).days // 7
            expected_count += weeks // p.repeat_interval + 1
    
    status_summary = {row.status: row.count for row in sessions_by_status}
    
    return {
        'patterns': patterns_data,
        'sessions': sessions_data,
        'status_summary': status_summary,
        'expected_sessions': expected_count,
        'actual_held': status_summary.get('held', 0),
        'actual_canceled': status_summary.get('canceled', 0),
        'actual_rescheduled': status_summary.get('rescheduled', 0),
    }


def get_score_trend_for_student(
    student_id: int,
    score_type: Optional[str] = None,
    class_id: Optional[int] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Get score trend for a student over time.
    
    Args:
        student_id: The student ID
        score_type: Optional score type filter (Q/T/C/M1/M2/N)
        class_id: Optional class filter
        limit: Max sessions to return
    
    Returns:
        List of dicts with session date and average score
    """
    q = db.session.query(
        ClassSession.session_date,
        func.avg(SessionScore.score).label('avg_score'),
        func.count(SessionScore.id).label('score_count'),
    ).join(ClassSession)\
     .filter(SessionScore.student_id == student_id)\
     .filter(ClassSession.status == 'held')
    
    if score_type:
        q = q.filter(SessionScore.score_type == score_type)
    
    if class_id:
        q = q.filter(ClassSession.class_id == class_id)
    
    results = q.group_by(ClassSession.session_date)\
               .order_by(ClassSession.session_date.desc())\
               .limit(limit).all()
    
    return [
        {
            'session_date': row.session_date.isoformat() if row.session_date else None,
            'avg_score': float(row.avg_score) if row.avg_score else 0.0,
            'score_count': row.score_count,
        }
        for row in results
    ]


def get_class_score_summary(
    class_id: int,
    session_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Get score summary for a class.
    
    Args:
        class_id: The class ID
        session_id: Optional session filter
    
    Returns:
        Dict with score type statistics
    """
    q = db.session.query(
        SessionScore.score_type,
        func.avg(SessionScore.score).label('avg_score'),
        func.min(SessionScore.score).label('min_score'),
        func.max(SessionScore.score).label('max_score'),
        func.count(SessionScore.id).label('count'),
    ).join(ClassSession)\
     .filter(ClassSession.class_id == class_id)\
     .filter(ClassSession.status == 'held')
    
    if session_id:
        q = q.filter(SessionScore.session_id == session_id)
    
    results = q.group_by(SessionScore.score_type).all()
    
    return {
        row.score_type: {
            'avg': float(row.avg_score) if row.avg_score else 0.0,
            'min': row.min_score,
            'max': row.max_score,
            'count': row.count,
        }
        for row in results
    }


def get_student_ranking_in_class(
    class_id: int,
    score_type: Optional[str] = None,
    session_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Get student ranking by average score in a class.
    
    Args:
        class_id: The class ID
        score_type: Optional score type filter
        session_id: Optional session filter
    
    Returns:
        List of students with their average scores, ordered by rank
    """
    q = db.session.query(
        Student.id.label('student_id'),
        Student.student_number,
        Student.display_name,
        func.avg(SessionScore.score).label('avg_score'),
        func.count(SessionScore.id).label('score_count'),
    ).join(SessionScore)\
     .join(ClassSession)\
     .filter(ClassSession.class_id == class_id)\
     .filter(ClassSession.status == 'held')
    
    if score_type:
        q = q.filter(SessionScore.score_type == score_type)
    
    if session_id:
        q = q.filter(SessionScore.session_id == session_id)
    
    results = q.group_by(Student.id, Student.student_number, Student.display_name)\
               .order_by(func.avg(SessionScore.score).desc())\
               .all()
    
    return [
        {
            'rank': i + 1,
            'student_id': row.student_id,
            'student_number': row.student_number,
            'display_name': row.display_name,
            'avg_score': float(row.avg_score) if row.avg_score else 0.0,
            'score_count': row.score_count,
        }
        for i, row in enumerate(results)
    ]


def get_sessions_without_scores(class_id: int) -> List[Dict[str, Any]]:
    """Find sessions that have no score records yet.
    
    Useful for identifying classes where teachers forgot to record scores.
    
    Args:
        class_id: The class ID
    
    Returns:
        List of sessions without scores
    """
    q = db.session.query(
        ClassSession.id,
        ClassSession.session_date,
        ClassSession.start_time,
        ClassSession.end_time,
        ClassSession.topic,
        ClassSession.status,
    ).outerjoin(
        SessionScore,
        ClassSession.id == SessionScore.session_id
    ).filter(
        ClassSession.class_id == class_id,
        ClassSession.status == 'held',
        SessionScore.id.is_(None),  # No scores recorded
    ).order_by(ClassSession.session_date.desc()).all()
    
    return [
        {
            'session_id': row.id,
            'session_date': row.session_date.isoformat() if row.session_date else None,
            'start_time': row.start_time,
            'end_time': row.end_time,
            'topic': row.topic,
            'status': row.status,
        }
        for row in q
    ]
