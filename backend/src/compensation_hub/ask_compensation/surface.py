"""The relational data Ask Compensation can query.

The model writes SQL against two logical relations, ``employees`` and ``fx_rates``. They are not
database tables: the executor defines them as CTEs over the real tables, so a question can only
ever read what is described here. Answerability comes from this surface. A question that needs
anything else, such as gender, tenure, or salary history, is reported as missing data; exposing
a new attribute to Ask Compensation means adding it here deliberately.
"""

from dataclasses import dataclass
from typing import Literal

# How a value may be used and shown. ``money`` is an annual amount in USD at the seeded rates and
# can be compared and combined across countries. ``money_local`` is an amount in the employee's
# own currency; amounts in different currencies cannot be combined, so it is only ever shown or
# compared, never aggregated or used in arithmetic.
Unit = Literal["id", "text", "count", "money", "money_local", "rate", "number", "percent"]


@dataclass(frozen=True)
class SurfaceColumn:
    name: str
    unit: Unit
    sql_type: str
    description: str
    label: str


@dataclass(frozen=True)
class SurfaceRelation:
    name: str
    description: str
    columns: tuple[SurfaceColumn, ...]
    definition: str

    def column(self, name: str) -> SurfaceColumn | None:
        return next((column for column in self.columns if column.name == name), None)


EMPLOYEES = SurfaceRelation(
    name="employees",
    description="One row per employee with their current annual salary.",
    columns=(
        SurfaceColumn("employee_id", "id", "INT", "Internal employee identifier.", "Employee ID"),
        SurfaceColumn(
            "employee_code",
            "text",
            "TEXT",
            "Unique employee code such as EMP00042.",
            "Employee code",
        ),
        SurfaceColumn("full_name", "text", "TEXT", "Employee full name.", "Name"),
        SurfaceColumn("country", "text", "TEXT", "Country the employee is based in.", "Country"),
        SurfaceColumn(
            "department", "text", "TEXT", "Department the employee works in.", "Department"
        ),
        SurfaceColumn("job_title", "text", "TEXT", "Employee job title.", "Job title"),
        SurfaceColumn(
            "salary_currency",
            "text",
            "TEXT",
            "Currency code the salary is paid in.",
            "Salary currency",
        ),
        SurfaceColumn(
            "salary_local",
            "money_local",
            "DECIMAL",
            "Current annual salary in salary_currency. Show or compare only; never aggregate.",
            "Local salary",
        ),
        SurfaceColumn(
            "salary_usd",
            "money",
            "DECIMAL",
            "Current annual salary converted to USD at the fixed exchange rates.",
            "Salary in USD",
        ),
    ),
    # Employees without compensation keep a row with NULL salary columns, so they count as
    # employees but contribute no salary, the same semantics as the Analytics service.
    definition=(
        "SELECT e.id AS employee_id, e.employee_code, e.full_name, e.country, e.department, "
        "e.job_title, c.currency_code AS salary_currency, c.annual_salary AS salary_local, "
        "c.annual_salary * f.rate_to_usd AS salary_usd "
        "FROM public.employees AS e "
        "LEFT JOIN public.compensation AS c ON c.employee_id = e.id "
        "LEFT JOIN public.fx_rates AS f ON f.currency_code = c.currency_code"
    ),
)

FX_RATES = SurfaceRelation(
    name="fx_rates",
    description="The fixed exchange rates, one row per configured currency.",
    columns=(
        SurfaceColumn("currency_code", "text", "TEXT", "Currency code.", "Currency"),
        SurfaceColumn(
            "rate_to_usd",
            "rate",
            "DECIMAL",
            "USD value of one unit of the currency.",
            "Rate to USD",
        ),
    ),
    definition="SELECT currency_code, rate_to_usd FROM public.fx_rates",
)

RELATIONS: dict[str, SurfaceRelation] = {
    relation.name: relation for relation in (EMPLOYEES, FX_RATES)
}

# Columns whose distinct values are shown to the planner, so filters use real values.
VOCABULARY_COLUMNS = ("country", "department", "job_title", "salary_currency")

_DESCRIBED = [
    column.label[0].lower() + column.label[1:]
    for column in EMPLOYEES.columns
    if column.unit != "id"
]
STORED_DATA_DESCRIPTION = (
    f"The employee data covers: {', '.join(_DESCRIBED[:-1])}, and {_DESCRIBED[-1]} "
    "(current annual salaries only)"
)


def vocabulary_query(column: str) -> str:
    """Distinct non-null values of a surface column, read through the surface definition."""
    if column not in VOCABULARY_COLUMNS:
        raise ValueError(f"{column} is not a vocabulary column")
    return (
        f"SELECT DISTINCT {column} FROM ({EMPLOYEES.definition}) AS surface "
        f"WHERE {column} IS NOT NULL ORDER BY {column}"
    )


def schema_mapping() -> dict[str, dict[str, str]]:
    """The surface in the shape sqlglot's qualifier expects."""
    return {
        relation.name: {column.name: column.sql_type for column in relation.columns}
        for relation in RELATIONS.values()
    }
