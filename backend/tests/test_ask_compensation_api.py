import json
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

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
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.contexts: list[PlannerContext] = []
        self.histories: list[tuple[PlannerTurn, ...]] = []

    def plan(
        self,
        question: str,
        context: PlannerContext,
        history: Sequence[PlannerTurn] = (),
    ) -> str:
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


def query(
    *,
    name: str = "answer",
    select_items: list[dict[str, object]],
    filters: list[dict[str, object]] | None = None,
    group_by: list[str] | None = None,
    order_by: list[dict[str, object]] | None = None,
    distinct: bool = False,
    limit: int | None = None,
    target_currency: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": name,
        "select": select_items,
        "filters": filters or [],
        "group_by": group_by or [],
        "order_by": order_by or [],
        "distinct": distinct,
    }
    if limit is not None:
        payload["limit"] = limit
    if target_currency is not None:
        payload["target_currency"] = target_currency
    return payload


def planned(
    queries: list[dict[str, object]],
    calculation: dict[str, object] | None = None,
) -> str:
    plan: dict[str, object] = {"queries": queries}
    if calculation is not None:
        plan["calculation"] = calculation
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


def test_count_question_is_derived_from_database(seeded_client: TestClient) -> None:
    question = f"How many {SAMPLE.department} employees are based in {SAMPLE.country}?"
    planner = FakePlanner(
        {
            question: planned(
                [
                    query(
                        select_items=[{"alias": "employee_count", "aggregate": "count"}],
                        filters=[
                            {"field": "country", "op": "eq", "values": [SAMPLE.country]},
                            {
                                "field": "department",
                                "op": "eq",
                                "values": [SAMPLE.department],
                            },
                        ],
                    )
                ]
            )
        }
    )
    install(seeded_client, planner)
    expected = seeded_client.get(
        "/analytics/summary",
        params={"country": SAMPLE.country, "department": SAMPLE.department},
    ).json()["employee_count"]

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    assert body["result"] == {
        "kind": "scalar",
        "currency": None,
        "columns": [{"key": "employee_count", "label": "Employee Count", "format": "count"}],
        "rows": [{"employee_count": expected}],
    }
    assert body["analytics_path"] == (
        f"/analytics?country={SAMPLE.country}&department={SAMPLE.department}&metric=headcount"
    )


def test_generic_grouped_query_can_rank_departments(seeded_client: TestClient) -> None:
    question = "Which departments have the highest average salary?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    [
                        query(
                            select_items=[
                                {"alias": "department", "field": "department"},
                                {
                                    "alias": "average_salary",
                                    "field": "salary_usd",
                                    "aggregate": "avg",
                                },
                            ],
                            group_by=["department"],
                            order_by=[{"key": "average_salary", "direction": "desc"}],
                        )
                    ]
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    result = body["result"]
    assert isinstance(result, dict)
    assert result["kind"] == "table"
    assert result["currency"] == "USD"
    rows = result["rows"]
    assert isinstance(rows, list)
    assert rows
    salaries = [Decimal(str(row["average_salary"])) for row in rows]
    assert salaries == sorted(salaries, reverse=True)


def test_generic_statistics_include_median(seeded_client: TestClient) -> None:
    question = f"What is the median salary in {SAMPLE.department}?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    [
                        query(
                            select_items=[
                                {
                                    "alias": "median_salary",
                                    "field": "salary_usd",
                                    "aggregate": "median",
                                }
                            ],
                            filters=[
                                {
                                    "field": "department",
                                    "op": "eq",
                                    "values": [SAMPLE.department],
                                }
                            ],
                        )
                    ]
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    assert body["result"]["kind"] == "scalar"  # type: ignore[index]
    assert body["result"]["currency"] == "USD"  # type: ignore[index]
    assert Decimal(str(body["result"]["rows"][0]["median_salary"])) > 0  # type: ignore[index]


def test_employee_ranking_is_a_bounded_generic_row_query(seeded_client: TestClient) -> None:
    question = f"Who are the three highest-paid employees in {SAMPLE.country}?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    [
                        query(
                            select_items=[
                                {"alias": "employee", "field": "full_name"},
                                {"alias": "employee_code", "field": "employee_code"},
                                {"alias": "job_title", "field": "job_title"},
                                {"alias": "country", "field": "country"},
                                {"alias": "salary", "field": "salary_usd"},
                            ],
                            filters=[
                                {"field": "country", "op": "eq", "values": [SAMPLE.country]}
                            ],
                            order_by=[{"key": "salary", "direction": "desc"}],
                            limit=3,
                        )
                    ]
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    result = body["result"]
    assert isinstance(result, dict)
    assert result["kind"] == "table"
    rows = result["rows"]
    assert isinstance(rows, list)
    assert 0 < len(rows) <= 3
    salaries = [Decimal(str(row["salary"])) for row in rows]
    assert salaries == sorted(salaries, reverse=True)


