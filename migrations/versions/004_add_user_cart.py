"""Add user_cart table for tonight's cart feature

Revision ID: 004
Revises: 003
Create Date: 2026-04-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE user_cart (
            user_id         BIGINT  NOT NULL REFERENCES users(id),
            cocktail_id     INT     NOT NULL,
            in_cart         BOOLEAN NOT NULL DEFAULT FALSE,
            last_updated_ts TIMESTAMP,
            PRIMARY KEY (user_id, cocktail_id)
        )
    """)
    op.execute("CREATE INDEX ix_user_cart_user_id ON user_cart (user_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_cart_user_id")
    op.execute("DROP TABLE IF EXISTS user_cart")
