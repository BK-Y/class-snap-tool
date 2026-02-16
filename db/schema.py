# db/schema.py
import sqlite3
from pathlib import Path

def init_db():
    """
    初始化数据库表结构（执行 schema.sql）
    """
    db_path = Path(__file__).parent.parent / ".data" / "school.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        # 读取并执行 schema.sql（假设它在项目根目录）
        schema_file = Path(__file__).parent / "schema.sql"
        if not schema_file.exists():
            raise FileNotFoundError(f"未找到 schema.sql: {schema_file}")

        with open(schema_file, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # 清理注释和空行（防执行失败）
        cleaned_sql = "\n".join(
            line for line in sql_content.split("\n")
            if line.strip() and not line.strip().startswith("--")
        )

        conn.executescript(cleaned_sql)
        conn.commit()
        print(f"✅ 表结构初始化成功：{db_path}")
    except sqlite3.Error as e:
        print(f"❌ 建表失败：{e}")
        raise
    finally:
        conn.close()
