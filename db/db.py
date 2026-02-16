# db.py
import sqlite3
import os
from flask import g

# 数据库路径：放在 instance/ 目录下（Flask 推荐）
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'school.db')

def get_db():
    """
    获取当前请求的数据库连接。
    如果没有连接，则创建一个新连接并存入 Flask 的 g 对象。
    """
    if 'db' not in g:
        # 确保 instance/ 目录存在
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        # 连接数据库，启用 Row 工厂（可通过列名访问）
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """
    关闭数据库连接（Flask teardown 钩子调用）。
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """
    初始化数据库：
    1. 执行 schema.sql 创建表
    2. 插入示例学生（避免下拉框为空）
    """
    # with current_app.app_context():
    db = get_db()
        
    
        # 读取 schema.sql 并执行
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"未找到 schema.sql 文件: {schema_path}")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        db.executescript(f.read())
        
    db.commit()
    
    # 插入测试学生（避免首次运行时学员列表为空）
    db.execute("""
        INSERT OR IGNORE INTO students (display_name) 
        VALUES ('小明'), ('小红'), ('小刚'), ('莉莉'), ('天天')
    """)
    
    # 可选：插入一个测试班级
    db.execute("""
        INSERT OR IGNORE INTO classes (type, level, group_number)
        VALUES ('启蒙', 'L1', 1)
    """)
    
    db.commit()
    print("✅ 数据库初始化成功！")
    print(f"   数据库位置: {DATABASE}")

def search_students(student_number=None,display_name=None,legal_name=None,doc_type=None, doc_number=None,gender=None):
    """ 
    根据条件搜索学生
    若参数为None则忽略该条件
    """
    db = get_db()
    query_parts = []
    params = []
    sql = "SELECT * FROM students WHERE 1=1"

    if student_number:
        query_parts.append("student_number = ?")
        params.append(student_number)

    if display_name:
        query_parts.append("display_name LIKE ?")
        params.append(f'%{display_name}%')

    if legal_name:
        query_parts.append("legal_name LIKE ?")
        params.append(f'%{legal_name}%')

    if doc_type:
        query_parts.append("doc_type = ?")
        params.append(doc_type)
        
    if doc_number:
        query_parts.append("doc_number = ?")
        params.append(doc_number)

    if gender:
        query_parts.append("gender LIKE ?")
        params.append(f'%{gender}%')

    if query_parts:
        sql += " AND " + " AND ".join(query_parts)

    sql += " ORDER BY display_name"

    return db.execute(sql,params).fetchall()

# =============== 非 Flask 环境使用（如命令行初始化）===============
if __name__ == '__main__':
    # 用于直接运行 python db.py 来初始化数据库
    init_db()
