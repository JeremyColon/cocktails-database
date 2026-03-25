"""Add source, scraped_at, and alcohol_type columns to cocktails table

Revision ID: 001
Revises:
Create Date: 2026-03-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # alcohol_type doesn't exist on cocktails in the current schema — add it
    # so the scraper and API can filter by liquor type at the cocktail level.
    op.add_column(
        "cocktails",
        sa.Column("alcohol_type", sa.Text(), nullable=True),
    )

    op.add_column(
        "cocktails",
        sa.Column("source", sa.Text(), nullable=False, server_default="liquor.com"),
    )
    op.add_column(
        "cocktails",
        sa.Column("scraped_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # Unique index for deduplication — lower() so case differences don't create dupes.
    # Use plain SQL for all indexes to avoid Alembic version compatibility issues.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS cocktails_name_source_idx "
        "ON cocktails (lower(recipe_name), source)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS cocktails_alcohol_type_idx "
        "ON cocktails (alcohol_type)"
    )

    # Deduplicate cocktails_ingredients — keep the row with the lowest PK for each
    # (cocktail_id, ingredient_id) pair before adding the unique index.
    op.execute("""
        DELETE FROM cocktails_ingredients
        WHERE cocktail_ingredient_id NOT IN (
            SELECT MIN(cocktail_ingredient_id)
            FROM cocktails_ingredients
            GROUP BY cocktail_id, ingredient_id
        )
    """)

    # Unique constraint on cocktails_ingredients (cocktail_id, ingredient_id)
    # so ON CONFLICT (cocktail_id, ingredient_id) DO NOTHING works on re-scrapes
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS cocktails_ingredients_unique_idx "
        "ON cocktails_ingredients (cocktail_id, ingredient_id)"
    )

    # GIN index on ingredients for fast full-text search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ingredients_ingredient_gin_idx "
        "ON ingredients USING gin(to_tsvector('english', ingredient))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ingredients_ingredient_gin_idx")
    op.execute("DROP INDEX IF EXISTS cocktails_ingredients_unique_idx")
    op.execute("DROP INDEX IF EXISTS cocktails_alcohol_type_idx")
    op.execute("DROP INDEX IF EXISTS cocktails_name_source_idx")
    op.drop_column("cocktails", "scraped_at")
    op.drop_column("cocktails", "source")
    op.drop_column("cocktails", "alcohol_type")
