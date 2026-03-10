from db.models import Class, Enrollment
from db.sa_db import db
from sqlalchemy import desc

def list_classes_with_counts():
    # 返回所有班级及学生数
    return (
        db.session.query(
            Class,
            db.func.count(Enrollment.student_id).label('student_count')
        )
        .outerjoin(Enrollment, Enrollment.class_id == Class.id)
        .group_by(Class.id, Class.type, Class.level, Class.group_number, Class.status)
        .order_by(desc(Class.id))
        .all()
    )

def create_class(class_type, level, group_number, status="active"):
    c = Class(type=class_type, level=level, group_number=group_number, status=status)
    db.session.add(c)
    db.session.commit()
    return c.id

def get_class_by_id(class_id):
    return Class.query.get(class_id)
