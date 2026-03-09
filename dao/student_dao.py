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
    legal_name: Optional[str] = None,
    doc_type: Optional[str] = None,
    doc_number: Optional[str] = None,
    gender: Optional[str] = None,
    birthday: Optional[str] = None,
) -> int:
    """创建学生记录"""
    student_number_value = student_number.strip()
    doc_type_value = _clean_optional(doc_type) or ""
    doc_number_value = _clean_optional(doc_number) or f"AUTO-{student_number_value}"

    cursor = conn.execute("""
        INSERT INTO students (
            student_number, display_name, legal_name,
            doc_type, doc_number, gender, birthday
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        student_number_value,
        display_name.strip(),
        _clean_optional(legal_name),
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
    legal_name: Optional[str] = None,
    gender: Optional[str] = None,
    birthday: Optional[str] = None,
    doc_type: Optional[str] = None,
    doc_number: Optional[str] = None,
) -> None:
    """按学号更新学生信息"""
    student_number_value = student_number.strip()
    doc_type_value = _clean_optional(doc_type) or ""
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
            _clean_optional(legal_name),
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
    class_id: int = None,
    limit: int = None,
    offset: int = None,
) -> List[sqlite3.Row]:
    """统一查询接口，支持按班级筛选（通过enrollments）。"""
    where_clauses = []
    params = []
    joins = []

    if class_id is not None:
        joins.append("JOIN enrollments e ON e.student_id = students.id")
        where_clauses.append("e.class_id = ?")
        params.append(class_id)

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

    sql = "SELECT students.* FROM students"
    if joins:
        sql += " " + " ".join(joins)
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    sql += " ORDER BY students.id"

    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    if offset:
        sql += " OFFSET ?"
        params.append(offset)

    cursor = conn.execute(sql, params)
    return cursor.fetchall()


def add_student_document(conn: sqlite3.Connection, student_id: int, doc_type: str, doc_number: str, is_primary: bool = False) -> int:
    """为学生添加证件，若 is_primary=True，自动取消其他主证件"""
    if is_primary:
        conn.execute(
            "UPDATE student_documents SET is_primary=0 WHERE student_id=?",
            (student_id,)
        )
    cursor = conn.execute(
        """
        INSERT INTO student_documents (student_id, doc_type, doc_number, is_primary)
        VALUES (?, ?, ?, ?)
        """,
        (student_id, doc_type.strip(), doc_number.strip(), int(is_primary))
    )
    return cursor.lastrowid

def update_student_document(conn: sqlite3.Connection, doc_id: int, doc_type: str, doc_number: str, is_primary: bool = False) -> None:
    """更新证件信息，若 is_primary=True，自动取消其他主证件"""
    student_id = conn.execute("SELECT student_id FROM student_documents WHERE id=?", (doc_id,)).fetchone()[0]
    if is_primary:
        conn.execute(
            "UPDATE student_documents SET is_primary=0 WHERE student_id=?",
            (student_id,)
        )
    conn.execute(
        """
        UPDATE student_documents
        SET doc_type=?, doc_number=?, is_primary=?
        WHERE id=?
        """,
        (doc_type.strip(), doc_number.strip(), int(is_primary), doc_id)
    )

def delete_student_document(conn: sqlite3.Connection, doc_id: int) -> None:
    """删除指定证件"""
    conn.execute("DELETE FROM student_documents WHERE id=?", (doc_id,))

def list_student_documents(conn: sqlite3.Connection, student_id: int) -> list:
    """获取学生所有证件，主证件优先"""
    cursor = conn.execute(
        "SELECT * FROM student_documents WHERE student_id=? ORDER BY is_primary DESC, id ASC",
        (student_id,)
    )
    return cursor.fetchall()

# =================================================================
# 证件类型相关
# =================================================================

def list_doc_types(conn: sqlite3.Connection) -> list:
    """返回所有证件类型记录，作为字典列表"""
    cursor = conn.execute("SELECT type_code,label FROM doc_types ORDER BY id")
    return cursor.fetchall()


def add_doc_type(conn: sqlite3.Connection, type_code: str, label: str) -> int:
    """如果类型不存在则添加并返回 id，否则返回已有 id"""
    type_code = type_code.strip()
    label = label.strip()
    if not type_code or not label:
        raise ValueError("类型和标签不能为空")
    cur = conn.execute("SELECT id FROM doc_types WHERE type_code=?", (type_code,))
    row = cur.fetchone()
    if row:
        return row[0]
    cursor = conn.execute(
        "INSERT INTO doc_types (type_code,label) VALUES (?,?)",
        (type_code, label)
    )
    return cursor.lastrowid

def set_primary_document(conn: sqlite3.Connection, doc_id: int) -> None:
    """将指定证件设为主证件（自动取消其他主证件）"""
    row = conn.execute("SELECT student_id FROM student_documents WHERE id=?", (doc_id,)).fetchone()
    if not row:
        raise ValueError("证件不存在")
    student_id = row[0]
    conn.execute("UPDATE student_documents SET is_primary=0 WHERE student_id=?", (student_id,))
    conn.execute("UPDATE student_documents SET is_primary=1 WHERE id=?", (doc_id,))
