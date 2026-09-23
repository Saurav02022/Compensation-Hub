"""Optional live-model evaluation for Ask Compensation.

Excluded from the default test run and CI. It verifies that representative questions are
translated into the generic read-only query program and that missing-data questions are declined.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from compensation_hub.ask_compensation.provider import build_query_planner
from compensation_hub.core.config import Settings

pytestmark = pytest.mark.live

SUPPORTED_QUESTIONS = [
    "What is the average salary in Engineering?",
    "What is the median salary in Sales?",
    "Who are the five highest-paid Engineering employees in India?",
    "What percentage of employees are in Engineering?",
    "Which three countries have the highest payroll?",
    "What currencies are used in Germany?",
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


@pytest.mark.parametrize("question", SUPPORTED_QUESTIONS)
def test_answerable_questions_produce_valid_read_only_programs(
    live_client: TestClient,
    question: str,
) -> None:
    body = live_client.post(
        "/analytics/ask",
        json={"question": question, "history": []},
    ).json()

    assert body["status"] == "answered", body
    assert body["plan"]["queries"], body
    assert body["result"] is not None, body


@pytest.mark.parametrize("question", UNSUPPORTED_QUESTIONS)
def test_questions_requiring_unavailable_or_subjective_data_are_declined(
    live_client: TestClient,
    question: str,
) -> None:
    body = live_client.post(
        "/analytics/ask",
        json={"question": question, "history": []},
    ).json()

    assert body["status"] == "unsupported", body
    assert "data available in Compensation Hub" in body["answer"]


def test_follow_up_reuses_previous_validated_program(live_client: TestClient) -> None:
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
    assert second["result"]["currency"] == "INR", second
    assert second["plan"]["queries"][-1]["target_currency"] == "INR", second
