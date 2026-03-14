"""add pattern history table and version fields

Revision ID: add_pattern_history
Revises: add_session_tables
Create Date: 2026-03-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_pattern_history'
down_revision = 'add_session_tables'
branch_labels = None
depends_on = None


def upgrade():
    # 1. 创建排课规则修改历史表
    op.execute('''
        CREATE TABLE IF NOT EXISTS class_schedule_pattern_history (
            id INTEGER NOT NULL PRIMARY KEY,
            pattern_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            old_weekday INTEGER,
            old_start_time VARCHAR(5),
            old_end_time VARCHAR(5),
            old_repeat_interval INTEGER,
            old_valid_from DATE,
            old_valid_to DATE,
            old_note VARCHAR(128),
            new_weekday INTEGER,
            new_start_time VARCHAR(5),
            new_end_time VARCHAR(5),
            new_repeat_interval INTEGER,
            new_valid_from DATE,
            new_valid_to DATE,
            new_note VARCHAR(128),
            change_reason VARCHAR(256),
            changed_by VARCHAR(32),
            changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            affected_sessions_count INTEGER DEFAULT 0,
            FOREIGN KEY(pattern_id) REFERENCES class_schedule_patterns (id) ON DELETE CASCADE,
            FOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE CASCADE
        )
    ''')
    
    # 2. 为历史表创建索引
    op.execute('CREATE INDEX IF NOT EXISTS ix_history_pattern ON class_schedule_pattern_history (pattern_id, changed_at)')
    
    # 3. 为排课规则表添加版本控制字段（如果不存在）
    # SQLite 无法直接检查列是否存在，我们使用尝试创建的方式
    try:
        with op.batch_alter_table('class_schedule_patterns', schema=None) as batch_op:
            batch_op.add_column(sa.Column('version', sa.Integer(), nullable=True, server_default='1'))
    except Exception:
        pass  # 列已存在
    
    try:
        with op.batch_alter_table('class_schedule_patterns', schema=None) as batch_op:
            batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'))
    except Exception:
        pass
    
    try:
        with op.batch_alter_table('class_schedule_patterns', schema=None) as batch_op:
            batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
    except Exception:
        pass
    
    # 更新现有记录的 version 和 is_active
    op.execute("UPDATE class_schedule_patterns SET version = 1, is_active = 1 WHERE version IS NULL")


def downgrade():
    with op.batch_alter_table('class_schedule_patterns', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('is_active')
        batch_op.drop_column('version')
    
    op.drop_index('ix_history_pattern', table_name='class_schedule_pattern_history')
    op.drop_table('class_schedule_pattern_history')
