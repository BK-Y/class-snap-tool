from db.sa_db import db

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(32), unique=True, nullable=False)
    display_name = db.Column(db.String(64), nullable=False)
    gender = db.Column(db.String(8))
    birthday = db.Column(db.String(16))
    birthday_cal = db.Column(db.String(8))
    # 证件信息迁移到 student_documents
    documents = db.relationship('StudentDocument', backref='student', cascade="all, delete-orphan")

class StudentDocument(db.Model):
    __tablename__ = 'student_documents'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    doc_type = db.Column(db.String(32), nullable=False)
    doc_number = db.Column(db.String(64), nullable=False)
    # 新字段：证件上显示的姓名
    doc_name = db.Column(db.String(64), nullable=True)
    is_primary = db.Column(db.Boolean, default=False)
    __table_args__ = (db.UniqueConstraint('student_id', 'doc_type'),)

class DocType(db.Model):
    __tablename__ = 'doc_types'
    id = db.Column(db.Integer, primary_key=True)
    type_code = db.Column(db.String(32), unique=True, nullable=False)
    label = db.Column(db.String(32), nullable=False)

class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(32), nullable=False)
    level = db.Column(db.String(32), nullable=False)
    group_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(16), default='active')
    # additional metadata
    teacher = db.Column(db.String(64), nullable=True)
    class_time = db.Column(db.String(64), nullable=True)  # e.g. 周二 18:00-20:00
    start_date = db.Column(db.String(32), nullable=True)  # e.g. 2026-03-15
    __table_args__ = (db.UniqueConstraint('type', 'level', 'group_number'),)

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), primary_key=True)
    enrolled_at = db.Column(db.DateTime)

class EnrollmentLog(db.Model):
    __tablename__ = 'enrollment_logs'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    event_type = db.Column(db.String(8), nullable=False)
    event_time = db.Column(db.DateTime)
    operator_id = db.Column(db.String(32), nullable=False)
    reason = db.Column(db.String(128))
    source = db.Column(db.String(16), default='web')
    request_id = db.Column(db.String(64))
    student_number_snapshot = db.Column(db.String(32))
    student_name_snapshot = db.Column(db.String(64))

class LearningRecord(db.Model):
    __tablename__ = 'learning_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    academic_year = db.Column(db.String(16), nullable=False)
    term = db.Column(db.String(8))
    record_type = db.Column(db.String(16), default='general')
    content = db.Column(db.Text, nullable=False)
    score = db.Column(db.Float)
    recorded_by = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime)

class StudentOperationLog(db.Model):
    __tablename__ = 'student_operation_logs'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    operator_id = db.Column(db.String(32), nullable=False)
    operation_time = db.Column(db.DateTime)
    operation_type = db.Column(db.String(8), nullable=False)
    field_name = db.Column(db.String(32))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    remark = db.Column(db.String(128))
