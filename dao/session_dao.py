"""DAO for class schedule patterns, sessions, and scores.

This module provides data access functions for the three-table model:
- ClassSchedulePattern: recurring schedule rules for a class
- ClassSession: actual class sessions (held/canceled/rescheduled)
- SessionScore: score records for students in each session
"""

from datetime import datetime, date
from typing import List, Optional, Tuple, Dict, Any
from contextlib import contextmanager

from db.models import ClassSchedulePattern, ClassSession, SessionScore, Class, Student
from db.sa_db import db


# ==================== Context Manager for Transactions ====================

@contextmanager
def transaction():
    """Context manager for database transactions with automatic rollback."""
    try:
        yield
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


# ==================== ClassSchedulePattern DAO ====================

def create_schedule_pattern(
    class_id: int,
    weekday: int,
    start_time: str,
    end_time: str,
    repeat_interval: int = 1,
    valid_from: Optional[date] = None,
    valid_to: Optional[date] = None,
    note: Optional[str] = None,
) -> int:
    """Create a new schedule pattern for a class.
    
    Args:
        class_id: The class ID
        weekday: Day of week (0=Monday, 6=Sunday)
        start_time: Start time in HH:MM format
        end_time: End time in HH:MM format
        repeat_interval: How often the class repeats (1=every week, 2=every other week)
        valid_from: Rule effective start date
        valid_to: Rule effective end date
        note: Optional note (e.g., "寒假停课")
    
    Returns:
        The created pattern ID
    """
    pattern = ClassSchedulePattern(
        class_id=class_id,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        repeat_interval=repeat_interval,
        valid_from=valid_from,
        valid_to=valid_to,
        note=note,
    )
    db.session.add(pattern)
    db.session.commit()
    return pattern.id


def get_schedule_pattern(pattern_id: int) -> Optional[ClassSchedulePattern]:
    """Get a schedule pattern by ID."""
    return ClassSchedulePattern.query.get(pattern_id)


def list_schedule_patterns_for_class(class_id: int, active_only: bool = True) -> List[ClassSchedulePattern]:
    """List all schedule patterns for a class.
    
    Args:
        class_id: The class ID
        active_only: If True, only return patterns that are currently valid
    
    Returns:
        List of schedule patterns
    """
    q = ClassSchedulePattern.query.filter_by(class_id=class_id)
    if active_only:
        today = date.today()
        q = q.filter(
            db.or_(
                ClassSchedulePattern.valid_from.is_(None),
                ClassSchedulePattern.valid_from <= today,
            ),
            db.or_(
                ClassSchedulePattern.valid_to.is_(None),
                ClassSchedulePattern.valid_to >= today,
            ),
        )
    return q.order_by(ClassSchedulePattern.weekday, ClassSchedulePattern.start_time).all()


