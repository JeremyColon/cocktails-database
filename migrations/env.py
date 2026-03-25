import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Build the sync DB URL from env vars — no application imports needed.
# Bypasses alembic.ini interpolation entirely.
def _build_db_url() -> str:
    # Prefer explicit COCKTAILS_* vars (RDS) over DATABASE_URL, which may
    # be set to a legacy SQLite path from the old Dash app.
    host = os.environ.get("COCKTAILS_HOST", "")
    if host:
        port = os.environ.get("COCKTAILS_PORT", "5432")
        user = os.environ.get("COCKTAILS_USER", "postgres")
        pwd = os.environ.get("COCKTAILS_PWD", "")
        db = os.environ.get("COCKTAILS_DB", "postgres")
        return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"

    url = os.environ.get("DATABASE_URL", "")
    if url:
        return url.replace("postgresql+asyncpg://", "postgresql://").replace(
            "postgres://", "postgresql://"
        )

    raise RuntimeError(
        "No database URL configured. Set COCKTAILS_HOST (and COCKTAILS_PWD, "
        "COCKTAILS_USER, COCKTAILS_DB, COCKTAILS_PORT) or DATABASE_URL."
    )

# target_metadata is None — migrations use plain SQL, not ORM autogenerate.
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(
        url=_build_db_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_build_db_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
