import json
from collections.abc import Sequence
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from compensation_hub.ask_compensation.provider import (
    PlannerContext,
    PlannerTurn,
    PlannerUnavailableError,
    UnconfiguredQueryPlanner,
    build_query_planner,
)
from compensation_hub.core.config import Settings
from compensation_hub.db.models import FxRate
from compensation_hub.seed.dataset import build_seed_dataset

DATASET = build_seed_dataset(employee_count=60)
SAMPLE = DATASET.employees[0]


class FakePlanner:
    """Returns canned provider text and records the context it receives."""

    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.contexts: list[PlannerContext] = []
        self.questions: list[str] = []
        self.histories: list[tuple[PlannerTurn, ...]] = []

    def plan(
        self,
        question: str,
        context: PlannerContext,
        history: Sequence[PlannerTurn] = (),
    ) -> str:
        self.questions.append(question)
        self.contexts.append(context)
        self.histories.append(tuple(history))
        return self.responses[question]


class BrokenPlanner:
    def plan(
        self,
        question: str,
        context: PlannerContext,
        history: Sequence[PlannerTurn] = (),
    ) -> str:
        raise PlannerUnavailableError("connection refused")


def planned(plan: dict[str, object]) -> str:
    return json.dumps({"status": "plan", "plan": plan})


def install(client: TestClient, planner: object) -> None:
    app = client.app
    assert isinstance(app, FastAPI)
    app.state.query_planner = planner


def ask(
    client: TestClient,
    question: str,
    *,
    history: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    response = client.post(
        "/analytics/ask",
        json={"question": question, "history": history or []},
    )
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


def test_aggregate_question_is_answered_from_database(seeded_client: TestClient) -> None:
    question = f"How many {SAMPLE.department} employees are based in {SAMPLE.country}?"
    planner = FakePlanner(
        {
            question: planned(
                {
                    "kind": "aggregate",
                    "metric": "employee_count",
                    "filters": {
                        "countries": [SAMPLE.country],
                        "departments": [SAMPLE.department],
                    },
                }
            )
        }
    )
    install(seeded_client, planner)
    expected = seeded_client.get(
        "/analytics/summary",
        params={"country": SAMPLE.country, "department": SAMPLE.department},
    ).json()

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    assert body["result"] == {
        "kind": "scalar",
        "currency": None,
        "columns": [{"key": "value", "label": "Employee count", "format": "count"}],
        "rows": [{"value": expected["employee_count"]}],
    }
    assert body["analytics_path"] == (
        f"/analytics?country={SAMPLE.country}&department={SAMPLE.department}&metric=headcount"
    )


def test_grouped_median_salary_is_supported(seeded_client: TestClient) -> None:
    question = "Show median salary by department."
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    {
                        "kind": "aggregate",
                        "metric": "median_salary",
                        "group_by": "department",
                    }
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    assert body["plan"]["metric"] == "median_salary"  # type: ignore[index]
    result = body["result"]
    assert isinstance(result, dict)
    assert result["kind"] == "table"
    assert result["currency"] == "USD"
    assert result["rows"]


def test_follow_up_can_convert_previous_payroll_to_inr(
    seeded_client: TestClient,
    db_session: Session,
) -> None:
    first = "What is the total payroll in Germany?"
    follow_up = "Convert that to Indian currency."
    planner = FakePlanner(
        {
            first: planned(
                {
                    "kind": "aggregate",
                    "metric": "total_payroll",
                    "filters": {"countries": ["Germany"]},
                }
            ),
            follow_up: planned(
                {
                    "kind": "aggregate",
                    "metric": "total_payroll",
                    "filters": {"countries": ["Germany"]},
                    "target_currency": "INR",
                }
            ),
        }
    )
    install(seeded_client, planner)

    first_body = ask(seeded_client, first)
    assert first_body["status"] == "answered"
    first_plan = first_body["plan"]
    assert isinstance(first_plan, dict)

    second_body = ask(
        seeded_client,
        follow_up,
        history=[{"question": first, "plan": first_plan}],
    )

    assert second_body["status"] == "answered"
    assert second_body["plan"]["target_currency"] == "INR"  # type: ignore[index]
    assert second_body["result"]["currency"] == "INR"  # type: ignore[index]
    assert "converted to INR" in str(second_body["interpretation"])

    history = planner.histories[1]
    assert len(history) == 1
    assert history[0].question == first
    assert '"total_payroll"' in history[0].plan_json

    rate = db_session.scalar(select(FxRate.rate_to_usd).where(FxRate.currency_code == "INR"))
    assert rate is not None
    usd_value = Decimal(str(first_body["result"]["rows"][0]["value"]))  # type: ignore[index]
    expected = (usd_value / Decimal(rate)).quantize(Decimal("0.01"))
    assert Decimal(str(second_body["result"]["rows"][0]["value"])) == expected  # type: ignore[index]


def test_employee_ranking_returns_bounded_employee_rows(seeded_client: TestClient) -> None:
    question = f"Who are the three highest-paid employees in {SAMPLE.country}?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    {
                        "kind": "employees",
                        "filters": {"countries": [SAMPLE.country]},
                        "sort_by": "salary_usd",
                        "sort": "desc",
                        "limit": 3,
                    }
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    result = body["result"]
    assert isinstance(result, dict)
    assert result["kind"] == "employees"
    rows = result["rows"]
    assert isinstance(rows, list)
    assert len(rows) <= 3
    assert all("employee_code" in row and "local_compensation" in row for row in rows)


