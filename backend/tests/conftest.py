from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from compensation_hub.db.base import Base
from compensation_hub.db.session import create_database_engine, create_session_factory

BACKEND_DIR = Path(__file__).resolve().parent.parent


class TestSettings(BaseSettings):
    """Test-only configuration; TEST_DATABASE_URL comes from the environment or `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    test_database_url: PostgresDsn | None = None


def alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    # configparser treats "%" as interpolation syntax, so URL-encoded characters must be escaped.
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = TestSettings().test_database_url
    if url is None:
        pytest.skip("TEST_DATABASE_URL is not set; PostgreSQL integration tests are skipped")
    return str(url)


@pytest.fixture(scope="session")
def migrated_engine(test_database_url: str) -> Iterator[Engine]:
    """Engine bound to a test database migrated to the latest schema from a clean state."""
    config = alembic_config(test_database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_database_engine(test_database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(migrated_engine: Engine) -> Iterator[Session]:
    """Session on an empty schema; all MVP tables are truncated after each test."""
    session_factory = create_session_factory(migrated_engine)
    with session_factory() as session:
        yield session
        session.rollback()
        table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)
        session.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY"))
        session.commit()
