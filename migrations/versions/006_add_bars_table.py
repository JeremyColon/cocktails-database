"""Introduce bars table; migrate ingredient_list out of user_bar; add bar_link_invites

Revision ID: 006
Revises: 005
Create Date: 2026-04-07

Changes:
- Create bars (bar_id, ingredient_list, last_updated_ts, deleted_at)
- Add bar_id FK column to user_bar; migrate each row's ingredient_list into a new bars row
- Drop ingredient_list from user_bar
- Create bar_link_invites for household linking
"""
from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create bars table
    op.execute("""
        CREATE TABLE bars (
            bar_id          BIGSERIAL   PRIMARY KEY,
            ingredient_list BIGINT[]    NOT NULL DEFAULT '{}',
            last_updated_ts TIMESTAMP,
            deleted_at      TIMESTAMP
        )
    """)

    # 2. Add bar_id column to user_bar (nullable for now)
    op.execute("ALTER TABLE user_bar ADD COLUMN bar_id BIGINT")

    # 3. Migrate each existing user_bar row into its own bars row
    op.execute("""
        DO $$
        DECLARE
            r RECORD;
            new_bar_id BIGINT;
        BEGIN
            FOR r IN SELECT user_id, ingredient_list, last_updated_ts FROM user_bar LOOP
                INSERT INTO bars (ingredient_list, last_updated_ts)
                VALUES (COALESCE(r.ingredient_list, '{}'), r.last_updated_ts)
                RETURNING bar_id INTO new_bar_id;

                UPDATE user_bar SET bar_id = new_bar_id WHERE user_id = r.user_id;
            END LOOP;
        END $$
    """)

    # 4. Add FK constraint and NOT NULL
    op.execute("ALTER TABLE user_bar ADD CONSTRAINT fk_user_bar_bar_id FOREIGN KEY (bar_id) REFERENCES bars(bar_id)")
    op.execute("ALTER TABLE user_bar ALTER COLUMN bar_id SET NOT NULL")

    # 5. Drop ingredient_list from user_bar (now lives in bars)
    op.execute("ALTER TABLE user_bar DROP COLUMN ingredient_list")

    # 6. Create bar_link_invites for household linking
    op.execute("""
        CREATE TABLE bar_link_invites (
            token       TEXT      PRIMARY KEY,
            inviter_id  BIGINT    NOT NULL REFERENCES users(id),
            expires_at  TIMESTAMP NOT NULL,
            accepted_at TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX ix_bar_link_invites_inviter_id ON bar_link_invites (inviter_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_bar_link_invites_inviter_id")
    op.execute("DROP TABLE IF EXISTS bar_link_invites")

    # Restore ingredient_list on user_bar from bars
    op.execute("ALTER TABLE user_bar ADD COLUMN ingredient_list BIGINT[] DEFAULT '{}'")
    op.execute("""
        UPDATE user_bar ub
        SET ingredient_list = b.ingredient_list
        FROM bars b
        WHERE b.bar_id = ub.bar_id
    """)

    op.execute("ALTER TABLE user_bar DROP CONSTRAINT IF EXISTS fk_user_bar_bar_id")
    op.execute("ALTER TABLE user_bar DROP COLUMN bar_id")
    op.execute("DROP TABLE IF EXISTS bars")
