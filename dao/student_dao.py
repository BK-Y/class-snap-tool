from typing import List, Optional
import sqlite3
import datetime


def _clean_optional(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None

def generate_student_number(conn: sqlite3.Connection, prefix: str = "") -> str:
    """自动生成学号（年份 + 序号）"""
    year = datetime.datetime.now().year
    prefix_year = f"{prefix}{year}"
    
    cursor = conn.execute("""
        SELECT student_number FROM students 
        WHERE student_number LIKE ? 
        ORDER BY student_number DESC 
        LIMIT 1
    """, (f"{prefix_year}%",))
    
    row = cursor.fetchone()
    if row:
        last_num = int(row['student_number'][-4:])
        new_num = last_num + 1
    else:
        new_num = 1
    
    return f"{prefix_year}{new_num:04d}"

def create_student(
    conn: sqlite3.Connection,
    student_number: str,
    display_name: str,
    legal_name: str,
    doc_type: Optional[str],
    doc_number: Optional[str],
    gender: Optional[str] = None,
    birthday: Optional[str] = None,
) -> int:
    """创建学生记录"""
    student_number_value = student_number.strip()
    doc_type_value = _clean_optional(doc_type) or "OTHER"
    doc_number_value = _clean_optional(doc_number) or f"AUTO-{student_number_value}"

    cursor = conn.execute("""
        INSERT INTO students (
            student_number, display_name, legal_name,
            doc_type, doc_number, gender, birthday
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        student_number_value,
        display_name.strip(),
        legal_name.strip(),
        doc_type_value,
        doc_number_value,
        _clean_optional(gender),
        _clean_optional(birthday),
    ))
    return cursor.lastrowid


def update_student(
    conn: sqlite3.Connection,
    student_number: str,
    *,
    display_name: str,
    legal_name: str,
    gender: Optional[str] = None,
    birthday: Optional[str] = None,
    doc_type: Optional[str] = None,
    doc_number: Optional[str] = None,
) -> None:
    """按学号更新学生信息"""
    student_number_value = student_number.strip()
    doc_type_value = _clean_optional(doc_type) or "OTHER"
    doc_number_value = _clean_optional(doc_number) or f"AUTO-{student_number_value}"

    conn.execute(
        """
        UPDATE students
        SET display_name = ?,
            legal_name = ?,
            gender = ?,
            birthday = ?,
            doc_type = ?,
            doc_number = ?
        WHERE student_number = ?
        """,
        (
            display_name.strip(),
            legal_name.strip(),
            _clean_optional(gender),
            _clean_optional(birthday),
            doc_type_value,
            doc_number_value,
            student_number_value,
        ),
    )

def search_students(
    conn: sqlite3.Connection,
    *,
    student_number: str = None,
    display_name: str = None,
    legal_name: str = None,
    doc_type: str = None,
    doc_number: str = None,
    gender: str = None,
    limit: int = None,
    offset: int = None,
) -> List[sqlite3.Row]:
    """统一查询接口"""
    where_clauses = []
    params = []
    
    
    if student_number is not None:
        where_clauses.append("student_number = ?")
        params.append(student_number.strip())
    
    if display_name:
        where_clauses.append("display_name LIKE ?")
        params.append(f"%{display_name.strip()}%")
    
    if legal_name:
        where_clauses.append("legal_name LIKE ?")
        params.append(f"%{legal_name.strip()}%")
    
    if doc_type:
        where_clauses.append("doc_type = ?")
        params.append(doc_type.strip())
    
    if doc_number:
        where_clauses.append("doc_number = ?")
        params.append(doc_number.strip())
    
    if gender:
        where_clauses.append("gender = ?")
        params.append(gender.strip())
    
    sql = "SELECT * FROM students"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    sql += " ORDER BY id"
    
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    if offset:
        sql += " OFFSET ?"
        params.append(offset)
    
    cursor = conn.execute(sql, params)
    return cursor.fetchall() 
