"""Checks a structurally valid query against the catalog and the current data.

The output is a resolved query the executor can turn into SQL without further decisions. Every
rejection carries a message for the HR Manager: ``MissingDataError`` when the question needs
data Compensation Hub does not hold, ``InvalidQueryError`` when the plan is internally
inconsistent (an operation that does not suit a field, an unknown reference, a unit mismatch).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from compensation_hub.ask_compensation.catalog import (
    AGGREGATE_FUNCTIONS,
    FIELDS,
    FILTER_OPERATORS,
    STORED_DATA_DESCRIPTION,
    FieldSpec,
)
from compensation_hub.ask_compensation.plan import (
    Calculation,
    CalculationOperator,
    ComparisonOperator,
    Condition,
    Measure,
    Query,
)

DEFAULT_ROW_LIMIT = 25
MAX_CALCULATION_DEPTH = 3
MAX_NUMBER_MAGNITUDE = Decimal("1e15")
MAX_LISTED_VALUES = 30

# count: whole employees; money: amounts in the answer currency; percent: a share out of 100;
# number: a unitless ratio or scaled count.
Unit = Literal["count", "money", "percent", "number"]


class MissingDataError(Exception):
    def __init__(self, missing: Sequence[str], message: str) -> None:
        super().__init__(message)
        self.missing = tuple(missing)
        self.message = message


class InvalidQueryError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class DataContext:
    """Facts about the current data that plans are validated against.

    ``vocabulary`` maps each category field to the values present in the data; ``fx_rates``
    maps each configured currency to its fixed rate to USD.
    """

    vocabulary: Mapping[str, Sequence[str]]
    fx_rates: Mapping[str, Decimal]


@dataclass(frozen=True)
class ResolvedCondition:
    field: FieldSpec
    op: str
    # Canonical category values, a text fragment, or a salary threshold already in USD.
    values: tuple[str, ...] = ()
    threshold_usd: Decimal | None = None
    description: str = ""


@dataclass(frozen=True)
class ResolvedMeasure:
    name: str
    function: str
    field: FieldSpec | None
    conditions: tuple[ResolvedCondition, ...]
    unit: Unit
    label: str


@dataclass(frozen=True)
class ResolvedCalculation:
    name: str
    op: CalculationOperator
    left: str | Decimal
    right: str | Decimal
    unit: Unit
    label: str


@dataclass(frozen=True)
class ResolvedHaving:
    key: str
    op: ComparisonOperator
    value: Decimal


@dataclass(frozen=True)
class ResolvedOrder:
    key: str
    descending: bool


@dataclass(frozen=True)
class ValidatedQuery:
    kind: Literal["rows", "aggregate"]
    conditions: tuple[ResolvedCondition, ...]
    currency: str
    target_rate: Decimal
    limit: int | None
    order: tuple[ResolvedOrder, ...]
    # rows
    fields: tuple[FieldSpec, ...] = ()
    # aggregate
    group_by: tuple[FieldSpec, ...] = ()
    measures: tuple[ResolvedMeasure, ...] = ()
    calculations: tuple[ResolvedCalculation, ...] = ()
    having: tuple[ResolvedHaving, ...] = ()

    def labels(self) -> dict[str, str]:
        """Display labels for every field, measure, and calculation the query refers to."""
        labels = {spec.name: spec.label for spec in (*self.fields, *self.group_by)}
        labels.update({measure.name: measure.label for measure in self.measures})
        labels.update({calculation.name: calculation.label for calculation in self.calculations})
        return labels


def _listing(values: Sequence[str]) -> str:
    if len(values) > MAX_LISTED_VALUES:
        return ", ".join(values[:MAX_LISTED_VALUES]) + ", …"
    return ", ".join(values)


def _field(name: str) -> FieldSpec:
    spec = FIELDS.get(name)
    if spec is None:
        described = name.replace("_", " ")
        raise MissingDataError(
            [described],
            f"Compensation Hub does not store {described!r} for employees. "
            f"{STORED_DATA_DESCRIPTION}.",
        )
    return spec


def _number(value: str | Decimal | None, what: str) -> Decimal:
    if isinstance(value, Decimal):
        number = value
    else:
        try:
            number = Decimal(str(value).replace(",", ""))
        except ArithmeticError as error:
            raise InvalidQueryError(f"{what} needs a number, not {value!r}.") from error
    if not number.is_finite() or abs(number) >= MAX_NUMBER_MAGNITUDE:
        raise InvalidQueryError(f"{what} is outside the supported range.")
    return number


def _rate(context: DataContext, currency: str) -> Decimal:
    rate = context.fx_rates.get(currency)
    if rate is None:
        configured = ", ".join(sorted(context.fx_rates))
        raise MissingDataError(
            [f"{currency} exchange rate"],
            f"There is no exchange rate for {currency}, so amounts cannot be expressed in it. "
            f"Configured currencies: {configured}.",
        )
    return rate


def _canonical(spec: FieldSpec, value: str, context: DataContext) -> str:
    known = context.vocabulary.get(spec.name, ())
    by_folded = {item.casefold(): item for item in known}
    canonical = by_folded.get(value.casefold())
    if canonical is None:
        raise MissingDataError(
            [f"{spec.label} {value!r}"],
            f"The employee data has no {spec.label} {value!r}. "
            f"The {spec.plural} in the data are: {_listing(known)}.",
        )
    return canonical


def _format_number(value: Decimal) -> str:
    return f"{value.normalize():,f}"


def _condition(condition: Condition, context: DataContext, currency: str) -> ResolvedCondition:
    spec = _field(condition.field)
    allowed = FILTER_OPERATORS[spec.kind]
    if condition.op not in allowed:
        raise InvalidQueryError(f"The {spec.label} cannot be filtered with {condition.op!r}.")

    if condition.op in ("in", "not_in"):
        if not condition.values:
            raise InvalidQueryError(f"The {condition.op!r} filter on {spec.label} needs values.")
        values = tuple(dict.fromkeys(_canonical(spec, v, context) for v in condition.values))
        verb = "is one of" if condition.op == "in" else "is none of"
        return ResolvedCondition(
            spec, condition.op, values, None, f"{spec.label} {verb} {', '.join(values)}"
        )

    if condition.values:
        raise InvalidQueryError(f"The {condition.op!r} filter on {spec.label} takes one value.")
    if condition.value is None:
        raise InvalidQueryError(f"The {condition.op!r} filter on {spec.label} needs a value.")

    if spec.kind == "money":
        threshold_currency = condition.currency or currency
        amount = _number(condition.value, f"The {spec.label} filter")
        threshold_usd = amount * _rate(context, threshold_currency)
        symbol = {"gt": ">", "gte": "≥", "lt": "<", "lte": "≤"}[condition.op]
        return ResolvedCondition(
            spec,
            condition.op,
            (),
            threshold_usd,
            f"{spec.label} {symbol} {threshold_currency} {_format_number(amount)}",
        )

    if condition.currency is not None:
        raise InvalidQueryError(f"A currency applies only to salary filters, not {spec.label}.")
    text = str(condition.value).strip()
    if not text:
        raise InvalidQueryError(f"The {spec.label} filter needs a value.")
    if spec.kind == "category":
        value = _canonical(spec, text, context)
        verb = "is" if condition.op == "eq" else "is not"
        return ResolvedCondition(spec, condition.op, (value,), None, f"{spec.label} {verb} {value}")
    verbs = {"eq": "is", "contains": "contains", "starts_with": "starts with"}
    return ResolvedCondition(
        spec, condition.op, (text,), None, f"{spec.label} {verbs[condition.op]} {text!r}"
    )


def _conditions(
    conditions: Sequence[Condition], context: DataContext, currency: str
) -> tuple[ResolvedCondition, ...]:
    return tuple(_condition(condition, context, currency) for condition in conditions)


MEASURE_LABELS = {
    "sum": "Total",
    "avg": "Average",
    "median": "Median",
    "min": "Lowest",
    "max": "Highest",
}


def _measure(measure: Measure, context: DataContext, currency: str) -> ResolvedMeasure:
    spec = _field(measure.field) if measure.field is not None else None
    if spec is None:
        if measure.function != "count":
            raise InvalidQueryError(f"The {measure.function!r} measure needs a field.")
        unit: Unit = "count"
        label = "Employees"
    else:
        if measure.function not in AGGREGATE_FUNCTIONS[spec.kind]:
            raise InvalidQueryError(
                f"The {spec.label} cannot be aggregated with {measure.function!r}."
            )
        if measure.function == "count":
            unit, label = "count", f"Employees with a {spec.label}"
        elif measure.function == "count_distinct":
            unit, label = "count", f"Distinct {spec.plural}"
        else:
            unit, label = "money", f"{MEASURE_LABELS[measure.function]} {spec.label}"

    conditions = _conditions(measure.filters, context, currency)
    if conditions:
        label += f" ({'; '.join(condition.description for condition in conditions)})"
    return ResolvedMeasure(measure.name, measure.function, spec, conditions, unit, label)


# Units an arithmetic operation produces from two named operands; missing pairs are invalid,
# so a plan cannot, for example, multiply two amounts of money or add money to a headcount.
NAMED_OPERAND_UNITS: dict[tuple[CalculationOperator, Unit, Unit], Unit] = {
    **{("add", unit, unit): unit for unit in ("count", "money", "percent", "number")},
    **{("subtract", unit, unit): unit for unit in ("count", "money", "percent", "number")},
    **{("percent", unit, unit): "percent" for unit in ("count", "money", "number")},
    ("divide", "money", "money"): "number",
    ("divide", "count", "count"): "number",
    ("divide", "percent", "percent"): "number",
    ("divide", "number", "number"): "number",
    ("divide", "money", "count"): "money",
    ("divide", "money", "number"): "money",
    ("divide", "count", "number"): "number",
    ("multiply", "number", "number"): "number",
    ("multiply", "money", "number"): "money",
    ("multiply", "number", "money"): "money",
    ("multiply", "count", "number"): "number",
    ("multiply", "number", "count"): "number",
    ("multiply", "percent", "number"): "percent",
    ("multiply", "number", "percent"): "percent",
}
# A literal scales or offsets a named value and keeps its unit, except that scaling a headcount
# by a fraction is no longer a whole count.
SCALED_COUNT_UNIT: Unit = "number"
OPERATOR_SYMBOLS: dict[CalculationOperator, str] = {
    "add": "+",
    "subtract": "−",
    "multiply": "×",
    "divide": "÷",
    "percent": "as % of",
}


def _calculation(
    calculation: Calculation,
    known: dict[str, tuple[Unit, str, int]],
) -> tuple[ResolvedCalculation, int]:
    def operand(value: str | Decimal) -> tuple[Unit | None, str, int]:
        if isinstance(value, Decimal):
            _number(value, f"The {calculation.name!r} calculation")
            return None, _format_number(value), 0
        if value not in known:
            raise InvalidQueryError(
                f"The {calculation.name!r} calculation refers to {value!r}, which is not an "
                "earlier measure or calculation."
            )
        unit, label, depth = known[value]
        return unit, label, depth

    left_unit, left_label, left_depth = operand(calculation.left)
    right_unit, right_label, right_depth = operand(calculation.right)
    op = calculation.op

    if left_unit is None and right_unit is None:
        raise InvalidQueryError(f"The {calculation.name!r} calculation uses no measure.")
    if isinstance(calculation.right, Decimal) and op in ("divide", "percent"):
        if calculation.right == 0:
            raise InvalidQueryError(f"The {calculation.name!r} calculation divides by zero.")

    unit: Unit | None
    if left_unit is not None and right_unit is not None:
        unit = NAMED_OPERAND_UNITS.get((op, left_unit, right_unit))
    elif op == "percent" or (op == "divide" and left_unit is None):
        # "x as % of 50" or "100 ÷ x" do not describe a meaningful compensation figure.
        unit = "percent" if op == "percent" and left_unit is not None else None
    else:
        named = left_unit if left_unit is not None else right_unit
        assert named is not None
        unit = SCALED_COUNT_UNIT if named == "count" and op in ("multiply", "divide") else named

    if unit is None:
        raise InvalidQueryError(
            f"The {calculation.name!r} calculation cannot {op} "
            f"{left_unit or 'a number'} and {right_unit or 'a number'}."
        )

    depth = max(left_depth, right_depth) + 1
    if depth > MAX_CALCULATION_DEPTH:
        raise InvalidQueryError(
            f"The {calculation.name!r} calculation nests more than "
            f"{MAX_CALCULATION_DEPTH} levels of arithmetic."
        )
    label = f"{left_label} {OPERATOR_SYMBOLS[op]} {right_label}"
    resolved = ResolvedCalculation(
        calculation.name, op, calculation.left, calculation.right, unit, label
    )
    return resolved, depth


def _validate_rows(
    query: Query, conditions: tuple[ResolvedCondition, ...], rate: Decimal
) -> ValidatedQuery:
    if query.group_by or query.measures or query.calculations or query.having:
        raise InvalidQueryError(
            "A row query lists employees; it cannot also group or aggregate them."
        )
    if not query.fields:
        raise InvalidQueryError("A row query needs at least one field to show.")

    fields = [_field(name) for name in dict.fromkeys(query.fields)]
    order: list[ResolvedOrder] = []
    for key in query.order_by:
        spec = _field(key.key)
        if not spec.orderable:
            raise InvalidQueryError(f"Rows cannot be ordered by {spec.label}.")
        if spec not in fields:
            fields.append(spec)
        order.append(ResolvedOrder(spec.name, key.direction == "desc"))
    local_salary, currency = FIELDS["local_salary"], FIELDS["currency"]
    if local_salary in fields and currency not in fields:
        # A local amount is meaningless without its currency, so it is always shown beside it.
        fields.insert(fields.index(local_salary) + 1, currency)

    return ValidatedQuery(
        kind="rows",
        conditions=conditions,
        currency=query.currency,
        target_rate=rate,
        limit=query.limit or DEFAULT_ROW_LIMIT,
        order=tuple(order),
        fields=tuple(fields),
    )


def _validate_aggregate(
    query: Query, context: DataContext, conditions: tuple[ResolvedCondition, ...], rate: Decimal
) -> ValidatedQuery:
    if query.fields:
        raise InvalidQueryError(
            "An aggregate query summarizes employees; list fields with a row query instead."
        )
    if not query.measures:
        raise InvalidQueryError("An aggregate query needs at least one measure.")

    group_by: list[FieldSpec] = []
    for name in dict.fromkeys(query.group_by):
        spec = _field(name)
        if not spec.groupable:
            raise InvalidQueryError(f"Employees cannot be grouped by {spec.label}.")
        group_by.append(spec)

    group_names = {spec.name for spec in group_by}
    known: dict[str, tuple[Unit, str, int]] = {}

    def claim(name: str) -> None:
        if name in known or name in group_names:
            raise InvalidQueryError(f"The name {name!r} is used more than once.")

    measures: list[ResolvedMeasure] = []
    for measure in query.measures:
        claim(measure.name)
        resolved = _measure(measure, context, query.currency)
        measures.append(resolved)
        known[resolved.name] = (resolved.unit, resolved.label, 0)

    calculations: list[ResolvedCalculation] = []
    for calculation in query.calculations:
        claim(calculation.name)
        resolved_calculation, depth = _calculation(calculation, known)
        calculations.append(resolved_calculation)
        known[calculation.name] = (resolved_calculation.unit, resolved_calculation.label, depth)

    having = []
    for condition in query.having:
        if condition.key not in known:
            raise InvalidQueryError(f"The condition refers to {condition.key!r}, which is unknown.")
        having.append(
            ResolvedHaving(condition.key, condition.op, _number(condition.value, "The condition"))
        )

    order: list[ResolvedOrder] = []
    for key in query.order_by:
        if key.key not in known and key.key not in group_names:
            raise InvalidQueryError(
                f"Results cannot be ordered by {key.key!r}; order by a grouped field, "
                "a measure, or a calculation."
            )
        order.append(ResolvedOrder(key.key, key.direction == "desc"))

    return ValidatedQuery(
        kind="aggregate",
        conditions=conditions,
        currency=query.currency,
        target_rate=rate,
        limit=(query.limit or None) if group_by else None,
        order=tuple(order),
        group_by=tuple(group_by),
        measures=tuple(measures),
        calculations=tuple(calculations),
        having=tuple(having),
    )


def validate_query(query: Query, context: DataContext) -> ValidatedQuery:
    rate = _rate(context, query.currency)
    conditions = _conditions(query.filters, context, query.currency)
    if query.kind == "rows":
        return _validate_rows(query, conditions, rate)
    return _validate_aggregate(query, context, conditions, rate)
