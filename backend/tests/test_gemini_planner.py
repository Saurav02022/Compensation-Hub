from typing import Any

import httpx
import pytest
from google.genai import errors

from compensation_hub.ask_compensation.provider import (
    GeminiQueryPlanner,
    PlannerContext,
    PlannerTurn,
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
    currency_codes=("EUR", "INR", "USD"),
    country_currencies=(("Germany", "EUR"), ("India", "INR")),
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


def test_plan_sends_question_with_constrained_generic_schema() -> None:
    response = (
        '{"status":"plan","plan":{"queries":[{"name":"answer","select":'
        '[{"alias":"employee_count","aggregate":"count"}]}]}}'
    )
    planner, models = planner_with(FakeResponse(response))

    raw = planner.plan("How many employees are there?", CONTEXT)

    assert raw == response
    call = models.calls[0]
    assert call["model"] == "gemini-test"
    assert call["contents"] == "How many employees are there?"
    config = call["config"]
    assert config.temperature == 0
    assert config.response_mime_type == "application/json"
    schema = config.response_json_schema
    assert schema["properties"]["status"]["enum"] == ["plan", "unsupported"]
    query_schema = schema["properties"]["plan"]["properties"]["queries"]["items"]
    fields = query_schema["properties"]["select"]["items"]["properties"]["field"]["enum"]
    assert "full_name" in fields
    assert "salary_usd" in fields
    assert "gender" not in fields
    assert "Germany" in config.system_instruction
    assert "Account Executive" in config.system_instruction
    assert "INR" in config.system_instruction


def test_plan_includes_validated_program_history_but_not_result_rows() -> None:
    response = (
        '{"status":"plan","plan":{"queries":[{"name":"answer","select":'
        '[{"alias":"total_payroll","field":"salary_usd","aggregate":"sum"}],'
        '"filters":[{"field":"country","op":"eq","values":["Germany"]}],'
        '"target_currency":"INR"}]}}'
    )
    planner, models = planner_with(FakeResponse(response))
    history = (
        PlannerTurn(
            question="What is the total payroll in Germany?",
            plan_json=(
                '{"queries":[{"name":"answer","select":[{"alias":"total_payroll",'
                '"field":"salary_usd","aggregate":"sum"}],"filters":'
                '[{"field":"country","op":"eq","values":["Germany"]}]}]}'
            ),
        ),
    )

    planner.plan("Convert that to Indian currency.", CONTEXT, history)

    contents = models.calls[0]["contents"]
    assert "Previous validated turns" in contents
    assert "What is the total payroll in Germany?" in contents
    assert '"field":"country"' in contents
    assert "Convert that to Indian currency." in contents
    assert "104,055,840" not in contents


def test_system_instruction_defines_product_rule_and_missing_data_boundary() -> None:
    instruction = build_system_instruction(CONTEXT)

    assert "If Compensation Hub has the data required" in instruction
    assert "produce a read-only query program" in instruction
    assert "must not be rejected merely because" in instruction
    assert "salary_usd" in instruction
    assert "percentile" in instruction
    assert "gender" in instruction.lower()
    assert "Never invent" in instruction
    assert "Never output SQL" in instruction
    assert "Follow-up questions are conversational" in instruction


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
