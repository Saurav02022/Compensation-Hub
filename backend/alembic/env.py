from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from compensation_hub.core.config import get_settings
from compensation_hub.db.base import Base
from compensation_hub.db.models import Compensation, Employee, FxRate  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Prefer a URL set programmatically (for example by tests), else the application settings."""
    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url:
        return configured_url
    return str(get_settings().database_url)


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_database_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