def test_distinct_values_question_uses_stored_data(seeded_client: TestClient) -> None:
    question = f"What currencies are used in {SAMPLE.country}?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    {
                        "kind": "values",
                        "field": "currency_code",
                        "filters": {"countries": [SAMPLE.country]},
                    }
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    assert body["result"]["kind"] == "table"  # type: ignore[index]
    assert body["result"]["rows"]  # type: ignore[index]


def test_share_question_is_calculated_deterministically(seeded_client: TestClient) -> None:
    question = f"What percentage of employees are in {SAMPLE.department}?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    {
                        "kind": "share",
                        "metric": "employee_count",
                        "filters": {"departments": [SAMPLE.department]},
                        "denominator_filters": {},
                    }
                )
            }
        ),
    )
    expected_count = seeded_client.get(
        "/analytics/summary",
        params={"department": SAMPLE.department},
    ).json()["employee_count"]

    body = ask(seeded_client, question)

    expected = (Decimal(expected_count) / Decimal(60) * 100).quantize(Decimal("0.01"))
    assert body["status"] == "answered"
    assert Decimal(body["result"]["rows"][0]["value"]) == expected  # type: ignore[index]


def test_comparison_question_is_calculated_from_two_scopes(seeded_client: TestClient) -> None:
    first_country = DATASET.employees[0].country
    second_country = next(
        employee.country for employee in DATASET.employees if employee.country != first_country
    )
    question = f"Compare headcount in {first_country} and {second_country}."
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    {
                        "kind": "compare",
                        "metric": "employee_count",
                        "filters": {"countries": [first_country]},
                        "compare_filters": {"countries": [second_country]},
                        "comparison": "difference",
                    }
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    assert body["result"]["kind"] == "scalar"  # type: ignore[index]
    assert body["plan"]["comparison"] == "difference"  # type: ignore[index]


def test_planner_sees_schema_vocabulary_but_never_employee_rows(
    seeded_client: TestClient,
) -> None:
    question = "What is our payroll?"
    planner = FakePlanner({question: planned({"kind": "aggregate", "metric": "total_payroll"})})
    install(seeded_client, planner)

    ask(seeded_client, question)

    context = planner.contexts[0]
    assert set(context.departments) == {employee.department for employee in DATASET.employees}
    assert set(context.countries) == {employee.country for employee in DATASET.employees}
    assert set(context.job_titles) == {employee.job_title for employee in DATASET.employees}
    assert context.currency_codes
    assert context.country_currencies

    shown = json.dumps(
        {
            "countries": list(context.countries),
            "departments": list(context.departments),
            "job_titles": list(context.job_titles),
            "currency_codes": list(context.currency_codes),
            "country_currencies": list(context.country_currencies),
        }
    )
    assert SAMPLE.full_name not in shown
    assert str(SAMPLE.annual_salary) not in shown
    assert SAMPLE.employee_code not in shown


