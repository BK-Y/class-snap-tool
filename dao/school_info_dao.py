from db.models import Student
from db.student_school_info import StudentSchoolInfo
from db.sa_db import db
from datetime import datetime

def add_school_info(student_id, school_name, start_year, grade_at_entry, remark=None):
    # 旧记录全部设为非当前
    StudentSchoolInfo.query.filter_by(student_id=student_id, is_current=True).update({"is_current": False})
    info = StudentSchoolInfo(
        student_id=student_id,
        school_name=school_name,
        start_year=start_year,
        grade_at_entry=grade_at_entry,
        is_current=True,
        changed_at=datetime.utcnow(),
        remark=remark
    )
    db.session.add(info)
    db.session.commit()
    return info.id

def get_current_school_info(student_id):
    return StudentSchoolInfo.query.filter_by(student_id=student_id, is_current=True).first()

def get_school_history(student_id):
    return StudentSchoolInfo.query.filter_by(student_id=student_id).order_by(StudentSchoolInfo.changed_at.desc()).all()

def calc_current_grade(start_year, grade_at_entry, current_year=None):
    # 假设小学一年级、二年级...，年级顺序可自定义
    grade_order = ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级"]
    if current_year is None:
        from datetime import datetime
        current_year = datetime.now().year
    try:
        idx = grade_order.index(grade_at_entry)
        offset = current_year - start_year
        new_idx = idx + offset
        if new_idx < len(grade_order):
            return grade_order[new_idx]
        else:
            return "已毕业"
    except Exception:
        return grade_at_entry