def update_schedule_pattern(
    pattern_id: int,
    weekday: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    repeat_interval: Optional[int] = None,
    valid_from: Optional[date] = None,
    valid_to: Optional[date] = None,
    note: Optional[str] = None,
    change_reason: Optional[str] = None,
    changed_by: str = 'web',
) -> bool:
    """Update a schedule pattern with history tracking.
    
    This function creates a history record before updating, ensuring that
    past sessions remain unaffected and changes are auditable.
    
    Args:
        pattern_id: The pattern ID to update
        weekday: New weekday (0-6)
        start_time: New start time (HH:MM)
        end_time: New end time (HH:MM)
        repeat_interval: New repeat interval
        valid_from: New valid from date
        valid_to: New valid to date
        note: New note
        change_reason: Reason for the change
        changed_by: Who made the change
    
    Returns:
        True if updated, False if pattern not found
    """
    from db.models import ClassSchedulePatternHistory
    
    pattern = ClassSchedulePattern.query.get(pattern_id)
    if not pattern:
        return False

    # Check if any fields actually changed
    changes = {}
    if weekday is not None and weekday != pattern.weekday:
        changes['weekday'] = (pattern.weekday, weekday)
    if start_time is not None and start_time != pattern.start_time:
        changes['start_time'] = (pattern.start_time, start_time)
    if end_time is not None and end_time != pattern.end_time:
        changes['end_time'] = (pattern.end_time, end_time)
    if repeat_interval is not None and repeat_interval != pattern.repeat_interval:
        changes['repeat_interval'] = (pattern.repeat_interval, repeat_interval)
    if valid_from is not None and valid_from != pattern.valid_from:
        changes['valid_from'] = (pattern.valid_from, valid_from)
    if valid_to is not None and valid_to != pattern.valid_to:
        changes['valid_to'] = (pattern.valid_to, valid_to)
    if note is not None and note != pattern.note:
        changes['note'] = (pattern.note, note)
    
    # Only create history record if something actually changed
    if changes:
        # Count affected future sessions (sessions with status='scheduled' linked to this pattern)
        from db.models import ClassSession
        affected_count = ClassSession.query.filter(
            ClassSession.schedule_pattern_id == pattern_id,
            ClassSession.status == 'scheduled'
        ).count()
        
        # Create history record
        history = ClassSchedulePatternHistory(
            pattern_id=pattern_id,
            class_id=pattern.class_id,
            old_weekday=pattern.weekday,
            old_start_time=pattern.start_time,
            old_end_time=pattern.end_time,
            old_repeat_interval=pattern.repeat_interval,
            old_valid_from=pattern.valid_from,
            old_valid_to=pattern.valid_to,
            old_note=pattern.note,
            new_weekday=weekday if weekday is not None else pattern.weekday,
            new_start_time=start_time if start_time is not None else pattern.start_time,
            new_end_time=end_time if end_time is not None else pattern.end_time,
            new_repeat_interval=repeat_interval if repeat_interval is not None else pattern.repeat_interval,
            new_valid_from=valid_from if valid_from is not None else pattern.valid_from,
            new_valid_to=valid_to if valid_to is not None else pattern.valid_to,
            new_note=note if note is not None else pattern.note,
            change_reason=change_reason,
            changed_by=changed_by,
            affected_sessions_count=affected_count,
        )
        db.session.add(history)
        
        # Update pattern version
        pattern.version = (pattern.version or 1) + 1
    
    # Apply updates
    if weekday is not None:
        pattern.weekday = weekday
    if start_time is not None:
        pattern.start_time = start_time
    if end_time is not None:
        pattern.end_time = end_time
    if repeat_interval is not None:
        pattern.repeat_interval = repeat_interval
    if valid_from is not None:
        pattern.valid_from = valid_from
    if valid_to is not None:
        pattern.valid_to = valid_to
    if note is not None:
        pattern.note = note

    db.session.commit()
    return True


def get_pattern_history(pattern_id: int) -> List:
    """Get modification history for a pattern.
    
    Returns:
        List of history records ordered by change time (newest first)
    """
    from db.models import ClassSchedulePatternHistory
    return ClassSchedulePatternHistory.query.filter_by(pattern_id=pattern_id)\
        .order_by(ClassSchedulePatternHistory.changed_at.desc()).all()


def delete_schedule_pattern(pattern_id: int) -> bool:
    """Delete a schedule pattern.

    Returns:
        True if deleted, False if pattern not found
    """
    pattern = ClassSchedulePattern.query.get(pattern_id)
    if not pattern:
        return False
    db.session.delete(pattern)
    db.session.commit()
    return True


# ==================== ClassSession DAO ====================

