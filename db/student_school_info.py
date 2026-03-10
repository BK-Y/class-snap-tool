from db.sa_db import db
from datetime import datetime

class StudentSchoolInfo(db.Model):
    __tablename__ = 'student_school_info'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    school_name = db.Column(db.String(128), nullable=False)
    start_year = db.Column(db.Integer, nullable=False)
    grade_at_entry = db.Column(db.String(32), nullable=False)  # 如“一年级”
    is_current = db.Column(db.Boolean, default=True)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    remark = db.Column(db.String(128))

    student = db.relationship('Student', backref=db.backref('school_infos', lazy=True))
