"""Add bar_share_tokens table for one-time bar share feature

Revision ID: 005
Revises: 004
Create Date: 2026-04-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE bar_share_tokens (
            token      TEXT      PRIMARY KEY,
            user_id    BIGINT    NOT NULL REFERENCES users(id),
            expires_at TIMESTAMP NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_bar_share_tokens_user_id ON bar_share_tokens (user_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_bar_share_tokens_user_id")
    op.execute("DROP TABLE IF EXISTS bar_share_tokens")
