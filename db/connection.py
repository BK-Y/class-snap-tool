import sqlite3
from  contextlib  import contextmanager
from pathlib import Path

def get_db_path() -> Path:
    """
    返回数据库文件路径：./.data/school.db
    自动创建 .data/ 目录（首次运行）
    """
    project_root = Path(__file__).parent.parent
    db_path = project_root / ".data" / "school.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path

@contextmanager
def get_db():
    """
    数据库连接上下文管理器（支持事务）
    用法：
        with get_db() as conn:
            conn.execute("INSERT ...")
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
    finally:
        conn.close()

def close_db(conn):
    """兼容旧 close_db() 签名（可选）"""
    if conn is not None:
        conn.close()
