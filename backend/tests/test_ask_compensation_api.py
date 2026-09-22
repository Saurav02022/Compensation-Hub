import json
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from compensation_hub.ask_compensation.provider import (
    PlannerContext,
    PlannerUnavailableError,
    UnconfiguredQueryPlanner,
    build_query_planner,
)
from compensation_hub.core.config import Settings
from compensation_hub.db.models import Compensation
from compensation_hub.seed.dataset import build_seed_dataset

DATASET = build_seed_dataset(employee_count=60)
SAMPLE = DATASET.employees[0]


class FakePlanner:
    """Returns canned provider text per question and records what it was shown."""

    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.contexts: list[PlannerContext] = []
        self.questions: list[str] = []

    def plan(self, question: str, context: PlannerContext) -> str:
        self.questions.append(question)
        self.contexts.append(context)
        return self.responses[question]


class BrokenPlanner:
    def plan(self, question: str, context: PlannerContext) -> str:
        raise PlannerUnavailableError("connection refused")


def planned(plan: dict[str, object]) -> str:
    return json.dumps({"status": "plan", "plan": plan})


def install(client: TestClient, planner: object) -> None:
    app = client.app
    assert isinstance(app, FastAPI)
    app.state.query_planner = planner


def ask(client: TestClient, question: str) -> dict[str, object]:
    response = client.post("/analytics/ask", json={"question": question})
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


def test_summary_question_is_answered_from_analytics(seeded_client: TestClient) -> None:
    question = f"What is the average salary in {SAMPLE.department}?"
    planner = FakePlanner(
        {
            question: planned(
                {"metric": "average_salary", "filters": {"department": SAMPLE.department}}
            )
        }
    )
    install(seeded_client, planner)
    expected = seeded_client.get(
        "/analytics/summary", params={"department": SAMPLE.department}
    ).json()

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    assert body["question"] == question
    assert body["plan"] == {
        "metric": "average_salary",
        "filters": {"country": None, "department": SAMPLE.department, "job_title": None},
        "group_by": None,
        "sort": None,
        "limit": None,
    }
    assert body["result"] == {
        "currency": "USD",
        "rows": [
            {
                "key": None,
                "employee_count": expected["employee_count"],
                "total_payroll_usd": expected["total_payroll_usd"],
                "average_salary_usd": expected["average_salary_usd"],
            }
        ],
    }
    average = Decimal(expected["average_salary_usd"])
    assert body["answer"] == (
        f"Average annual salary for department {SAMPLE.department}: USD {average:,.2f} "
        f"({expected['employee_count']:,} employees). "
        "Monetary values are normalized to USD using seeded exchange rates."
    )


def test_count_question_omits_currency_note(seeded_client: TestClient) -> None:
    question = f"How many {SAMPLE.department} employees are based in {SAMPLE.country}?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    {
                        "metric": "employee_count",
                        "filters": {"country": SAMPLE.country, "department": SAMPLE.department},
                    }
                )
            }
        ),
    )
    expected = seeded_client.get(
        "/analytics/summary", params={"country": SAMPLE.country, "department": SAMPLE.department}
    ).json()

    body = ask(seeded_client, question)

    assert body["answer"] == (
        f"Employee count for country {SAMPLE.country}, department {SAMPLE.department}: "
        f"{expected['employee_count']:,}."
    )


def test_grouped_question_uses_breakdown_with_sort_and_limit(seeded_client: TestClient) -> None:
    question = "Which three departments have the highest total payroll?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    {
                        "metric": "total_payroll",
                        "group_by": "department",
                        "sort": "desc",
                        "limit": 3,
                    }
                )
            }
        ),
    )
    expected = seeded_client.get(
        "/analytics/breakdown",
        params={
            "group_by": "department",
            "sort_by": "total_payroll_usd",
            "descending": "true",
            "limit": 3,
        },
    ).json()["rows"]

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    assert body["result"]["rows"] == expected  # type: ignore[index]
    listing = "; ".join(
        f"{row['key']}: USD {Decimal(row['total_payroll_usd']):,.2f}" for row in expected
    )
    assert body["answer"] == (
        f"Total annual payroll by department across the organization, highest first, top 3: "
        f"{listing}. Monetary values are normalized to USD using seeded exchange rates."
    )


def test_planner_sees_dimension_values_but_never_employee_data(
    seeded_client: TestClient,
) -> None:
    question = "Show average compensation by department."
    planner = FakePlanner(
        {question: planned({"metric": "average_salary", "group_by": "department"})}
    )
    install(seeded_client, planner)

    ask(seeded_client, question)

    assert planner.questions == [question]
    context = planner.contexts[0]
    assert set(context.departments) == {e.department for e in DATASET.employees}
    assert set(context.countries) == {e.country for e in DATASET.employees}
    assert set(context.job_titles) == {e.job_title for e in DATASET.employees}
    shown = json.dumps(
        {
            "countries": list(context.countries),
            "departments": list(context.departments),
            "job_titles": list(context.job_titles),
        }
    )
    assert SAMPLE.full_name not in shown
    assert str(SAMPLE.annual_salary) not in shown
    assert "EMP00001" not in shown


