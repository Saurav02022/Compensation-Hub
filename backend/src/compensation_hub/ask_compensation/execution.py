"""Runs validated SQL in a read-only PostgreSQL transaction and types the result.

The executed text is the one rendered from the validated syntax tree, with the approved surface
defined as CTEs in front of it and every string literal bound as a parameter. PostgreSQL enforces
read-only execution and a statement timeout on top of the validation.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from compensation_hub.analytics.service import MissingFxRateError
from compensation_hub.ask_compensation.sql_validation import ValidatedSql
from compensation_hub.ask_compensation.surface import EMPLOYEES, FX_RATES
from compensation_hub.db.models import Compensation, FxRate

STATEMENT_TIMEOUT = "5s"
CENTS = Decimal("0.01")
RATIO_PLACES = Decimal("0.0001")

ColumnType = Literal["text", "count", "money", "percent", "number"]
CellValue = str | int | Decimal | None


@dataclass(frozen=True)
class ResultColumn:
    key: str
    label: str
    type: ColumnType
    # The currency of a money column, or the key of the column that holds each row's currency.
    currency: str | None = None
    currency_key: str | None = None


@dataclass(frozen=True)
class ResultRow:
    values: tuple[CellValue, ...]
    employee_id: int | None = None


@dataclass(frozen=True)
class QueryResult:
    columns: tuple[ResultColumn, ...]
    rows: tuple[ResultRow, ...]
    total_rows: int


def begin_read_only(session: Session, statement_timeout: str | None = None) -> None:
    """Start a transaction PostgreSQL itself refuses to write in, with a statement timeout.

    Validation already admits only SELECT queries; this makes the database enforce it too. Must
    be the first statement of the transaction. Planned queries use ``STATEMENT_TIMEOUT``.
    """
    timeout = statement_timeout or STATEMENT_TIMEOUT
    session.execute(text("SET TRANSACTION READ ONLY"))
    session.execute(text(f"SET LOCAL statement_timeout = '{timeout}'"))


def ensure_fx_rates(session: Session) -> None:
    """Fail loudly if a stored salary cannot be normalized, rather than silently dropping it."""
    missing = session.scalars(
        select(Compensation.currency_code)
        .distinct()
        .outerjoin(FxRate, FxRate.currency_code == Compensation.currency_code)
        .where(FxRate.currency_code.is_(None))
    ).all()
    if missing:
        raise MissingFxRateError(missing)


def column_label(name: str) -> str:
    """A readable label from a result column name; the currency is shown separately."""
    surface = EMPLOYEES.column(name) or FX_RATES.column(name)
    if surface is not None and surface.unit != "money":
        return surface.label
    words = [word for word in name.split("_") if word]
    if words and words[-1].lower() == "usd":
        words = words[:-1]
    if not words or name.startswith("_col"):
        return "Value"
    label = " ".join(words)
    return label[0].upper() + label[1:]


def _decimal(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _whole_or_decimal(value: Any) -> int | Decimal:
    number = _decimal(value)
    if number == number.to_integral_value():
        return int(number)
    return number.quantize(RATIO_PLACES, rounding=ROUND_HALF_UP)


def execute_sql(session: Session, query: ValidatedSql, currency: str, rate: Decimal) -> QueryResult:
    """Run the query and express amounts in ``currency``.

    Amounts arrive in USD, the only currency the surface combines across employees, and are
    converted with ``rate`` (the seeded USD value of one unit of ``currency``) in Decimal.
    Local salaries keep their own currency, named by the salary_currency column beside them.
    """
    connection = session.connection()
    records = connection.exec_driver_sql(query.executable, query.parameters).all()
    total = len(records)
    if query.row_cap is not None and total > query.row_cap:
        records = records[: query.row_cap]
        total = int(connection.exec_driver_sql(query.count_sql, query.parameters).scalar_one())

    link = next((i for i, column in enumerate(query.columns) if column.unit == "id"), None)
    shown = [i for i, column in enumerate(query.columns) if column.unit != "id"]

    columns = []
    for index in shown:
        column = query.columns[index]
        label = column_label(column.name)
        if column.unit == "money":
            columns.append(ResultColumn(column.name, label, "money", currency=currency))
        elif column.unit == "money_local":
            columns.append(
                ResultColumn(column.name, label, "money", currency_key="salary_currency")
            )
        elif column.unit in ("count", "percent", "text"):
            columns.append(ResultColumn(column.name, label, column.unit))
        else:
            columns.append(ResultColumn(column.name, label, "number"))

    rows = []
    for record in records:
        values: list[CellValue] = []
        for index in shown:
            raw = record[index]
            unit = query.columns[index].unit
            if raw is None:
                values.append(None)
            elif unit == "money":
                values.append((_decimal(raw) / rate).quantize(CENTS, rounding=ROUND_HALF_UP))
            elif unit in ("money_local", "percent"):
                values.append(_decimal(raw).quantize(CENTS, rounding=ROUND_HALF_UP))
            elif unit in ("count", "number", "rate"):
                values.append(_whole_or_decimal(raw))
            else:
                values.append(str(raw))
        employee_id = record[link] if link is not None else None
        rows.append(ResultRow(tuple(values), employee_id=employee_id))

    return QueryResult(tuple(columns), tuple(rows), total)