def test_missing_gender_is_explained_instead_of_guessed(seeded_client: TestClient) -> None:
    question = "How many male engineers are in India?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: json.dumps(
                    {
                        "status": "unsupported",
                        "reason": "Gender is not stored for employees.",
                    }
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "unsupported"
    assert body["plan"] is None
    assert body["result"] is None
    assert "data available in Compensation Hub" in str(body["answer"])
    assert "Gender is not stored" in str(body["answer"])


@pytest.mark.parametrize(
    "raw",
    [
        "not json at all",
        json.dumps({"status": "plan"}),
        json.dumps(
            {
                "status": "plan",
                "plan": {
                    "kind": "aggregate",
                    "metric": "total_payroll",
                    "sql": "SELECT * FROM compensation",
                },
            }
        ),
        json.dumps(
            {
                "status": "plan",
                "plan": {
                    "kind": "employees",
                    "filters": {},
                    "update": {"annual_salary": "*1.1"},
                },
            }
        ),
        json.dumps(
            {
                "status": "plan",
                "plan": {
                    "kind": "share",
                    "metric": "average_salary",
                    "denominator_filters": {},
                },
            }
        ),
        json.dumps({"status": "execute", "sql": "DELETE FROM compensation"}),
    ],
)
def test_invalid_or_sql_like_planner_output_is_rejected(
    seeded_client: TestClient,
    raw: str,
) -> None:
    question = "Anything"
    install(seeded_client, FakePlanner({question: raw}))

    body = ask(seeded_client, question)

    assert body["status"] == "unsupported"
    assert body["plan"] is None
    assert body["result"] is None


def test_unknown_dimension_value_is_reported_instead_of_guessed(
    seeded_client: TestClient,
) -> None:
    question = "What is the total payroll for Atlantis?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    {
                        "kind": "aggregate",
                        "metric": "total_payroll",
                        "filters": {"countries": ["Atlantis"]},
                    }
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "unsupported"
    assert "Atlantis" in str(body["answer"])


def test_provider_outage_reports_unavailable_without_breaking_other_features(
    seeded_client: TestClient,
) -> None:
    install(seeded_client, BrokenPlanner())

    response = seeded_client.post(
        "/analytics/ask",
        json={"question": "How many employees?", "history": []},
    )

    assert response.status_code == 503
    assert "Ask Compensation is currently unavailable" in response.json()["detail"]
    assert seeded_client.get("/analytics/summary").status_code == 200
    assert seeded_client.get("/employees").status_code == 200


def test_question_and_history_are_bounded(seeded_client: TestClient) -> None:
    install(seeded_client, FakePlanner({}))

    assert seeded_client.post("/analytics/ask", json={"question": "hi"}).status_code == 422
    assert seeded_client.post("/analytics/ask", json={"question": "x" * 501}).status_code == 422

    plan = {"kind": "aggregate", "metric": "employee_count"}
    history = [{"question": "How many employees?", "plan": plan}] * 7
    response = seeded_client.post(
        "/analytics/ask",
        json={"question": "What about now?", "history": history},
    )
    assert response.status_code == 422


def test_default_planner_is_unavailable_until_a_provider_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    planner = build_query_planner(Settings(_env_file=None))

    assert isinstance(planner, UnconfiguredQueryPlanner)
    with pytest.raises(PlannerUnavailableError):
        planner.plan(
            "How many employees?",
            PlannerContext((), (), (), (), ()),
        )
