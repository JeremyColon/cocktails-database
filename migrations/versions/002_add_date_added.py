"""Add date_added column to cocktails table

Revision ID: 002
Revises: 001
Create Date: 2026-03-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cocktails",
        sa.Column(
            "date_added",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Backfill scraped recipes with the time they were first scraped.
    # Legacy pre-scraper recipes keep the server_default (now()).
    op.execute("""
        UPDATE cocktails
        SET date_added = scraped_at
        WHERE scraped_at IS NOT NULL
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS cocktails_date_added_idx ON cocktails (date_added DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS cocktails_date_added_idx")
    op.drop_column("cocktails", "date_added")
