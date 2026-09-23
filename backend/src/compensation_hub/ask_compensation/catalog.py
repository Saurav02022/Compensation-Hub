"""The employee and compensation data that Ask Compensation can reason about.

Answerability is decided by this catalog. A question can be answered only from the fields listed
here and the operations their kind allows; anything else is reported as data the product does
not store. Exposing a new attribute to Ask Compensation means adding it here deliberately.
"""

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import ColumnElement

from compensation_hub.analytics.service import SALARY_USD
from compensation_hub.db.models import Compensation, Employee

# category: a small controlled vocabulary, validated against the values in the data.
# text: free text matched case-insensitively.
# money: an annual salary normalized through the fixed exchange rates, so it can be compared,
#   aggregated, and converted across countries.
# local_money: an annual salary in the employee's own currency; only shown on employee rows,
#   because amounts in different currencies cannot be compared or combined.
FieldKind = Literal["category", "text", "money", "local_money"]

FILTER_OPERATORS: dict[FieldKind, frozenset[str]] = {
    "category": frozenset({"eq", "ne", "in", "not_in"}),
    "text": frozenset({"eq", "contains", "starts_with"}),
    "money": frozenset({"gt", "gte", "lt", "lte"}),
    "local_money": frozenset(),
}

AGGREGATE_FUNCTIONS: dict[FieldKind, frozenset[str]] = {
    "category": frozenset({"count", "count_distinct"}),
    "text": frozenset({"count", "count_distinct"}),
    "money": frozenset({"count", "sum", "avg", "median", "min", "max"}),
    "local_money": frozenset(),
}


# Compared by identity: each field is a single catalog entry, and comparing SQL expressions by
# value would build SQL rather than answer the question.
@dataclass(frozen=True, eq=False)
class FieldSpec:
    name: str
    kind: FieldKind
    label: str
    plural: str
    description: str
    expression: ColumnElement[Any]

    @property
    def groupable(self) -> bool:
        return self.kind == "category"

    @property
    def orderable(self) -> bool:
        return self.kind != "local_money"


FIELDS: dict[str, FieldSpec] = {
    spec.name: spec
    for spec in (
        FieldSpec(
            "employee_code",
            "text",
            "employee code",
            "employee codes",
            "Unique employee code such as EMP00042.",
            Employee.employee_code.expression,
        ),
        FieldSpec(
            "full_name",
            "text",
            "name",
            "names",
            "Employee full name.",
            Employee.full_name.expression,
        ),
        FieldSpec(
            "country",
            "category",
            "country",
            "countries",
            "Country the employee is based in.",
            Employee.country.expression,
        ),
        FieldSpec(
            "department",
            "category",
            "department",
            "departments",
            "Department the employee works in.",
            Employee.department.expression,
        ),
        FieldSpec(
            "job_title",
            "category",
            "job title",
            "job titles",
            "Employee job title.",
            Employee.job_title.expression,
        ),
        FieldSpec(
            "currency",
            "category",
            "salary currency",
            "salary currencies",
            "Currency code the employee's salary is paid in.",
            Compensation.currency_code.expression,
        ),
        FieldSpec(
            "salary",
            "money",
            "salary",
            "salaries",
            "Current annual salary converted to the answer currency with the fixed exchange rates.",
            SALARY_USD,
        ),
        FieldSpec(
            "local_salary",
            "local_money",
            "local salary",
            "local salaries",
            "Current annual salary in the employee's own currency. Employee rows only.",
            Compensation.annual_salary.expression,
        ),
    )
}

# Fields whose values the planner is shown and every filter value is checked against.
VOCABULARY_FIELDS = tuple(spec.name for spec in FIELDS.values() if spec.kind == "category")

STORED_DATA_DESCRIPTION = "The employee data covers: " + ", ".join(
    spec.label for spec in FIELDS.values()
)