def test_distinct_values_are_answered_from_stored_fields(seeded_client: TestClient) -> None:
    question = f"What currencies are used in {SAMPLE.country}?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    [
                        query(
                            select_items=[{"alias": "currency", "field": "currency_code"}],
                            filters=[
                                {"field": "country", "op": "eq", "values": [SAMPLE.country]}
                            ],
                            distinct=True,
                        )
                    ]
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    rows = body["result"]["rows"]  # type: ignore[index]
    assert rows == [{"currency": SAMPLE.currency_code}]


def test_percentage_is_calculated_from_two_safe_scalar_queries(
    seeded_client: TestClient,
) -> None:
    question = f"What percentage of employees are in {SAMPLE.department}?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    [
                        query(
                            name="part",
                            select_items=[{"alias": "count", "aggregate": "count"}],
                            filters=[
                                {
                                    "field": "department",
                                    "op": "eq",
                                    "values": [SAMPLE.department],
                                }
                            ],
                        ),
                        query(
                            name="whole",
                            select_items=[{"alias": "count", "aggregate": "count"}],
                        ),
                    ],
                    calculation={
                        "op": "percentage",
                        "left": {"query": "part", "column": "count"},
                        "right": {"query": "whole", "column": "count"},
                        "label": "Employee share",
                        "format": "percent",
                    },
                )
            }
        ),
    )
    expected_count = seeded_client.get(
        "/analytics/summary",
        params={"department": SAMPLE.department},
    ).json()["employee_count"]

    body = ask(seeded_client, question)

    expected = (
        Decimal(expected_count) / Decimal(60) * 100
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert body["status"] == "answered"
    assert Decimal(str(body["result"]["rows"][0]["value"])) == expected  # type: ignore[index]


def test_follow_up_reuses_validated_intent_and_converts_currency(
    seeded_client: TestClient,
    db_session: Session,
) -> None:
    first = "What is the total payroll in Germany?"
    follow_up = "Convert that to Indian currency."
    first_program = [
        query(
            select_items=[
                {"alias": "total_payroll", "field": "salary_usd", "aggregate": "sum"}
            ],
            filters=[{"field": "country", "op": "eq", "values": ["Germany"]}],
        )
    ]
    planner = FakePlanner(
        {
            first: planned(first_program),
            follow_up: planned(
                [
                    query(
                        select_items=[
                            {
                                "alias": "total_payroll",
                                "field": "salary_usd",
                                "aggregate": "sum",
                            }
                        ],
                        filters=[{"field": "country", "op": "eq", "values": ["Germany"]}],
                        target_currency="INR",
                    )
                ]
            ),
        }
    )
    install(seeded_client, planner)

    first_body = ask(seeded_client, first)
    first_plan = first_body["plan"]
    assert isinstance(first_plan, dict)
    second_body = ask(
        seeded_client,
        follow_up,
        history=[{"question": first, "plan": first_plan}],
    )

    assert second_body["status"] == "answered"
    assert second_body["result"]["currency"] == "INR"  # type: ignore[index]
    assert "converted to INR" in str(second_body["interpretation"])
    assert len(planner.histories[1]) == 1
    assert '"Germany"' in planner.histories[1][0].plan_json

    rate = db_session.scalar(select(FxRate.rate_to_usd).where(FxRate.currency_code == "INR"))
    assert rate is not None
    usd = Decimal(str(first_body["result"]["rows"][0]["total_payroll"]))  # type: ignore[index]
    expected = (usd / Decimal(rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    actual = Decimal(str(second_body["result"]["rows"][0]["total_payroll"]))  # type: ignore[index]
    assert actual == expected


def test_generic_comparison_uses_arithmetic_over_scalar_queries(
    seeded_client: TestClient,
) -> None:
    countries = list(dict.fromkeys(employee.country for employee in DATASET.employees))
    first_country, second_country = countries[:2]
    question = f"How much larger is {first_country} headcount than {second_country}?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    [
                        query(
                            name="left",
                            select_items=[{"alias": "count", "aggregate": "count"}],
                            filters=[
                                {"field": "country", "op": "eq", "values": [first_country]}
                            ],
                        ),
                        query(
                            name="right",
                            select_items=[{"alias": "count", "aggregate": "count"}],
                            filters=[
                                {"field": "country", "op": "eq", "values": [second_country]}
                            ],
                        ),
                    ],
                    calculation={
                        "op": "subtract",
                        "left": {"query": "left", "column": "count"},
                        "right": {"query": "right", "column": "count"},
                        "label": "Headcount difference",
                        "format": "count",
                    },
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    assert body["result"]["kind"] == "scalar"  # type: ignore[index]
    assert isinstance(body["result"]["rows"][0]["value"], int)  # type: ignore[index]


def test_planner_receives_schema_vocabulary_but_not_employee_rows(
    seeded_client: TestClient,
) -> None:
    question = "What is our payroll?"
    planner = FakePlanner(
        {
            question: planned(
                [
                    query(
                        select_items=[
                            {
                                "alias": "total_payroll",
                                "field": "salary_usd",
                                "aggregate": "sum",
                            }
                        ]
                    )
                ]
            )
        }
    )
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


def test_missing_field_is_explained_instead_of_guessed(seeded_client: TestClient) -> None:
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
    assert "Gender is not stored" in str(body["answer"])


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        json.dumps({"status": "plan"}),
        json.dumps(
            {
                "status": "plan",
                "plan": {
                    "queries": [
                        {
                            "name": "unsafe",
                            "select": [{"alias": "x", "aggregate": "count"}],
                            "sql": "SELECT * FROM compensation",
                        }
                    ]
                },
            }
        ),
        json.dumps(
            {
                "status": "plan",
                "plan": {
                    "queries": [
                        {
                            "name": "unsafe",
                            "select": [{"alias": "x", "aggregate": "count"}],
                            "update": {"annual_salary": "999999"},
                        }
                    ]
                },
            }
        ),
        json.dumps({"status": "execute", "sql": "DELETE FROM compensation"}),
    ],
)
def test_sql_or_write_like_planner_output_is_rejected(
    seeded_client: TestClient,
    raw: str,
) -> None:
    question = "Anything"
    install(seeded_client, FakePlanner({question: raw}))

    body = ask(seeded_client, question)

    assert body["status"] == "unsupported"
    assert body["plan"] is None
    assert body["result"] is None


