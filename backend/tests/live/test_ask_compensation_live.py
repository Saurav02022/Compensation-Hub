"""Optional live-model evaluation for Ask Compensation.

Excluded from the default test run and from CI. It needs TEST_DATABASE_URL, GEMINI_API_KEY,
and the live marker selected explicitly:

    uv run pytest -m live

The evaluation checks whether representative natural-language questions map to safe plans
that the application can execute. Exact values still come from PostgreSQL.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from compensation_hub.ask_compensation.provider import build_query_planner
from compensation_hub.core.config import Settings

pytestmark = pytest.mark.live

CASES: list[tuple[str, dict[str, object]]] = [
    (
        "What is the average salary in Engineering?",
        {"kind": "aggregate", "metric": "average_salary", "department": "Engineering"},
    ),
    (
        "What is the total payroll for Germany?",
        {"kind": "aggregate", "metric": "total_payroll", "country": "Germany"},
    ),
    (
        "What is the median salary in Sales?",
        {"kind": "aggregate", "metric": "median_salary", "department": "Sales"},
    ),
    (
        "Who are the five highest-paid Engineering employees in India?",
        {
            "kind": "employees",
            "department": "Engineering",
            "country": "India",
            "sort": "desc",
            "sort_by": "salary_usd",
            "limit": 5,
        },
    ),
    (
        "What currencies are used in Germany?",
        {"kind": "values", "field": "currency_code", "country": "Germany"},
    ),
    (
        "What percentage of employees are in Engineering?",
        {"kind": "share", "metric": "employee_count", "department": "Engineering"},
    ),
]

UNSUPPORTED_QUESTIONS = [
    "How many male engineers are based in India?",
    "What was Michael Nguyen's salary last year?",
    "Who should get a raise this year?",
]


@pytest.fixture
def live_client(seeded_client: TestClient) -> TestClient:
    settings = Settings()
    if settings.gemini_api_key is None:
        pytest.skip("GEMINI_API_KEY is not set; live evaluation is skipped")
    app = seeded_client.app
    assert isinstance(app, FastAPI)
    app.state.query_planner = build_query_planner(settings)
    return seeded_client


@pytest.mark.parametrize(("question", "expected"), CASES, ids=[case[0] for case in CASES])
def test_supported_question_maps_to_expected_plan(
    live_client: TestClient,
    question: str,
    expected: dict[str, object],
) -> None:
    body = live_client.post(
        "/analytics/ask",
        json={"question": question, "history": []},
    ).json()

    assert body["status"] == "answered", body
    plan = body["plan"]
    assert plan["kind"] == expected["kind"]
    if "metric" in expected:
        assert plan["metric"] == expected["metric"]
    if "field" in expected:
        assert plan["field"] == expected["field"]
    if "country" in expected:
        assert plan["filters"]["countries"] == [expected["country"]]
    if "department" in expected:
        assert plan["filters"]["departments"] == [expected["department"]]
    if "sort" in expected:
        assert plan["sort"] == expected["sort"]
    if "sort_by" in expected:
        assert plan["sort_by"] == expected["sort_by"]
    if "limit" in expected:
        assert plan["limit"] == expected["limit"]


@pytest.mark.parametrize("question", UNSUPPORTED_QUESTIONS)
def test_questions_requiring_missing_or_subjective_data_are_declined(
    live_client: TestClient,
    question: str,
) -> None:
    body = live_client.post(
        "/analytics/ask",
        json={"question": question, "history": []},
    ).json()

    assert body["status"] == "unsupported", body


def test_follow_up_reuses_prior_validated_intent(live_client: TestClient) -> None:
    first_question = "What is the total payroll in Germany?"
    first = live_client.post(
        "/analytics/ask",
        json={"question": first_question, "history": []},
    ).json()
    assert first["status"] == "answered", first

    second = live_client.post(
        "/analytics/ask",
        json={
            "question": "Convert that to Indian currency.",
            "history": [{"question": first_question, "plan": first["plan"]}],
        },
    ).json()

    assert second["status"] == "answered", second
    assert second["plan"]["kind"] == "aggregate"
    assert second["plan"]["metric"] == "total_payroll"
    assert second["plan"]["filters"]["countries"] == ["Germany"]
    assert second["plan"]["target_currency"] == "INR"
    assert second["result"]["currency"] == "INR"
