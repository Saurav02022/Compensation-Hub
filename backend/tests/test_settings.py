import pytest
from pydantic import ValidationError

from compensation_hub.core.config import Settings


def test_settings_read_database_url_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:secret@db.example:5432/hub")

    settings = Settings(_env_file=None)

    assert str(settings.database_url) == "postgresql+psycopg://user:secret@db.example:5432/hub"


def test_settings_require_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_reject_non_postgres_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///local.db")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
