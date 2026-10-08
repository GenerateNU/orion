"""Alembic environment: the one place OrionDB's schema is migrated from."""

from logging.config import fileConfig

from alembic import context

from orion_core.db.engines import make_sync_engine
from orion_core.db.orion import Base
from orion_core.settings import get_settings

fileConfig(context.config.config_file_name)

# Only Orion's metadata. Penelope tables live on a separate MetaData.
target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = make_sync_engine(get_settings().orion_database_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
