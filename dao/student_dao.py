from typing import List, Dict, Any, Optional, Literal
import sqlite3
import datetime

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
    doc_type: str,
    doc_number: str,
    gender: Optional[str] = None,
) -> int:
    """创建学生记录"""
    cursor = conn.execute("""
        INSERT INTO students (
            student_number, display_name, legal_name,
            doc_type, doc_number, gender
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        student_number.strip(),
        display_name.strip(),
        legal_name.strip(),
        doc_type.strip(),
        doc_number.strip(),
        gender.strip() 
    ))
    return cursor.lastrowid 
   

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
