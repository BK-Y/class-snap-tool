from db.models import Student, StudentDocument, DocType
from db.sa_db import db
from sqlalchemy import or_
from datetime import datetime

def generate_student_number(prefix: str = "") -> str:
    year = datetime.now().year
    prefix_year = f"{prefix}{year}"
    last = Student.query.filter(Student.student_number.like(f"{prefix_year}%")) \
        .order_by(Student.student_number.desc()).first()
    if last and last.student_number[-4:].isdigit():
        new_num = int(last.student_number[-4:]) + 1
    else:
        new_num = 1
    return f"{prefix_year}{new_num:04d}"

def create_student(student_number, display_name, legal_name=None, gender=None, birthday=None):
    student = Student(
        student_number=student_number,
        display_name=display_name,
        gender=gender,
        birthday=birthday
    )
    db.session.add(student)
    db.session.commit()
    return student.id

def search_students(student_number=None, display_name=None, legal_name=None, gender=None, class_id=None, limit=None, offset=None):
    q = Student.query
    if student_number:
        q = q.filter_by(student_number=student_number)
    if display_name:
        q = q.filter(Student.display_name.like(f"%{display_name}%"))
    if gender:
        q = q.filter_by(gender=gender)
    # class_id 过滤略，需 join Enrollment
    if limit:
        q = q.limit(limit)
    if offset:
        q = q.offset(offset)
    return q.all()

def list_student_documents(student_id):
    return StudentDocument.query.filter_by(student_id=student_id).order_by(StudentDocument.is_primary.desc(), StudentDocument.id.asc()).all()

def add_student_document(student_id, doc_type, doc_number, is_primary=False):
    if is_primary:
        StudentDocument.query.filter_by(student_id=student_id).update({"is_primary": False})
    doc = StudentDocument(student_id=student_id, doc_type=doc_type, doc_number=doc_number, is_primary=is_primary)
    db.session.add(doc)
    db.session.commit()
    return doc.id

def list_doc_types():
    return DocType.query.order_by(DocType.id).all()

def add_doc_type(type_code, label):
    doc_type = DocType.query.filter_by(type_code=type_code).first()
    if doc_type:
        return doc_type.id
    doc_type = DocType(type_code=type_code, label=label)
    db.session.add(doc_type)
    db.session.commit()
    return doc_type.id

def update_student(student_number, display_name=None, legal_name=None, gender=None, birthday=None):
    student = Student.query.filter_by(student_number=student_number).first()
    if not student:
        return None
    if display_name is not None:
        student.display_name = display_name
    if gender is not None:
        student.gender = gender
    if birthday is not None:
        student.birthday = birthday
    db.session.commit()
    return student.id

def update_student_document(doc_id, doc_type, doc_number, is_primary=False):
    doc = StudentDocument.query.get(doc_id)
    if not doc:
        return None
    doc.doc_type = doc_type
    doc.doc_number = doc_number
    doc.is_primary = is_primary
    db.session.commit()
    return doc.id

def delete_student_document(doc_id):
    doc = StudentDocument.query.get(doc_id)
    if not doc:
        return False
    db.session.delete(doc)
    db.session.commit()
    return True

def set_primary_document(student_id, doc_id):
    # 先将所有证件 is_primary 设为 False
    StudentDocument.query.filter_by(student_id=student_id).update({"is_primary": False})
    # 再将指定证件 is_primary 设为 True
    doc = StudentDocument.query.get(doc_id)
    if not doc:
        return False
    doc.is_primary = True
    db.session.commit()
    return True
