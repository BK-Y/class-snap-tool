from typing import List, Dict, Any, Optional, Literal
import sqlite3

def search_students(
    conn: sqlite3.Connection,
    *,
    student_number: Optional[str] = None,
    display_name: Optional[str] = None,
    legal_name: Optional[str] = None,
    doc_type: Optional[str] = None,
    doc_number: Optional[str] = None,
    gender: Optional[str] = None,
    order_by: str = "display_name",
    order_direction: Literal["ASC", "DESC"] = "ASC",
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    搜索学生（DAO 层：安全、参数化、类型化）
    
    Args:
        conn: 数据库连接（由调用方提供）
        student_number: 精确匹配学号
        display_name: 模糊匹配常用称呼（不区分大小写）
        legal_name: 模糊匹配法定姓名（不区分大小写）
        doc_type/doc_number: 精确匹配证件
        gender: 模糊匹配性别（不区分大小写）
        order_by: 排序字段（id, student_number, display_name...）
        limit/offset: 分页支持
    
    Returns:
        List of student dicts (keys: id, student_number, display_name, gender, legal_name, doc_type, doc_number)
    """
    # 校验排序字段（防 SQL 注入）
    allowed_order = {"id", "student_number", "display_name", "legal_name", "gender", "doc_type", "doc_number"}
    if order_by not in allowed_order:
        raise ValueError(f"order_by 必须是 {sorted(allowed_order)}, 得到 '{order_by}'")

    where_clauses = []
    params = []

    def _add_clause(field: str, op: str, value: Any):
        where_clauses.append(f"{field} {op} ?")
        params.append(value)

    # 精确匹配字段
    if student_number and isinstance(student_number, str) and student_number.strip():
        _add_clause("student_number", "=", student_number.strip())
    if doc_type and isinstance(doc_type, str) and doc_type.strip():
        _add_clause("doc_type", "=", doc_type.strip())
    if doc_number and isinstance(doc_number, str) and doc_number.strip():
        _add_clause("doc_number", "=", doc_number.strip())

    # 模糊匹配（LOWER + LIKE，真正不区分大小写）
    if display_name and isinstance(display_name, str) and display_name.strip():
        _add_clause("LOWER(display_name)", "LIKE", f"%{display_name.strip().lower()}%")
    if legal_name and isinstance(legal_name, str) and legal_name.strip():
        _add_clause("LOWER(legal_name)", "LIKE", f"%{legal_name.strip().lower()}%")
    if gender and isinstance(gender, str) and gender.strip():
        _add_clause("LOWER(gender)", "LIKE", f"%{gender.strip().lower()}%")

    # 构建 SQL
    select_fields = ["id", "student_number", "display_name", "gender", "legal_name", "doc_type", "doc_number"]
    sql = f"SELECT {', '.join(select_fields)} FROM students"

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    sql += f" ORDER BY {order_by} {order_direction}"

    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    if offset is not None:
        sql += " OFFSET ?"
        params.append(offset)

    # 执行
    cursor = conn.cursor()
    cursor.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]
