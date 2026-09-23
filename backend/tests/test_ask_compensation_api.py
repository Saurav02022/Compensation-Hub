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


def predicate(field: str, operator: str, value: object) -> dict[str, object]:
    return {"field": field, "operator": operator, "value": value}


def aggregate(
    function: str,
    field: str | None = None,
    *,
    where: list[dict[str, object]] | None = None,
    distinct: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": "aggregate",
        "function": function,
        "distinct": distinct,
        "where": where or [],
    }
    if field is not None:
        payload["field"] = field
    return payload


def field(name: str) -> dict[str, object]:
    return {"kind": "field", "field": name}


def literal(value: object) -> dict[str, object]:
    return {"kind": "literal", "value": value}


def binary(operator: str, left: object, right: object) -> dict[str, object]:
    return {"kind": "binary", "operator": operator, "left": left, "right": right}


def item(
    alias: str,
    label: str,
    expression: object,
    format_kind: str,
) -> dict[str, object]:
    return {
        "alias": alias,
        "label": label,
        "expression": expression,
        "format": format_kind,
    }


def plan(
    select_items: list[dict[str, object]],
    *,
    where: list[dict[str, object]] | None = None,
    group_by: list[str] | None = None,
    distinct_rows: bool = False,
    order_by: list[dict[str, object]] | None = None,
    limit: int = 50,
) -> dict[str, object]:
    return {
        "select": select_items,
        "where": where or [],
        "group_by": group_by or [],
        "distinct": distinct_rows,
        "order_by": order_by or [],
        "limit": limit,
    }


def planned(query_plan: dict[str, object]) -> str:
    return json.dumps({"status": "plan", "plan": query_plan})


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
    query_plan = plan(
        [
            item(
                "employee_count",
                "Employee count",
                aggregate("count"),
                "count",
            )
        ],
        where=[
            predicate("country", "equals", SAMPLE.country),
            predicate("department", "equals", SAMPLE.department),
        ],
    )
    install(seeded_client, FakePlanner({question: planned(query_plan)}))
    expected = seeded_client.get(
        "/analytics/summary",
        params={"country": SAMPLE.country, "department": SAMPLE.department},
    ).json()["employee_count"]

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    assert body["result"] == {
        "kind": "scalar",
        "currency_by_column": {},
        "columns": [
            {
                "key": "employee_count",
                "label": "Employee count",
                "format": "count",
            }
        ],
        "rows": [{"employee_count": expected}],
    }


def test_grouped_query_can_rank_departments(seeded_client: TestClient) -> None:
    question = "Which departments have the highest average salary?"
    query_plan = plan(
        [
            item("department", "Department", field("department"), "text"),
            item(
                "average_salary",
                "Average salary",
                aggregate("average", "salary_usd"),
                "currency",
            ),
        ],
        group_by=["department"],
        order_by=[{"key": "average_salary", "direction": "desc"}],
    )
    install(seeded_client, FakePlanner({question: planned(query_plan)}))

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    result = body["result"]
    assert isinstance(result, dict)
    assert result["kind"] == "table"
    assert result["currency_by_column"] == {"average_salary": "USD"}
    rows = result["rows"]
    assert isinstance(rows, list)
    values = [Decimal(str(row["average_salary"])) for row in rows]
    assert values == sorted(values, reverse=True)


def test_median_is_available_without_a_special_question_handler(
    seeded_client: TestClient,
) -> None:
    question = f"What is the median salary in {SAMPLE.department}?"
    query_plan = plan(
        [
            item(
                "median_salary",
                "Median salary",
                aggregate("median", "salary_usd"),
                "currency",
            )
        ],
        where=[predicate("department", "equals", SAMPLE.department)],
    )
    install(seeded_client, FakePlanner({question: planned(query_plan)}))

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    assert body["result"]["kind"] == "scalar"  # type: ignore[index]
    assert body["result"]["currency_by_column"] == {"median_salary": "USD"}  # type: ignore[index]
    assert Decimal(str(body["result"]["rows"][0]["median_salary"])) > 0  # type: ignore[index]


def test_employee_ranking_is_a_bounded_row_query(seeded_client: TestClient) -> None:
    question = f"Who are the three highest-paid employees in {SAMPLE.country}?"
    query_plan = plan(
        [
            item("employee", "Employee", field("full_name"), "text"),
            item("employee_code", "Employee code", field("employee_code"), "text"),
            item("salary", "Salary", field("salary_usd"), "currency"),
        ],
        where=[predicate("country", "equals", SAMPLE.country)],
        order_by=[{"key": "salary", "direction": "desc"}],
        limit=3,
    )
    install(seeded_client, FakePlanner({question: planned(query_plan)}))

    body = ask(seeded_client, question)

    result = body["result"]
    assert isinstance(result, dict)
    rows = result["rows"]
    assert isinstance(rows, list)
    assert 0 < len(rows) <= 3
    salaries = [Decimal(str(row["salary"])) for row in rows]
    assert salaries == sorted(salaries, reverse=True)


