"""Alembic environment configuration — async engine variant.

Reads ``DATABASE_URL`` from the environment (or ``alembic.ini`` fallback)
and runs migrations using SQLAlchemy's async runner.
"""

from __future__ import annotations

import asyncio
import os

# Import ORM metadata so Alembic can autogenerate migrations.
# Add imports for any additional ORM modules here.
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app.infrastructure.persistence.sqlalchemy.models import Base

# Alembic Config object — provides access to values within alembic.ini.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url with DATABASE_URL env var when present.
database_url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL without a live connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    """Execute migrations within an active connection."""
    context.configure(connection=connection, target_metadata=target_metadata)  # type: ignore[arg-type]
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations inside it."""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url") or "",
        echo=False,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
