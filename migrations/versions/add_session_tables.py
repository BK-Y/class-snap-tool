"""add session tables: schedule patterns, sessions, scores

Revision ID: add_session_tables
Revises: add_doc_name
Create Date: 2026-03-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_session_tables'
down_revision = 'add_doc_name'
branch_labels = None
depends_on = None


def upgrade():
    # 使用批处理模式以支持 SQLite 的 IF NOT EXISTS
    with op.batch_alter_table('classes', schema=None) as batch_op:
        pass  # 仅用于启用批处理模式
    
    # 1. 创建排课规则表 class_schedule_patterns (如果不存在)
    op.execute('''
        CREATE TABLE IF NOT EXISTS class_schedule_patterns (
            id INTEGER NOT NULL PRIMARY KEY,
            class_id INTEGER NOT NULL,
            weekday INTEGER NOT NULL,
            start_time VARCHAR(5) NOT NULL,
            end_time VARCHAR(5) NOT NULL,
            repeat_interval INTEGER DEFAULT 1,
            valid_from DATE,
            valid_to DATE,
            note VARCHAR(128),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            FOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE CASCADE,
            CONSTRAINT check_weekday_range CHECK (weekday >= 0 AND weekday <= 6),
            CONSTRAINT check_repeat_interval_positive CHECK (repeat_interval >= 1)
        )
    ''')

    # 2. 创建实际课次表 class_sessions (如果不存在)
    op.execute('''
        CREATE TABLE IF NOT EXISTS class_sessions (
            id INTEGER NOT NULL PRIMARY KEY,
            class_id INTEGER NOT NULL,
            schedule_pattern_id INTEGER,
            session_date DATE NOT NULL,
            start_time VARCHAR(5),
            end_time VARCHAR(5),
            session_index INTEGER,
            session_stage VARCHAR(32),
            status VARCHAR(16) DEFAULT 'scheduled' NOT NULL,
            cancel_reason VARCHAR(128),
            reschedule_to_session_id INTEGER,
            is_extra BOOLEAN DEFAULT 0,
            topic VARCHAR(128),
            summary TEXT,
            teacher VARCHAR(64),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            FOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE CASCADE,
            FOREIGN KEY(schedule_pattern_id) REFERENCES class_schedule_patterns (id) ON DELETE SET NULL,
            FOREIGN KEY(reschedule_to_session_id) REFERENCES class_sessions (id) ON DELETE SET NULL,
            CONSTRAINT check_session_status CHECK (status IN ('scheduled', 'held', 'canceled', 'rescheduled'))
        )
    ''')

    # 3. 创建打分明细表 session_scores (如果不存在)
    op.execute('''
        CREATE TABLE IF NOT EXISTS session_scores (
            id INTEGER NOT NULL PRIMARY KEY,
            session_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            score_type VARCHAR(8) NOT NULL,
            score FLOAT,
            comment TEXT,
            recorded_by VARCHAR(32) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            FOREIGN KEY(session_id) REFERENCES class_sessions (id) ON DELETE CASCADE,
            FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE,
            CONSTRAINT check_score_type CHECK (score_type IN ('Q', 'T', 'C', 'M1', 'M2', 'N')),
            CONSTRAINT check_score_range CHECK (score >= 0 AND score <= 5)
        )
    ''')

    # 4. 为常用查询创建索引 (如果不存在)
    op.execute('CREATE INDEX IF NOT EXISTS ix_sessions_class_date ON class_sessions (class_id, session_date)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_sessions_status ON class_sessions (status)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_scores_session ON session_scores (session_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_scores_student ON session_scores (student_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_patterns_class ON class_schedule_patterns (class_id)')


def downgrade():
    op.drop_index('ix_patterns_class', table_name='class_schedule_patterns')
    op.drop_index('ix_scores_student', table_name='session_scores')
    op.drop_index('ix_scores_session', table_name='session_scores')
    op.drop_index('ix_sessions_status', table_name='class_sessions')
    op.drop_index('ix_sessions_class_date', table_name='class_sessions')
    
    op.drop_table('session_scores')
    op.drop_table('class_sessions')
    op.drop_table('class_schedule_patterns')
