import json
from typing import Any

import httpx
import pytest
from google.genai import errors

from compensation_hub.ask_compensation.plan import Query
from compensation_hub.ask_compensation.provider import (
    GeminiQueryPlanner,
    PlannerContext,
    PlannerTurn,
    PlannerUnavailableError,
    UnconfiguredQueryPlanner,
    build_query_planner,
    build_response_schema,
    build_system_instruction,
)
from compensation_hub.core.config import Settings

CONTEXT = PlannerContext(
    vocabulary={
        "country": ("Germany", "India"),
        "department": ("Engineering", "Sales"),
        "job_title": ("Software Engineer", "Account Executive"),
        "currency": ("EUR", "INR"),
    },
    currencies=("EUR", "INR", "USD"),
)
PAYROLL_QUERY = Query.model_validate(
    {
        "kind": "aggregate",
        "filters": [{"field": "country", "op": "eq", "value": "Germany"}],
        "measures": [{"name": "payroll", "function": "sum", "field": "salary"}],
    }
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
    raw_plan = '{"status": "query", "query": {"kind": "aggregate"}}'
    planner, models = planner_with(FakeResponse(raw_plan))

    raw = planner.plan("How many employees are there?", [], CONTEXT)

    assert raw == raw_plan
    call = models.calls[0]
    assert call["model"] == "gemini-test"
    assert [content.role for content in call["contents"]] == ["user"]
    assert call["contents"][0].parts[0].text == "How many employees are there?"
    config = call["config"]
    assert config.temperature == 0
    assert config.thinking_config.thinking_level == "LOW"
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == build_response_schema(CONTEXT)
    assert "Germany" in config.system_instruction
    assert "Account Executive" in config.system_instruction


def test_history_is_sent_as_prior_turns_with_queries_only() -> None:
    planner, models = planner_with(FakeResponse("{}"))
    history = [PlannerTurn("What is the total payroll in Germany?", PAYROLL_QUERY)]

    planner.plan("Convert that to INR.", history, CONTEXT)

    contents = models.calls[0]["contents"]
    assert [content.role for content in contents] == ["user", "model", "user"]
    assert contents[0].parts[0].text == "What is the total payroll in Germany?"
    reply = json.loads(contents[1].parts[0].text)
    assert reply == {"status": "query", "query": PAYROLL_QUERY.model_dump(mode="json")}
    assert contents[2].parts[0].text == "Convert that to INR."


def test_system_instruction_describes_the_catalog_and_the_rules() -> None:
    instruction = build_system_instruction(CONTEXT)

    for field in ("employee_code", "full_name", "country", "salary", "local_salary", "currency"):
        assert f'"{field}"' in instruction
    assert '"Germany", "India"' in instruction
    assert "EUR, INR, USD" in instruction
    assert "missing_data" in instruction
    assert "recommending salaries or raises" in instruction
    assert "never infer an attribute" in instruction


def test_response_schema_uses_only_the_supported_json_schema_subset() -> None:
    supported = {
        "type", "properties", "required", "items", "enum", "anyOf", "minimum", "maximum",
        "maxItems", "minItems", "description",
    }  # fmt: skip

    def keywords(node: object) -> set[str]:
        if isinstance(node, dict):
            found = set(node) - {"properties"}
            for key, value in node.items():
                if key == "properties":
                    for child in value.values():
                        found |= keywords(child)
                else:
                    found |= keywords(value)
            return found | ({"properties"} if "properties" in node else set())
        if isinstance(node, list):
            return set().union(*(keywords(item) for item in node)) if node else set()
        return set()

    schema = build_response_schema(CONTEXT)
    assert keywords(schema) <= supported
    assert "maxItems" not in keywords(schema)


def test_response_schema_offers_only_catalog_fields_and_configured_currencies() -> None:
    schema = build_response_schema(CONTEXT)
    query = schema["properties"]["query"]  # type: ignore[index]

    assert query["properties"]["currency"]["enum"] == ["EUR", "INR", "USD"]
    assert "salary" in query["properties"]["fields"]["items"]["enum"]
    assert "gender" not in query["properties"]["fields"]["items"]["enum"]
    # Every property is required so constrained decoding fills in the whole plan.
    assert query["required"] == list(query["properties"])


def test_api_error_becomes_unavailable() -> None:
    planner, _ = planner_with(errors.APIError(503, {"error": {"message": "overloaded"}}))

    with pytest.raises(PlannerUnavailableError, match="status 503"):
        planner.plan("How many employees are there?", [], CONTEXT)


def test_network_error_becomes_unavailable() -> None:
    planner, _ = planner_with(httpx.ConnectError("connection refused"))

    with pytest.raises(PlannerUnavailableError, match="could not be reached"):
        planner.plan("How many employees are there?", [], CONTEXT)


def test_empty_response_becomes_unavailable() -> None:
    planner, _ = planner_with(FakeResponse(None))

    with pytest.raises(PlannerUnavailableError, match="empty"):
        planner.plan("How many employees are there?", [], CONTEXT)


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
