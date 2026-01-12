"""add request_candidates created_at index

Revision ID: q1w2e3r4t5y6
Revises: m4n5o6p7q8r9
Create Date: 2026-01-12 03:00:00.000000
"""

from alembic import op
from sqlalchemy import inspect


revision = "q1w2e3r4t5y6"
down_revision = "m4n5o6p7q8r9"
branch_labels = None
depends_on = None


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(idx.get("name") == index_name for idx in indexes)


def upgrade() -> None:
    index_name = "idx_request_candidates_created_at"
    if not _index_exists("request_candidates", index_name):
        op.create_index(index_name, "request_candidates", ["created_at"])


def downgrade() -> None:
    index_name = "idx_request_candidates_created_at"
    if _index_exists("request_candidates", index_name):
        op.drop_index(index_name, table_name="request_candidates")