def create_session(
    class_id: int,
    session_date: date,
    schedule_pattern_id: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    session_index: Optional[int] = None,
    session_stage: Optional[str] = None,
    status: str = 'scheduled',
    is_extra: bool = False,
    topic: Optional[str] = None,
    teacher: Optional[str] = None,
) -> int:
    """Create a new class session.
    
    Args:
        class_id: The class ID
        session_date: The date of the session
        schedule_pattern_id: Optional reference to the schedule pattern
        start_time: Optional actual start time
        end_time: Optional actual end time
        session_index: Session number (e.g., 1st, 2nd class)
        session_stage: Stage/phase (e.g., 讲解/实操/汇报)
        status: Session status (scheduled/held/canceled/rescheduled)
        is_extra: Whether this is an extra/makeup session
        topic: Session topic
        teacher: Teacher for this session (overrides class default)
    
    Returns:
        The created session ID
    """
    session = ClassSession(
        class_id=class_id,
        session_date=session_date,
        schedule_pattern_id=schedule_pattern_id,
        start_time=start_time,
        end_time=end_time,
        session_index=session_index,
        session_stage=session_stage,
        status=status,
        is_extra=is_extra,
        topic=topic,
        teacher=teacher,
    )
    db.session.add(session)
    db.session.commit()
    return session.id


def get_session(session_id: int) -> Optional[ClassSession]:
    """Get a session by ID with related data."""
    return ClassSession.query.options(
        db.joinedload(ClassSession.class_ref),
        db.joinedload(ClassSession.schedule_pattern),
        db.joinedload(ClassSession.scores),
    ).get(session_id)


def list_sessions_for_class(
    class_id: int,
    status_filter: Optional[List[str]] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: Optional[int] = None,
) -> List[ClassSession]:
    """List sessions for a class.
    
    Args:
        class_id: The class ID
        status_filter: Optional list of statuses to filter by
        date_from: Optional start date filter
        date_to: Optional end date filter
        limit: Optional limit on results
    
    Returns:
        List of sessions ordered by date
    """
    q = ClassSession.query.filter_by(class_id=class_id)
    
    if status_filter:
        q = q.filter(ClassSession.status.in_(status_filter))
    if date_from:
        q = q.filter(ClassSession.session_date >= date_from)
    if date_to:
        q = q.filter(ClassSession.session_date <= date_to)
    
    q = q.order_by(ClassSession.session_date.desc(), ClassSession.start_time)
    
    if limit:
        q = q.limit(limit)
    
    return q.all()


def update_session(
    session_id: int,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    session_stage: Optional[str] = None,
    status: Optional[str] = None,
    cancel_reason: Optional[str] = None,
    reschedule_to_session_id: Optional[int] = None,
    is_extra: Optional[bool] = None,
    topic: Optional[str] = None,
    summary: Optional[str] = None,
    teacher: Optional[str] = None,
) -> bool:
    """Update a session.
    
    Returns:
        True if updated, False if session not found
    """
    session = ClassSession.query.get(session_id)
    if not session:
        return False
    
    if start_time is not None:
        session.start_time = start_time
    if end_time is not None:
        session.end_time = end_time
    if session_stage is not None:
        session.session_stage = session_stage
    if status is not None:
        session.status = status
    if cancel_reason is not None:
        session.cancel_reason = cancel_reason
    if reschedule_to_session_id is not None:
        session.reschedule_to_session_id = reschedule_to_session_id
    if is_extra is not None:
        session.is_extra = is_extra
    if topic is not None:
        session.topic = topic
    if summary is not None:
        session.summary = summary
    if teacher is not None:
        session.teacher = teacher
    
    db.session.commit()
    return True


def cancel_session(session_id: int, reason: str) -> bool:
    """Cancel a session with a reason.
    
    Returns:
        True if canceled, False if session not found
    """
    session = ClassSession.query.get(session_id)
    if not session:
        return False
    session.status = 'canceled'
    session.cancel_reason = reason
    db.session.commit()
    return True


def mark_session_held(session_id: int) -> bool:
    """Mark a session as held (completed).
    
    Returns:
        True if updated, False if session not found
    """
    session = ClassSession.query.get(session_id)
    if not session:
        return False
    session.status = 'held'
    db.session.commit()
    return True


