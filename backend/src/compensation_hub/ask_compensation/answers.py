"""Deterministic wording for Ask Compensation results.

Every sentence here is composed by application code from the validated query and the rows
PostgreSQL returned; the model never writes an answer or a figure.
"""

from decimal import Decimal

from compensation_hub.ask_compensation.execution import CellValue, QueryResult, ResultColumn
from compensation_hub.ask_compensation.validation import ValidatedQuery

ANALYTICS_DIMENSIONS = frozenset({"country", "department", "job_title"})
COMPARISON_SYMBOLS = {"gt": ">", "gte": "≥", "lt": "<", "lte": "≤", "eq": "=", "ne": "≠"}


def format_value(value: CellValue, column: ResultColumn) -> str:
    if value is None:
        return "not available"
    if column.type == "count" and isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, Decimal):
        if column.type == "money":
            return f"{column.currency} {value:,.2f}"
        if column.type == "percent":
            return f"{value:,.2f}%"
        return f"{value:,.2f}"
    return str(value)


def primary_column(query: ValidatedQuery) -> str | None:
    """The figure the question is about: the final calculation, otherwise the first measure."""
    if query.kind == "rows":
        return None
    if query.calculations:
        return query.calculations[-1].name
    return query.measures[0].name


def _uses_money(query: ValidatedQuery) -> bool:
    if query.kind == "rows":
        return any(spec.kind == "money" for spec in query.fields)
    return any(measure.unit == "money" for measure in query.measures) or any(
        condition.field.kind == "money" for condition in query.conditions
    )


def compose_answer(query: ValidatedQuery, result: QueryResult) -> str:
    money_note = (
        f" Amounts are in {query.currency} at the fixed exchange rates."
        if _uses_money(query)
        else ""
    )
    shown = len(result.rows)

    if query.kind == "aggregate" and not query.group_by:
        if not result.rows:
            return "No figures match the conditions." + money_note
        row = result.rows[0]
        primary = primary_column(query)
        ordered = sorted(
            zip(result.columns, row.values, strict=True), key=lambda item: item[0].key != primary
        )
        figures = "; ".join(
            f"{column.label}: {format_value(value, column)}" for column, value in ordered
        )
        return f"{figures}.{money_note}"

    if query.kind == "rows":
        noun = "employee" if result.total_rows == 1 else "employees"
    elif len(query.group_by) == 1:
        spec = query.group_by[0]
        noun = spec.label if result.total_rows == 1 else spec.plural
    else:
        noun = "group" if result.total_rows == 1 else "groups"

    if shown == 0:
        return "No employees match the conditions." if query.kind == "rows" else f"No {noun} match."
    if result.total_rows > shown:
        return f"Showing the first {shown:,} of {result.total_rows:,} {noun}.{money_note}"
    return f"{shown:,} {noun}.{money_note}"


def describe_query(query: ValidatedQuery) -> str:
    """A plain reading of what was computed, so the HR Manager can check the interpretation."""
    parts: list[str] = []
    if query.kind == "rows":
        parts.append("Employees, showing " + ", ".join(spec.label for spec in query.fields))
    else:
        labels = query.labels()
        names = [item.name for item in query.measures] + [item.name for item in query.calculations]
        measures = "; ".join(labels[name] for name in names)
        if query.group_by:
            measures += " by " + " and ".join(spec.label for spec in query.group_by)
        parts.append(measures)
    if query.conditions:
        parts.append("where " + "; ".join(condition.description for condition in query.conditions))
    if query.having:
        labels = query.labels()
        parts.append(
            "only where "
            + "; ".join(
                f"{labels[condition.key]} {COMPARISON_SYMBOLS[condition.op]} "
                f"{condition.value.normalize():,f}"
                for condition in query.having
            )
        )
    if query.order:
        labels = query.labels()
        parts.append(
            "ordered by "
            + ", ".join(
                f"{labels[order.key]} {'highest' if order.descending else 'lowest'} first"
                for order in query.order
            )
        )
    if query.limit is not None:
        parts.append(f"at most {query.limit}")
    if _uses_money(query):
        parts.append(f"amounts in {query.currency}")
    return " · ".join(parts)


def analytics_view(query: ValidatedQuery) -> dict[str, str | None] | None:
    """Describe the Analytics workspace view with the same figures, if the query has one.

    Analytics shows headcount, payroll, or average salary in USD, optionally by one dimension and
    filtered to exact dimension values; anything beyond that has no equivalent view.
    """
    if query.kind != "aggregate" or query.calculations or query.having or query.currency != "USD":
        return None
    if len(query.measures) != 1 or len(query.group_by) > 1:
        return None
    measure = query.measures[0]
    if measure.conditions:
        return None
    salary = measure.field is not None and measure.field.name == "salary"
    if measure.function == "count" and measure.field is None:
        metric = "headcount"
    elif salary and measure.function == "sum":
        metric = "payroll"
    elif salary and measure.function == "avg":
        metric = "average"
    else:
        return None
    group = query.group_by[0].name if query.group_by else None
    if group is not None and group not in ANALYTICS_DIMENSIONS:
        return None

    view: dict[str, str | None] = {"group_by": group, "metric": metric}
    for condition in query.conditions:
        name = condition.field.name
        if condition.op != "eq" or name not in ANALYTICS_DIMENSIONS or name in view:
            return None
        view[name] = condition.values[0]
    return view