def test_distinct_values_are_answered_from_stored_fields(seeded_client: TestClient) -> None:
    question = f"What currencies are used in {SAMPLE.country}?"
    query_plan = plan(
        [item("currency", "Currency", field("currency_code"), "text")],
        where=[predicate("country", "equals", SAMPLE.country)],
        distinct_rows=True,
    )
    install(seeded_client, FakePlanner({question: planned(query_plan)}))

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    assert body["result"]["rows"] == [{"currency": SAMPLE.currency_code}]  # type: ignore[index]


def test_percentage_uses_generic_expression_tree(seeded_client: TestClient) -> None:
    question = f"What percentage of employees are in {SAMPLE.department}?"
    part = aggregate(
        "count",
        where=[predicate("department", "equals", SAMPLE.department)],
    )
    whole = aggregate("count")
    percentage = binary("multiply", binary("divide", part, whole), literal(100))
    query_plan = plan(
        [item("share", "Employee share", percentage, "percent")]
    )
    install(seeded_client, FakePlanner({question: planned(query_plan)}))
    expected_count = seeded_client.get(
        "/analytics/summary",
        params={"department": SAMPLE.department},
    ).json()["employee_count"]

    body = ask(seeded_client, question)

    expected = (Decimal(expected_count) / Decimal(60) * 100).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    assert Decimal(str(body["result"]["rows"][0]["share"])) == expected  # type: ignore[index]


def test_follow_up_reuses_validated_intent_and_converts_currency(
    seeded_client: TestClient,
    db_session: Session,
) -> None:
    first = "What is the total payroll in Germany?"
    follow_up = "Convert that to Indian currency."
    payroll = aggregate(
        "sum",
        "salary_usd",
        where=[predicate("country", "equals", "Germany")],
    )
    first_plan = plan([item("payroll", "Total payroll", payroll, "currency")])
    second_plan = plan(
        [
            item(
                "payroll",
                "Total payroll",
                {
                    "kind": "currency",
                    "currency_code": "INR",
                    "expression": payroll,
                },
                "currency",
            )
        ]
    )
    planner = FakePlanner(
        {
            first: planned(first_plan),
            follow_up: planned(second_plan),
        }
    )
    install(seeded_client, planner)

    first_body = ask(seeded_client, first)
    validated_first_plan = first_body["plan"]
    assert isinstance(validated_first_plan, dict)

    second_body = ask(
        seeded_client,
        follow_up,
        history=[{"question": first, "plan": validated_first_plan}],
    )

    assert second_body["status"] == "answered"
    assert second_body["result"]["currency_by_column"] == {"payroll": "INR"}  # type: ignore[index]
    assert len(planner.histories[1]) == 1
    assert '"Germany"' in planner.histories[1][0].plan_json

    rate = db_session.scalar(select(FxRate.rate_to_usd).where(FxRate.currency_code == "INR"))
    assert rate is not None
    usd = Decimal(str(first_body["result"]["rows"][0]["payroll"]))  # type: ignore[index]
    expected = (usd / Decimal(rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    actual = Decimal(str(second_body["result"]["rows"][0]["payroll"]))  # type: ignore[index]
    assert actual == expected


def test_comparison_uses_generic_conditional_aggregates(seeded_client: TestClient) -> None:
    countries = list(dict.fromkeys(employee.country for employee in DATASET.employees))
    first_country, second_country = countries[:2]
    question = f"How much larger is {first_country} headcount than {second_country}?"
    left = aggregate(
        "count",
        where=[predicate("country", "equals", first_country)],
    )
    right = aggregate(
        "count",
        where=[predicate("country", "equals", second_country)],
    )
    difference = binary("subtract", left, right)
    query_plan = plan(
        [item("difference", "Headcount difference", difference, "count")]
    )
    install(seeded_client, FakePlanner({question: planned(query_plan)}))

    body = ask(seeded_client, question)

    assert body["status"] == "answered"
    assert isinstance(body["result"]["rows"][0]["difference"], int)  # type: ignore[index]


def test_planner_receives_vocabulary_but_not_employee_rows(
    seeded_client: TestClient,
) -> None:
    question = "What is our payroll?"
    query_plan = plan(
        [
            item(
                "payroll",
                "Total payroll",
                aggregate("sum", "salary_usd"),
                "currency",
            )
        ]
    )
    planner = FakePlanner({question: planned(query_plan)})
    install(seeded_client, planner)

    ask(seeded_client, question)

    context = planner.contexts[0]
    assert set(context.departments) == {employee.department for employee in DATASET.employees}
    assert set(context.countries) == {employee.country for employee in DATASET.employees}
    assert set(context.job_titles) == {employee.job_title for employee in DATASET.employees}
    assert context.currency_codes

    shown = json.dumps(
        {
            "countries": list(context.countries),
            "departments": list(context.departments),
            "job_titles": list(context.job_titles),
            "currency_codes": list(context.currency_codes),
        }
    )
    assert SAMPLE.full_name not in shown
    assert str(SAMPLE.annual_salary) not in shown
    assert SAMPLE.employee_code not in shown


def test_missing_field_is_explained_instead_of_guessed(seeded_client: TestClient) -> None:
    question = "How many employees match a field we do not store?"
    install(
        seeded_client,
        FakePlanner(
            {
                question: json.dumps(
                    {
                        "status": "unsupported",
                        "missing": "The requested employee attribute is not stored.",
                    }
                )
            }
        ),
    )

    body = ask(seeded_client, question)

    assert body["status"] == "unsupported"
    assert body["plan"] is None
    assert body["result"] is None
    assert "Missing data" in str(body["answer"])
    assert "not stored" in str(body["answer"])


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        json.dumps({"status": "plan"}),
        json.dumps(
            {
                "status": "plan",
                "plan": {
                    "select": [
                        {
                            "alias": "unsafe",
                            "label": "Unsafe",
                            "format": "text",
                            "expression": {"kind": "field", "field": "full_name"},
                        }
                    ],
                    "sql": "SELECT * FROM compensation",
                },
            }
        ),
        json.dumps({"status": "execute", "sql": "DELETE FROM compensation"}),
    ],
)
def test_invalid_or_sql_like_output_is_rejected(
    seeded_client: TestClient,
    raw: str,
) -> None:
    question = "Anything"
    install(seeded_client, FakePlanner({question: raw}))

    body = ask(seeded_client, question)

    assert body["status"] == "unsupported"
    assert body["plan"] is None
    assert body["result"] is None