def test_unsupported_question_returns_clear_response(seeded_client: TestClient) -> None:
    question = "Who should get a raise this year?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: json.dumps(
                    {"status": "unsupported", "reason": "Salary recommendations are not supported"}
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "unsupported"
    assert body["plan"] is None
    assert body["result"] is None
    assert "cannot be answered reliably" in str(body["answer"])
    assert "Salary recommendations are not supported" in str(body["answer"])


@pytest.mark.parametrize(
    "raw",
    [
        "not json at all",
        json.dumps({"status": "plan"}),
        json.dumps({"status": "plan", "plan": {"metric": "median_salary"}}),
        json.dumps({"status": "plan", "plan": {"metric": "total_payroll", "group_by": "salary"}}),
        json.dumps({"status": "plan", "plan": {"metric": "total_payroll", "limit": 0}}),
        json.dumps({"status": "plan", "plan": {"metric": "total_payroll", "limit": 101}}),
        json.dumps({"status": "plan", "plan": {"metric": "total_payroll", "sql": "SELECT 1"}}),
        json.dumps(
            {
                "status": "plan",
                "plan": {"metric": "total_payroll", "filters": {"employee_code": "EMP00001"}},
            }
        ),
        json.dumps({"status": "execute", "sql": "DELETE FROM compensation"}),
    ],
)
def test_invalid_planner_output_is_rejected_as_unsupported(
    seeded_client: TestClient, raw: str
) -> None:
    question = "Anything"
    install(seeded_client, FakePlanner({question: raw}))

    body = ask(seeded_client, question)

    assert body["status"] == "unsupported"
    assert body["plan"] is None
    assert body["result"] is None


def test_write_like_plan_cannot_change_compensation(
    seeded_client: TestClient, db_session: Session
) -> None:
    before = db_session.scalar(select(func.sum(Compensation.annual_salary)))
    question = "Give everyone in Sales a 10% raise"
    install(
        seeded_client,
        FakePlanner(
            {
                question: json.dumps(
                    {
                        "status": "plan",
                        "plan": {
                            "metric": "total_payroll",
                            "filters": {"department": "Sales"},
                            "update": {"annual_salary": "*1.1"},
                        },
                    }
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "unsupported"
    db_session.expire_all()
    assert db_session.scalar(select(func.sum(Compensation.annual_salary))) == before


def test_unknown_filter_value_is_reported_instead_of_guessed(seeded_client: TestClient) -> None:
    question = "What is the total payroll for Atlantis?"
    install(
        seeded_client,
        FakePlanner(
            {question: planned({"metric": "total_payroll", "filters": {"country": "Atlantis"}})}
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "unsupported"
    assert "There is no country named 'Atlantis'" in str(body["answer"])


def test_code_fenced_json_is_accepted(seeded_client: TestClient) -> None:
    question = "How many employees are there?"
    install(
        seeded_client,
        FakePlanner({question: "```json\n" + planned({"metric": "employee_count"}) + "\n```"}),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    assert body["answer"] == "Employee count across the organization: 60."


def test_provider_outage_reports_unavailable_without_breaking_other_features(
    seeded_client: TestClient,
) -> None:
    install(seeded_client, BrokenPlanner())

    response = seeded_client.post("/analytics/ask", json={"question": "How many employees?"})

    assert response.status_code == 503
    assert "Ask Compensation is currently unavailable" in response.json()["detail"]
    assert seeded_client.get("/analytics/summary").status_code == 200
    assert seeded_client.get("/employees").status_code == 200


def test_question_is_validated(seeded_client: TestClient) -> None:
    install(seeded_client, FakePlanner({}))

    assert seeded_client.post("/analytics/ask", json={"question": "hi"}).status_code == 422
    assert seeded_client.post("/analytics/ask", json={"question": "x" * 501}).status_code == 422
    assert seeded_client.post("/analytics/ask", json={}).status_code == 422
    assert (
        seeded_client.post(
            "/analytics/ask", json={"question": "How many?", "sql": "SELECT 1"}
        ).status_code
        == 422
    )


def test_default_planner_is_unavailable_until_a_provider_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    planner = build_query_planner(Settings(_env_file=None))

    assert isinstance(planner, UnconfiguredQueryPlanner)
    with pytest.raises(PlannerUnavailableError):
        planner.plan("How many employees?", PlannerContext((), (), ()))
