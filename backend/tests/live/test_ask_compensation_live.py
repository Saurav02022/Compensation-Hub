"""Optional live-model evaluation for Ask Compensation.

Excluded from the default test run and CI. It verifies that Gemini can translate varied,
answerable questions into the generic read-only query AST and that questions requiring data
outside the schema are declined without guessing.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from compensation_hub.ask_compensation.provider import build_query_planner
from compensation_hub.core.config import Settings

pytestmark = pytest.mark.live

ANSWERABLE_QUESTIONS = [
    "How many employees are in Engineering?",
    "Which departments have the highest average salary?",
    "What is the median salary in Sales?",
    "Who are the five highest-paid Engineering employees in India?",
    "What percentage of employees are in Engineering?",
    "Which currencies are used in Germany?",
    "How much larger is Germany's payroll than India's?",
    "Show employees whose names contain Patel.",
]

MISSING_DATA_QUESTIONS = [
    "How many male engineers are based in India?",
    "What was the total payroll last year?",
    "Which employees have the highest performance rating?",
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


@pytest.mark.parametrize("question", ANSWERABLE_QUESTIONS)
def test_answerable_question_produces_data_grounded_result(
    live_client: TestClient,
    question: str,
) -> None:
    body = live_client.post(
        "/analytics/ask",
        json={"question": question, "history": []},
    ).json()

    assert body["status"] == "answered", body
    assert body["plan"]["select"], body
    assert body["result"] is not None, body


@pytest.mark.parametrize("question", MISSING_DATA_QUESTIONS)
def test_missing_data_question_is_declined(
    live_client: TestClient,
    question: str,
) -> None:
    body = live_client.post(
        "/analytics/ask",
        json={"question": question, "history": []},
    ).json()

    assert body["status"] == "unsupported", body
    assert "Missing data" in body["answer"], body


def test_follow_up_reuses_previous_validated_query(live_client: TestClient) -> None:
    first_question = "What is the total payroll in Germany?"
    first = live_client.post(
        "/analytics/ask",
        json={"question": first_question, "history": []},
    ).json()
    assert first["status"] == "answered", first

    second = live_client.post(
        "/analytics/ask",
        json={
            "question": "Convert that to INR.",
            "history": [{"question": first_question, "plan": first["plan"]}],
        },
    ).json()

    assert second["status"] == "answered", second
    assert second["result"]["currency_by_column"], second
    assert "INR" in second["result"]["currency_by_column"].values(), second