def test_local_salary_aggregate_is_rejected_before_execution(
    seeded_client: TestClient,
) -> None:
    question = "What is total local salary?"
    unsafe_plan = plan(
        [
            item(
                "total",
                "Total",
                aggregate("sum", "annual_salary"),
                "currency",
            )
        ]
    )
    install(seeded_client, FakePlanner({question: planned(unsafe_plan)}))

    body = ask(seeded_client, question)

    assert body["status"] == "unsupported"
    assert "valid read-only data query" in str(body["answer"])


def test_unknown_controlled_value_is_reported(seeded_client: TestClient) -> None:
    question = "What is the total payroll for Atlantis?"
    query_plan = plan(
        [
            item(
                "payroll",
                "Total payroll",
                aggregate("sum", "salary_usd"),
                "currency",
            )
        ],
        where=[predicate("country", "equals", "Atlantis")],
    )
    install(seeded_client, FakePlanner({question: planned(query_plan)}))

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


def test_question_history_and_row_limit_are_bounded(seeded_client: TestClient) -> None:
    install(seeded_client, FakePlanner({}))

    assert seeded_client.post("/analytics/ask", json={"question": "hi"}).status_code == 422
    assert seeded_client.post("/analytics/ask", json={"question": "x" * 501}).status_code == 422

    valid_plan = plan(
        [item("count", "Count", aggregate("count"), "count")]
    )
    history = [{"question": "How many employees?", "plan": valid_plan}] * 7
    response = seeded_client.post(
        "/analytics/ask",
        json={"question": "What about now?", "history": history},
    )
    assert response.status_code == 422

    too_large = dict(valid_plan)
    too_large["limit"] = 101
    question = "Show everything"
    install(seeded_client, FakePlanner({question: planned(too_large)}))
    body = ask(seeded_client, question)
    assert body["status"] == "unsupported"


def test_default_planner_is_unavailable_without_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    planner = build_query_planner(Settings(_env_file=None))

    assert isinstance(planner, UnconfiguredQueryPlanner)
    with pytest.raises(PlannerUnavailableError):
        planner.plan("How many employees?", PlannerContext((), (), (), ()))
