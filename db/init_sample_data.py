# db/init_sample_data.py
import sqlite3
from pathlib import Path

def init_sample_data():
    """
    插入初始测试数据（避免首次运行为空）
    """
    db_path = Path(__file__).parent.parent / "data" / "school.db"
    conn = sqlite3.connect(db_path)
    try:
        # 插入 5 名测试学生
        conn.execute("""
            INSERT OR IGNORE INTO students (
                display_name, student_number, legal_name,
                doc_type, doc_number
            ) VALUES 
                ('小明', '20230001', '张小明', 'ID_CARD', '110101200001011234'),
                ('小红', '20230002', '李小红', 'ID_CARD', '110101200001011235'),
                ('小刚', '20230003', '王小刚', 'ID_CARD', '110101200001011236'),
                ('莉莉', '20230004', '陈莉莉', 'ID_CARD', '110101200001011237'),
                ('天天', '20230005', '刘天天', 'ID_CARD', '110101200001011238')
        """)

        # 插入一个测试班级
        conn.execute("""
            INSERT OR IGNORE INTO classes (type, level, group_number)
            VALUES ('启蒙', 'L1', 1)
        """)

        conn.commit()
        print("✅ 示例数据插入成功")
    finally:
        conn.close()

