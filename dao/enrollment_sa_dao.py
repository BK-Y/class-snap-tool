from db.models import Enrollment, EnrollmentLog, Student, Class
from db.sa_db import db
from sqlalchemy import desc
from datetime import datetime

def list_students_in_class(class_id):
    return (
        db.session.query(Student, Enrollment.enrolled_at)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .filter(Enrollment.class_id == class_id)
        .order_by(Student.student_number)
        .all()
    )

def enroll_student(class_id, student_id, operator_id='system', reason=None, source='web', request_id=None):
    # 添加报名关系
    e = Enrollment(student_id=student_id, class_id=class_id, enrolled_at=datetime.now())
    db.session.add(e)
    db.session.commit()
    # 添加日志
    log = EnrollmentLog(
        student_id=student_id, class_id=class_id, event_type='JOIN', event_time=datetime.now(),
        operator_id=operator_id, reason=reason, source=source, request_id=request_id,
        student_number_snapshot=Student.query.get(student_id).student_number,
        student_name_snapshot=Student.query.get(student_id).display_name
    )
    db.session.add(log)
    db.session.commit()
    return e

def remove_student(class_id, student_id, operator_id='system', reason=None, source='web', request_id=None):
    Enrollment.query.filter_by(class_id=class_id, student_id=student_id).delete()
    db.session.commit()
    log = EnrollmentLog(
        student_id=student_id, class_id=class_id, event_type='LEAVE', event_time=datetime.now(),
        operator_id=operator_id, reason=reason, source=source, request_id=request_id,
        student_number_snapshot=Student.query.get(student_id).student_number,
        student_name_snapshot=Student.query.get(student_id).display_name
    )
    db.session.add(log)
    db.session.commit()

def list_classes_for_student(student_id):
    return (
        db.session.query(Class, Enrollment.enrolled_at)
        .join(Enrollment, Enrollment.class_id == Class.id)
        .filter(Enrollment.student_id == student_id)
        .order_by(Class.type, Class.level, Class.group_number)
        .all()
    )

def list_enrollment_logs_by_class(class_id, limit=50):
    return EnrollmentLog.query.filter_by(class_id=class_id).order_by(desc(EnrollmentLog.id)).limit(limit).all()
