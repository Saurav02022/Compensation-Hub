"""Deterministic wording for Ask Compensation results.

Every figure in an answer is taken from the rows PostgreSQL returned and phrased by application
code; the model never writes an answer or a number.
"""

from decimal import Decimal

from sqlglot import exp

from compensation_hub.ask_compensation.execution import CellValue, QueryResult, ResultColumn

ANALYTICS_DIMENSIONS = frozenset({"country", "department", "job_title"})
NUMERIC_TYPES = frozenset({"count", "money", "percent", "number"})


def format_value(value: CellValue, column: ResultColumn) -> str:
    if value is None:
        return "not available"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    if isinstance(value, Decimal):
        if column.type == "money" and column.currency:
            return f"{column.currency} {value:,.2f}"
        if column.type == "percent":
            return f"{value:,.2f}%"
        return f"{value:,.2f}" if column.type == "money" else f"{value.normalize():,f}"
    return str(value)


def is_scalar(result: QueryResult) -> bool:
    """One row of figures with no labels is shown as a headline rather than a table."""
    return len(result.rows) == 1 and all(column.type in NUMERIC_TYPES for column in result.columns)


def primary_column(result: QueryResult, requested: str | None) -> str | None:
    """The headline figure: the column the planner named, otherwise the last figure."""
    keys = [column.key for column in result.columns]
    if requested is not None and requested.lower() in keys:
        return requested.lower()
    numeric = [column.key for column in result.columns if column.type in NUMERIC_TYPES]
    return numeric[-1] if numeric else None


def compose_answer(result: QueryResult, primary: str | None, currency: str) -> str:
    money_note = (
        f" Amounts are in {currency} at the fixed exchange rates."
        if any(column.type == "money" and column.currency for column in result.columns)
        else ""
    )
    shown = len(result.rows)
    if shown == 0:
        return "No rows match the question."
    if is_scalar(result):
        row = result.rows[0]
        ordered = sorted(
            zip(result.columns, row.values, strict=True), key=lambda item: item[0].key != primary
        )
        figures = "; ".join(
            f"{column.label}: {format_value(value, column)}" for column, value in ordered
        )
        return f"{figures}.{money_note}"
    noun = "result" if result.total_rows == 1 else "results"
    if result.total_rows > shown:
        return f"Showing the first {shown:,} of {result.total_rows:,} {noun}.{money_note}"
    return f"{shown:,} {noun}.{money_note}"


def _dimension_filters(where: exp.Expr | None) -> dict[str, str] | None:
    if where is None:
        return {}
    filters: dict[str, str] = {}
    conditions = list(where.flatten()) if isinstance(where, exp.And) else [where]
    for condition in conditions:
        if not isinstance(condition, exp.EQ):
            return None
        column, value = condition.this, condition.expression
        if isinstance(value, exp.Column):
            column, value = value, column
        if not (
            isinstance(column, exp.Column)
            and column.name in ANALYTICS_DIMENSIONS
            and isinstance(value, exp.Literal)
            and value.is_string
            and column.name not in filters
        ):
            return None
        filters[column.name] = str(value.this)
    return filters


def _metric(node: exp.Expr) -> str | None:
    if isinstance(node, exp.Round):
        node = node.this
    if isinstance(node, exp.Count) and (
        isinstance(node.this, exp.Star)
        or (isinstance(node.this, exp.Column) and node.this.name == "employee_id")
    ):
        return "headcount"
    if isinstance(node, (exp.Sum, exp.Avg)) and isinstance(node.this, exp.Column):
        if node.this.name == "salary_usd":
            return "payroll" if isinstance(node, exp.Sum) else "average"
    return None


def analytics_view(tree: exp.Query, currency: str) -> dict[str, str | None] | None:
    """The Analytics workspace view that shows the same figures, if the query has one.

    Analytics shows headcount, payroll, or average salary in USD over the employees surface,
    optionally by one dimension and filtered to exact dimension values.
    """
    if currency != "USD" or not isinstance(tree, exp.Select):
        return None
    if tree.args.get("with_") or tree.args.get("joins") or tree.args.get("having"):
        return None
    source = tree.args.get("from_")
    if source is None or not isinstance(source.this, exp.Table) or source.this.name != "employees":
        return None
    filters = _dimension_filters(tree.args["where"].this if tree.args.get("where") else None)
    if filters is None:
        return None
    group = tree.args.get("group")
    group_columns = group.expressions if group else []
    if len(group_columns) > 1:
        return None
    dimension = None
    if group_columns:
        grouped = group_columns[0]
        if not isinstance(grouped, exp.Column) or grouped.name not in ANALYTICS_DIMENSIONS:
            return None
        dimension = grouped.name

    metrics = []
    for projection in tree.selects:
        value = projection.unalias()
        if isinstance(value, exp.Column) and value.name == dimension:
            continue
        metrics.append(_metric(value))
    if len(metrics) != 1 or metrics[0] is None:
        return None
    return {"group_by": dimension, "metric": metrics[0], **filters}
