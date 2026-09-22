"""Optional live-model evaluation for Ask Compensation.

Excluded from the default test run and from CI. It needs TEST_DATABASE_URL, GEMINI_API_KEY,
and the ``live`` marker selected explicitly:

    uv run pytest -m live

Each case checks that a representative question maps to the expected structured request; the
numbers themselves come from the deterministic analytics service and are not asserted here.
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
        {"metric": "average_salary", "department": "Engineering", "group_by": None},
    ),
    (
        "What is the total payroll for Germany?",
        {"metric": "total_payroll", "country": "Germany", "group_by": None},
    ),
    (
        "Show average compensation by department.",
        {"metric": "average_salary", "group_by": "department"},
    ),
    (
        "How many Engineering employees are based in India?",
        {
            "metric": "employee_count",
            "department": "Engineering",
            "country": "India",
            "group_by": None,
        },
    ),
    (
        "Which three countries have the highest total payroll?",
        {"metric": "total_payroll", "group_by": "country", "sort": "desc", "limit": 3},
    ),
]

UNSUPPORTED_QUESTIONS = [
    "Who should get a raise this year?",
    "What was Michael Nguyen's salary last year?",
    "What is the median salary in Sales?",
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
    live_client: TestClient, question: str, expected: dict[str, object]
) -> None:
    body = live_client.post("/analytics/ask", json={"question": question}).json()

    assert body["status"] == "answered", body
    plan = body["plan"]
    assert plan["metric"] == expected["metric"]
    assert plan["group_by"] == expected.get("group_by")
    for field in ("country", "department", "job_title"):
        assert plan["filters"][field] == expected.get(field), field
    if "sort" in expected:
        assert plan["sort"] == expected["sort"]
    if "limit" in expected:
        assert plan["limit"] == expected["limit"]


@pytest.mark.parametrize("question", UNSUPPORTED_QUESTIONS)
def test_unsupported_question_is_declined(live_client: TestClient, question: str) -> None:
    body = live_client.post("/analytics/ask", json={"question": question}).json()

    assert body["status"] == "unsupported", body