def delete_session(session_id: int) -> bool:
    """Delete a session.
    
    Returns:
        True if deleted, False if session not found
    """
    session = ClassSession.query.get(session_id)
    if not session:
        return False
    db.session.delete(session)
    db.session.commit()
    return True


# ==================== SessionScore DAO ====================

def create_score(
    session_id: int,
    student_id: int,
    score_type: str,
    score: Optional[float] = None,
    comment: Optional[str] = None,
    recorded_by: str = 'web',
) -> int:
    """Create a new score record.
    
    Args:
        session_id: The session ID
        student_id: The student ID
        score_type: Score type (Q/T/C/M1/M2/N)
        score: Score value (0-5, 0 means absent for Q type)
        comment: Optional comment
        recorded_by: Who recorded the score
    
    Returns:
        The created score ID
    """
    score_record = SessionScore(
        session_id=session_id,
        student_id=student_id,
        score_type=score_type,
        score=score,
        comment=comment,
        recorded_by=recorded_by,
    )
    db.session.add(score_record)
    db.session.commit()
    return score_record.id


def get_score(score_id: int) -> Optional[SessionScore]:
    """Get a score by ID."""
    return SessionScore.query.get(score_id)


def list_scores_for_session(session_id: int) -> List[SessionScore]:
    """List all scores for a session."""
    return SessionScore.query.filter_by(session_id=session_id).all()


def list_scores_for_student(student_id: int, limit: Optional[int] = None) -> List[SessionScore]:
    """List scores for a student.
    
    Args:
        student_id: The student ID
        limit: Optional limit on results
    
    Returns:
        List of scores ordered by session date (newest first)
    """
    q = SessionScore.query.filter_by(student_id=student_id)\
        .join(ClassSession)\
        .order_by(ClassSession.session_date.desc(), SessionScore.created_at.desc())
    if limit:
        q = q.limit(limit)
    return q.all()


def list_scores_for_class(
    class_id: int,
    session_id: Optional[int] = None,
    student_id: Optional[int] = None,
    score_type: Optional[str] = None,
) -> List[SessionScore]:
    """List scores for a class with optional filters.
    
    Args:
        class_id: The class ID
        session_id: Optional session filter
        student_id: Optional student filter
        score_type: Optional score type filter
    
    Returns:
        List of scores
    """
    q = SessionScore.query.join(ClassSession).filter(ClassSession.class_id == class_id)
    
    if session_id:
        q = q.filter(SessionScore.session_id == session_id)
    if student_id:
        q = q.filter(SessionScore.student_id == student_id)
    if score_type:
        q = q.filter(SessionScore.score_type == score_type)
    
    return q.order_by(ClassSession.session_date.desc(), SessionScore.created_at.desc()).all()


def update_score(
    score_id: int,
    score: Optional[float] = None,
    comment: Optional[str] = None,
) -> bool:
    """Update a score record.
    
    Returns:
        True if updated, False if score not found
    """
    score_record = SessionScore.query.get(score_id)
    if not score_record:
        return False
    
    if score is not None:
        score_record.score = score
    if comment is not None:
        score_record.comment = comment
    
    db.session.commit()
    return True


def delete_score(score_id: int) -> bool:
    """Delete a score record.
    
    Returns:
        True if deleted, False if score not found
    """
    score_record = SessionScore.query.get(score_id)
    if not score_record:
        return False
    db.session.delete(score_record)
    db.session.commit()
    return True


