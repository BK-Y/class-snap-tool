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
    # 当数据库尚未添加 doc_name 字段时，避免查询崩溃
    try:
        return StudentDocument.query.filter_by(student_id=student_id)\
            .order_by(StudentDocument.is_primary.desc(), StudentDocument.id.asc()).all()
    except Exception as e:
        # sqlite 抛出的错误信息会包含 no such column
        if 'no such column' in str(e):
            # 退回到不含 doc_name 的原始查询（使用 raw SQL）
            from sqlalchemy import text
            sql = text("SELECT id, student_id, doc_type, doc_number, is_primary FROM student_documents WHERE student_id=:sid ORDER BY is_primary DESC, id ASC")
            rows = db.session.execute(sql, {'sid': student_id}).fetchall()
            # 手动构造简单对象零钱返回
            class Tmp:
                def __getitem__(self, key):
                    return getattr(self, key)
            docs = []
            for r in rows:
                obj = Tmp()
                # row is a tuple in fallback mode
                obj.id = r[0]
                obj.student_id = r[1]
                obj.doc_type = r[2]
                obj.doc_number = r[3]
                obj.is_primary = r[4]
                obj.doc_name = None
                docs.append(obj)
            return docs
        raise

def add_student_document(student_id, doc_type, doc_number, doc_name=None, is_primary=False):
    if is_primary:
        StudentDocument.query.filter_by(student_id=student_id).update({"is_primary": False})
    doc = StudentDocument(
        student_id=student_id,
        doc_type=doc_type,
        doc_number=doc_number,
        doc_name=doc_name,
        is_primary=is_primary
    )
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

def update_student_document(doc_id, doc_type, doc_number, doc_name=None, is_primary=False):
    doc = StudentDocument.query.get(doc_id)
    if not doc:
        return None
    if is_primary:
        # clear any other primary documents for this student
        StudentDocument.query.filter(
            StudentDocument.student_id == doc.student_id,
            StudentDocument.id != doc_id
        ).update({"is_primary": False})
    doc.doc_type = doc_type
    doc.doc_number = doc_number
    if doc_name is not None:
        doc.doc_name = doc_name
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
