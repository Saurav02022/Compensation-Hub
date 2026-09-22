from typing import Any

import httpx
import pytest
from google.genai import errors

from compensation_hub.ask_compensation.provider import (
    GeminiQueryPlanner,
    PlannerContext,
    PlannerUnavailableError,
    UnconfiguredQueryPlanner,
    build_query_planner,
    build_system_instruction,
)
from compensation_hub.core.config import Settings

CONTEXT = PlannerContext(
    countries=("Germany", "India"),
    departments=("Engineering", "Sales"),
    job_titles=("Software Engineer", "Account Executive"),
)


class FakeResponse:
    def __init__(self, text: str | None) -> None:
        self.text = text


class FakeModels:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class FakeClient:
    def __init__(self, outcome: object) -> None:
        self.models = FakeModels(outcome)


def planner_with(outcome: object) -> tuple[GeminiQueryPlanner, FakeModels]:
    planner = GeminiQueryPlanner(api_key="test-key", model="gemini-test", timeout_seconds=5)
    client = FakeClient(outcome)
    planner._client = client  # type: ignore[assignment]
    return planner, client.models


def test_plan_sends_question_with_constrained_json_config() -> None:
    planner, models = planner_with(
        FakeResponse('{"status": "plan", "plan": {"metric": "employee_count"}}')
    )

    raw = planner.plan("How many employees are there?", CONTEXT)

    assert raw == '{"status": "plan", "plan": {"metric": "employee_count"}}'
    call = models.calls[0]
    assert call["model"] == "gemini-test"
    assert call["contents"] == "How many employees are there?"
    config = call["config"]
    assert config.temperature == 0
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema["properties"]["status"]["enum"] == ["plan", "unsupported"]
    assert "Germany" in config.system_instruction
    assert "Account Executive" in config.system_instruction


def test_system_instruction_lists_only_dimension_vocabulary() -> None:
    instruction = build_system_instruction(CONTEXT)

    assert '"Germany", "India"' in instruction
    assert '"Engineering", "Sales"' in instruction
    assert "unsupported" in instruction
    assert "who should get a raise" in instruction


def test_api_error_becomes_unavailable() -> None:
    planner, _ = planner_with(errors.APIError(503, {"error": {"message": "overloaded"}}))

    with pytest.raises(PlannerUnavailableError, match="status 503"):
        planner.plan("How many employees are there?", CONTEXT)


def test_network_error_becomes_unavailable() -> None:
    planner, _ = planner_with(httpx.ConnectError("connection refused"))

    with pytest.raises(PlannerUnavailableError, match="could not be reached"):
        planner.plan("How many employees are there?", CONTEXT)


def test_empty_response_becomes_unavailable() -> None:
    planner, _ = planner_with(FakeResponse(None))

    with pytest.raises(PlannerUnavailableError, match="empty"):
        planner.plan("How many employees are there?", CONTEXT)


def test_build_query_planner_uses_gemini_when_key_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-custom")

    planner = build_query_planner(Settings(_env_file=None))

    assert isinstance(planner, GeminiQueryPlanner)
    assert planner._model == "gemini-custom"


def test_build_query_planner_is_unconfigured_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    assert isinstance(build_query_planner(Settings(_env_file=None)), UnconfiguredQueryPlanner)


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_key_leaves_the_feature_unconfigured(
    monkeypatch: pytest.MonkeyPatch, blank: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.setenv("GEMINI_API_KEY", blank)

    settings = Settings(_env_file=None)

    assert settings.gemini_api_key is None
    assert isinstance(build_query_planner(settings), UnconfiguredQueryPlanner)


def test_settings_never_expose_the_key_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.setenv("GEMINI_API_KEY", "super-secret")

    assert "super-secret" not in repr(Settings(_env_file=None))