def batch_create_scores(
    session_id: int,
    scores: List[Dict[str, Any]],
    recorded_by: str = 'web',
) -> List[int]:
    """Create multiple score records in a single transaction.
    
    Args:
        session_id: The session ID
        scores: List of dicts with keys: student_id, score_type, score, comment
        recorded_by: Who recorded the scores
    
    Returns:
        List of created score IDs
    """
    created_ids = []
    with transaction():
        for s in scores:
            score_record = SessionScore(
                session_id=session_id,
                student_id=s['student_id'],
                score_type=s['score_type'],
                score=s.get('score'),
                comment=s.get('comment'),
                recorded_by=recorded_by,
            )
            db.session.add(score_record)
            db.session.flush()  # Get the ID without committing
            created_ids.append(score_record.id)
    return created_ids


# ==================== Statistics & Query Helpers ====================

def get_student_attendance_summary(student_id: int, class_id: Optional[int] = None) -> Dict[str, Any]:
    """Get attendance summary for a student.

    Returns:
        Dict with keys: total_sessions, attended, absent, makeup, rate
    """
    from sqlalchemy import and_
    
    q = db.session.query(
        db.func.count(db.distinct(ClassSession.id)).label('total_sessions'),
        db.func.sum(db.case(
            (SessionScore.score_type == 'Q', 1),
            else_=0,
        )).label('q_records'),
        db.func.sum(db.case(
            (and_(SessionScore.score_type == 'Q', SessionScore.score == 5), 1),
            else_=0,
        )).label('attended'),
        db.func.sum(db.case(
            (and_(SessionScore.score_type == 'Q', SessionScore.score == 0), 1),
            else_=0,
        )).label('absent'),
        db.func.sum(db.case(
            (and_(SessionScore.score_type == 'Q', SessionScore.score == 3), 1),
            else_=0,
        )).label('makeup'),
    ).select_from(SessionScore)\
     .join(ClassSession)\
     .filter(SessionScore.student_id == student_id)\
     .filter(ClassSession.status == 'held')

    if class_id:
        q = q.filter(ClassSession.class_id == class_id)

    result = q.first()

    total = result.total_sessions or 0
    attended = result.attended or 0
    absent = result.absent or 0
    makeup = result.makeup or 0
    rate = (attended + makeup) / total if total > 0 else 0.0

    return {
        'total_sessions': total,
        'attended': attended,
        'absent': absent,
        'makeup': makeup,
        'rate': rate,
    }


def get_class_session_stats(class_id: int) -> Dict[str, Any]:
    """Get session statistics for a class.

    Returns:
        Dict with session counts by status
    """
    q = db.session.query(
        db.func.count(ClassSession.id).label('total'),
        db.func.sum(db.case((ClassSession.status == 'held', 1), else_=0)).label('held'),
        db.func.sum(db.case((ClassSession.status == 'scheduled', 1), else_=0)).label('scheduled'),
        db.func.sum(db.case((ClassSession.status == 'canceled', 1), else_=0)).label('canceled'),
        db.func.sum(db.case((ClassSession.status == 'rescheduled', 1), else_=0)).label('rescheduled'),
    ).filter(ClassSession.class_id == class_id).first()

    return {
        'total': q.total or 0,
        'held': q.held or 0,
        'scheduled': q.scheduled or 0,
        'canceled': q.canceled or 0,
        'rescheduled': q.rescheduled or 0,
    }


def get_score_type_stats(
    class_id: int,
    score_type: str,
    session_id: Optional[int] = None,
) -> Dict[str, float]:
    """Get statistics for a specific score type in a class.
    
    Returns:
        Dict with avg, min, max scores
    """
    q = db.session.query(
        db.func.avg(SessionScore.score).label('avg'),
        db.func.min(SessionScore.score).label('min'),
        db.func.max(SessionScore.score).label('max'),
    ).join(ClassSession).filter(
        ClassSession.class_id == class_id,
        SessionScore.score_type == score_type,
        ClassSession.status == 'held',
    )
    
    if session_id:
        q = q.filter(SessionScore.session_id == session_id)
    
    result = q.first()
    
    return {
        'avg': result.avg or 0.0,
        'min': result.min or 0.0,
        'max': result.max or 0.0,
    }