def test_local_salary_cannot_be_aggregated_across_currencies(
    seeded_client: TestClient,
) -> None:
    question = "What is total local salary?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    [
                        query(
                            select_items=[
                                {
                                    "alias": "total",
                                    "field": "annual_salary",
                                    "aggregate": "sum",
                                }
                            ]
                        )
                    ]
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "unsupported"
    assert "across currencies" in str(body["answer"])


def test_unknown_controlled_value_is_reported(seeded_client: TestClient) -> None:
    question = "What is the total payroll for Atlantis?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: planned(
                    [
                        query(
                            select_items=[
                                {
                                    "alias": "total_payroll",
                                    "field": "salary_usd",
                                    "aggregate": "sum",
                                }
                            ],
                            filters=[
                                {"field": "country", "op": "eq", "values": ["Atlantis"]}
                            ],
                        )
                    ]
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "unsupported"
    assert "Atlantis" in str(body["answer"])


def test_provider_outage_does_not_break_core_features(seeded_client: TestClient) -> None:
    install(seeded_client, BrokenPlanner())

    response = seeded_client.post(
        "/analytics/ask",
        json={"question": "How many employees?", "history": []},
    )

    assert response.status_code == 503
    assert "Ask Compensation is currently unavailable" in response.json()["detail"]
    assert seeded_client.get("/analytics/summary").status_code == 200
    assert seeded_client.get("/employees").status_code == 200


def test_question_history_and_query_limits_are_bounded(seeded_client: TestClient) -> None:
    install(seeded_client, FakePlanner({}))

    assert seeded_client.post("/analytics/ask", json={"question": "hi"}).status_code == 422
    assert seeded_client.post("/analytics/ask", json={"question": "x" * 501}).status_code == 422

    valid_plan = {
        "queries": [
            {
                "name": "answer",
                "select": [{"alias": "employee_count", "aggregate": "count"}],
            }
        ]
    }
    history = [{"question": "How many employees?", "plan": valid_plan}] * 7
    assert (
        seeded_client.post(
            "/analytics/ask",
            json={"question": "What about now?", "history": history},
        ).status_code
        == 422
    )

    too_many_queries = [
        query(name=f"q{index}", select_items=[{"alias": "count", "aggregate": "count"}])
        for index in range(5)
    ]
    response = seeded_client.post(
        "/analytics/ask",
        json={
            "question": "Do everything.",
            "history": [
                {
                    "question": "Previous valid question",
                    "plan": {"queries": too_many_queries},
                }
            ],
        },
    )
    assert response.status_code == 422


def test_default_planner_is_unavailable_without_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    planner = build_query_planner(Settings(_env_file=None))

    assert isinstance(planner, UnconfiguredQueryPlanner)
    with pytest.raises(PlannerUnavailableError):
        planner.plan(
            "How many employees?",
            PlannerContext((), (), (), (), ()),
        )
