"""add doc_name column to student_documents

Revision ID: add_doc_name
Revises: 6bb08d035565
Create Date: 2026-03-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_doc_name'
down_revision = '6bb08d035565'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('student_documents', sa.Column('doc_name', sa.String(length=64), nullable=True))


def downgrade():
    op.drop_column('student_documents', 'doc_name')
