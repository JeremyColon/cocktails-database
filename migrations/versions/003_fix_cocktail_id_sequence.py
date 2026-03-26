"""Add sequence to cocktail_id and fix NULL rows

Revision ID: 003
Revises: 002
Create Date: 2026-03-25
"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Delete NULL cocktail_id rows from dependent tables first
    op.execute("DELETE FROM cocktails_ingredients WHERE cocktail_id IS NULL")
    op.execute("DELETE FROM cocktails WHERE cocktail_id IS NULL")

    # Create a sequence starting just above the current max id
    op.execute("""
        CREATE SEQUENCE IF NOT EXISTS cocktails_cocktail_id_seq
        START WITH 1
    """)
    op.execute("""
        SELECT setval(
            'cocktails_cocktail_id_seq',
            COALESCE((SELECT MAX(cocktail_id) FROM cocktails), 0) + 1
        )
    """)

    # Set column default to use the sequence
    op.execute("""
        ALTER TABLE cocktails
        ALTER COLUMN cocktail_id SET DEFAULT nextval('cocktails_cocktail_id_seq')
    """)

    # Now enforce NOT NULL
    op.execute("ALTER TABLE cocktails ALTER COLUMN cocktail_id SET NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE cocktails ALTER COLUMN cocktail_id DROP DEFAULT")
    op.execute("ALTER TABLE cocktails ALTER COLUMN cocktail_id DROP NOT NULL")
    op.execute("DROP SEQUENCE IF EXISTS cocktails_cocktail_id_seq")
