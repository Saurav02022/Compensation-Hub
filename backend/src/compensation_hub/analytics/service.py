from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from compensation_hub.db.models import Compensation, Employee, FxRate

GroupBy = Literal["country", "department", "job_title"]
SortBy = Literal["key", "employee_count", "total_payroll_usd", "average_salary_usd"]

ANALYTICS_CURRENCY = "USD"
MAX_BREAKDOWN_LIMIT = 100
CENTS = Decimal("0.01")


class MissingFxRateError(Exception):
    def __init__(self, currency_codes: Sequence[str]) -> None:
        codes = ", ".join(sorted(currency_codes))
        super().__init__(f"No exchange rate is configured for currency {codes}")
        self.currency_codes = tuple(sorted(currency_codes))


@dataclass(frozen=True)
class AnalyticsFilters:
    country: str | None = None
    department: str | None = None
    job_title: str | None = None


@dataclass(frozen=True)
class Summary:
    employee_count: int
    total_payroll_usd: Decimal
    average_salary_usd: Decimal | None


@dataclass(frozen=True)
class BreakdownRow:
    key: str
    employee_count: int
    total_payroll_usd: Decimal
    average_salary_usd: Decimal | None


GROUP_COLUMNS: dict[str, InstrumentedAttribute[str]] = {
    "country": Employee.country,
    "department": Employee.department,
    "job_title": Employee.job_title,
}

# salary_in_usd = annual_salary * rate_to_usd, evaluated by PostgreSQL in NUMERIC arithmetic.
SALARY_USD = Compensation.annual_salary * FxRate.rate_to_usd


def _filtered_employees[T: tuple[object, ...]](
    statement: Select[T], filters: AnalyticsFilters
) -> Select[T]:
    if filters.country:
        statement = statement.where(Employee.country == filters.country)
    if filters.department:
        statement = statement.where(Employee.department == filters.department)
    if filters.job_title:
        statement = statement.where(Employee.job_title == filters.job_title)
    return statement


def _aggregate_statement(
    filters: AnalyticsFilters, *group_columns: ColumnElement[str]
) -> Select[tuple[object, ...]]:
    statement = (
        select(
            *group_columns,
            func.count(Employee.id).label("employee_count"),
            func.coalesce(func.sum(SALARY_USD), 0).label("total_payroll_usd"),
            func.avg(SALARY_USD).label("average_salary_usd"),
        )
        .select_from(Employee)
        .outerjoin(Compensation, Compensation.employee_id == Employee.id)
        .outerjoin(FxRate, FxRate.currency_code == Compensation.currency_code)
    )
    return _filtered_employees(statement, filters)


def _ensure_fx_rates(session: Session, filters: AnalyticsFilters) -> None:
    """Fail loudly if any matching salary cannot be normalized, rather than dropping it."""
    statement = (
        select(Compensation.currency_code)
        .distinct()
        .join(Employee, Employee.id == Compensation.employee_id)
        .outerjoin(FxRate, FxRate.currency_code == Compensation.currency_code)
        .where(FxRate.currency_code.is_(None))
    )
    missing = session.scalars(_filtered_employees(statement, filters)).all()
    if missing:
        raise MissingFxRateError(missing)


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


def _optional_money(value: object | None) -> Decimal | None:
    return None if value is None else _money(value)


def get_summary(session: Session, filters: AnalyticsFilters) -> Summary:
    _ensure_fx_rates(session, filters)
    row = session.execute(_aggregate_statement(filters)).one()
    return Summary(
        employee_count=int(row.employee_count),
        total_payroll_usd=_money(row.total_payroll_usd),
        average_salary_usd=_optional_money(row.average_salary_usd),
    )


def get_breakdown(
    session: Session,
    group_by: GroupBy,
    filters: AnalyticsFilters,
    *,
    sort_by: SortBy = "key",
    descending: bool = False,
    limit: int | None = None,
) -> list[BreakdownRow]:
    _ensure_fx_rates(session, filters)
    group_column = GROUP_COLUMNS[group_by]
    statement = _aggregate_statement(filters, group_column.label("key")).group_by(group_column)

    sort_column = group_column if sort_by == "key" else statement.selected_columns[sort_by]
    ordering = [sort_column.desc().nulls_last() if descending else sort_column.asc().nulls_last()]
    if sort_by != "key":
        ordering.append(group_column.asc())
    statement = statement.order_by(*ordering)
    if limit is not None:
        statement = statement.limit(limit)

    return [
        BreakdownRow(
            key=row.key,
            employee_count=int(row.employee_count),
            total_payroll_usd=_money(row.total_payroll_usd),
            average_salary_usd=_optional_money(row.average_salary_usd),
        )
        for row in session.execute(statement)
    ]
