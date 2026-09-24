"""Parses and validates model-written SQL before anything reaches PostgreSQL.

The model's text is never executed as written. It is parsed into a syntax tree with sqlglot,
checked against an allowlist of statement types, syntax nodes, relations, columns, and
functions, bounded in size and nesting, qualified against the surface, checked for money rules,
rewritten in a few deterministic ways, and only then rendered back to SQL for execution.

Three kinds of rejection are distinguished: ``ForbiddenSqlError`` for anything that is not a
read of the approved surface (writes, other statements, system catalogs, session functions),
``UnknownReferenceError`` for relations or columns that do not exist, which usually means the
question needs data that is not stored, and ``InvalidSqlError`` for everything else.
"""

from dataclasses import dataclass, field
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import OptimizeError, SqlglotError
from sqlglot.optimizer.qualify import qualify

from compensation_hub.ask_compensation.sql_units import (
    LITERAL,
    UnitError,
    UnitInference,
    check_local_money,
    check_projections,
)
from compensation_hub.ask_compensation.surface import RELATIONS, Unit, schema_mapping

DIALECT = "postgres"

# Bounds sized for a 10,000-employee surface: generous enough for multi-step analytical
# questions (group-relative comparisons, per-group rankings, several CTEs), small enough that a
# runaway query is rejected before it reaches the database's statement timeout.
MAX_SQL_LENGTH = 5_000
MAX_NODES = 1_000
MAX_NESTING = 4
MAX_CTES = 8
MAX_JOINS = 4
MAX_SET_OPERATIONS = 4
MAX_ROWS = 100
MAX_INNER_LIMIT = 10_000

ALLOWED_NODES: tuple[type[exp.Expr], ...] = (
    exp.Select,
    exp.Union,
    exp.Intersect,
    exp.Except,
    exp.From,
    exp.Join,
    exp.Where,
    exp.Group,
    exp.Having,
    exp.Order,
    exp.Ordered,
    exp.Limit,
    exp.Offset,
    exp.Distinct,
    exp.With,
    exp.CTE,
    exp.Subquery,
    exp.Alias,
    exp.TableAlias,
    exp.Table,
    exp.Column,
    exp.Identifier,
    exp.Star,
    exp.Literal,
    exp.Boolean,
    exp.Null,
    exp.And,
    exp.Or,
    exp.Not,
    exp.Paren,
    exp.EQ,
    exp.NEQ,
    exp.GT,
    exp.GTE,
    exp.LT,
    exp.LTE,
    exp.Is,
    exp.In,
    exp.Between,
    exp.Like,
    exp.ILike,
    exp.Add,
    exp.Sub,
    exp.Mul,
    exp.Div,
    exp.Neg,
    exp.DPipe,
    exp.Case,
    exp.If,
    exp.Cast,
    exp.DataType,
    exp.Window,
    exp.WindowSpec,
    exp.Filter,
    exp.WithinGroup,
    exp.Tuple,
    exp.Exists,
)

# Aggregates, window functions, and scalar helpers useful for compensation analytics. Anything
# else, including every administrative, file, network, sleep, lock, sequence, and session
# function PostgreSQL offers, is rejected.
ALLOWED_FUNCTIONS: tuple[type[exp.Expr], ...] = (
    exp.Count,
    exp.Sum,
    exp.Avg,
    exp.Min,
    exp.Max,
    exp.Median,
    exp.PercentileCont,
    exp.PercentileDisc,
    exp.Stddev,
    exp.StddevPop,
    exp.StddevSamp,
    exp.Round,
    exp.Abs,
    exp.Floor,
    exp.Ceil,
    exp.Coalesce,
    exp.Nullif,
    exp.Greatest,
    exp.Least,
    exp.Lower,
    exp.Upper,
    exp.Trim,
    exp.Length,
    exp.Concat,
    exp.Rank,
    exp.DenseRank,
    exp.RowNumber,
    exp.Ntile,
    exp.Lag,
    exp.Lead,
    exp.FirstValue,
    exp.LastValue,
)

ALLOWED_CAST_TYPES = (
    exp.DataType.Type.DECIMAL,
    exp.DataType.Type.INT,
    exp.DataType.Type.BIGINT,
    exp.DataType.Type.SMALLINT,
    exp.DataType.Type.TEXT,
    exp.DataType.Type.VARCHAR,
)

# Statement and clause types that express something other than reading the surface.
FORBIDDEN_NODES: tuple[type[exp.Expr], ...] = tuple(
    node
    for node in (
        getattr(exp, name, None)
        for name in (
            "Insert",
            "Update",
            "Delete",
            "Merge",
            "Create",
            "Drop",
            "Alter",
            "TruncateTable",
            "Command",
            "Set",
            "Transaction",
            "Commit",
            "Rollback",
            "Copy",
            "Into",
            "Lock",
            "Grant",
            "Revoke",
            "Use",
            "Describe",
            "Pragma",
            "Analyze",
            "Placeholder",
            "Parameter",
            "Lateral",
            "TableSample",
            "Values",
        )
    )
    if isinstance(node, type)
)
SYSTEM_PREFIXES = ("pg_", "information_schema")


class InvalidSqlError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ForbiddenSqlError(InvalidSqlError):
    """The SQL does something other than read the approved surface."""


class UnknownReferenceError(InvalidSqlError):
    def __init__(self, names: list[str], message: str) -> None:
        super().__init__(message)
        self.names = names


@dataclass(frozen=True)
class OutputColumn:
    name: str
    unit: Unit


@dataclass(frozen=True)
class ValidatedSql:
    """A validated query and everything needed to run and present it."""

    sql: str
    executable: str
    count_sql: str
    columns: tuple[OutputColumn, ...]
    # String literals from the query, bound as parameters of executable and count_sql.
    parameters: dict[str, str]
    # The row cap the application applied, or None when the query's own LIMIT is smaller.
    row_cap: int | None
    tree: exp.Query = field(compare=False, repr=False)


def _function_name(node: exp.Expr) -> str:
    if isinstance(node, exp.Anonymous):
        return str(node.name).lower()
    return type(node).__name__.lower()


def _check_nodes(tree: exp.Expr) -> None:
    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            raise ForbiddenSqlError(
                f"{type(node).__name__.upper()} is not allowed; Ask Compensation only reads data."
            )
        if isinstance(node, ALLOWED_FUNCTIONS):
            continue
        if not isinstance(node, ALLOWED_NODES):
            if isinstance(node, exp.Func):
                name = _function_name(node)
                if name.startswith("pg_") or name in {"set_config", "current_setting", "dblink"}:
                    raise ForbiddenSqlError(f"The function {name} is not allowed.")
                raise InvalidSqlError(f"The function {name} is not available.")
            raise InvalidSqlError(f"The SQL construct {type(node).__name__} is not supported.")
        if isinstance(node, exp.Cast) and not node.to.is_type(*ALLOWED_CAST_TYPES):
            raise InvalidSqlError(
                f"Casting to {node.to.sql(dialect=DIALECT)} is not supported; amounts stay NUMERIC."
            )
        if isinstance(node, exp.Identifier) and "%" in str(node.name):
            raise InvalidSqlError("Names cannot contain %.")
        if isinstance(node, exp.With) and node.args.get("recursive"):
            raise InvalidSqlError("Recursive queries are not supported.")


def _cte_names(tree: exp.Expr) -> set[str]:
    return {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}


def _check_relations(tree: exp.Expr) -> None:
    ctes = _cte_names(tree)
    clashing = ctes & set(RELATIONS)
    if clashing:
        raise InvalidSqlError(f"A CTE cannot be named {', '.join(sorted(clashing))}.")
    unknown: list[str] = []
    for table in tree.find_all(exp.Table):
        name = str(table.name)
        lowered = name.lower()
        if table.args.get("db") or table.args.get("catalog"):
            raise ForbiddenSqlError("Schema-qualified names are not allowed.")
        if not isinstance(table.this, exp.Identifier):
            raise InvalidSqlError("Table functions are not supported.")
        if lowered.startswith(SYSTEM_PREFIXES):
            raise ForbiddenSqlError(f"The relation {name} is not available to Ask Compensation.")
        # A quoted name keeps its case in PostgreSQL, so "Employees" is not employees.
        known = lowered in RELATIONS or lowered in ctes
        if not known or (table.this.quoted and name != lowered):
            unknown.append(name)
    if unknown:
        raise UnknownReferenceError(
            unknown,
            f"The relation {', '.join(unknown)} does not exist. Only employees and fx_rates can "
            "be queried; if the question needs data they do not hold, respond with missing_data.",
        )


def _check_columns(tree: exp.Expr) -> None:
    known = {column.name for relation in RELATIONS.values() for column in relation.columns}
    known |= {str(alias.alias).lower() for alias in tree.find_all(exp.Alias) if alias.alias}
    for table_alias in tree.find_all(exp.TableAlias):
        known |= {str(column.name).lower() for column in table_alias.columns}
    unknown = sorted(
        {
            str(column.name)
            for column in tree.find_all(exp.Column)
            if column.name and str(column.name).lower() not in known
        }
    )
    if unknown:
        raise UnknownReferenceError(
            unknown,
            f"The column {', '.join(unknown)} does not exist. If the question needs data that "
            "is not stored, respond with missing_data.",
        )


def _nesting(node: exp.Expr) -> int:
    depth = 0
    parent = node.parent
    while parent is not None:
        if isinstance(parent, exp.Query):
            depth += 1
        parent = parent.parent
    return depth


def _literal_int(node: exp.Expr | None, what: str) -> int | None:
    if node is None:
        return None
    value = node.expression if isinstance(node, (exp.Limit, exp.Offset)) else node
    if not isinstance(value, exp.Literal) or value.is_string or not value.this.isdigit():
        raise InvalidSqlError(f"{what} must be a whole number.")
    return int(value.this)


def _check_bounds(tree: exp.Query) -> None:
    nodes = list(tree.walk())
    if len(nodes) > MAX_NODES:
        raise InvalidSqlError("The query is too complex.")
    if len(list(tree.find_all(exp.CTE))) > MAX_CTES:
        raise InvalidSqlError(f"The query uses more than {MAX_CTES} CTEs.")
    if len(list(tree.find_all(exp.SetOperation))) > MAX_SET_OPERATIONS:
        raise InvalidSqlError(f"The query combines more than {MAX_SET_OPERATIONS} set operations.")
    for select in tree.find_all(exp.Select):
        if len(select.args.get("joins") or []) > MAX_JOINS:
            raise InvalidSqlError(f"A SELECT joins more than {MAX_JOINS} relations.")
        if _nesting(select) > MAX_NESTING:
            raise InvalidSqlError(f"The query nests more than {MAX_NESTING} levels deep.")
    for limit in tree.find_all(exp.Limit):
        value = _literal_int(limit, "LIMIT")
        maximum = MAX_ROWS if limit.parent is tree else MAX_INNER_LIMIT
        if value is not None and value > maximum:
            raise InvalidSqlError(f"LIMIT {value} is above the maximum of {maximum}.")
    for offset in tree.find_all(exp.Offset):
        value = _literal_int(offset, "OFFSET")
        if value is not None and value > MAX_INNER_LIMIT:
            raise InvalidSqlError(f"OFFSET {value} is above the maximum of {MAX_INNER_LIMIT}.")


def _exact_median(ordered_by: exp.Expr, where: exp.Expr | None) -> exp.Expr:
    def middle(descending: bool) -> exp.Expr:
        ordered = exp.Ordered(this=ordered_by.copy(), desc=descending)
        value: exp.Expr = exp.WithinGroup(
            this=exp.PercentileDisc(this=exp.Literal.number("0.5")),
            expression=exp.Order(expressions=[ordered]),
        )
        if where is not None:
            value = exp.Filter(this=value, expression=where.copy())
        return value

    return exp.Paren(
        this=exp.Div(
            this=exp.Paren(this=exp.Add(this=middle(False), expression=middle(True))),
            expression=exp.Literal.number(2),
        )
    )


def _median_target(node: exp.Expr) -> exp.Expr | None:
    if isinstance(node, exp.Median):
        median_of: exp.Expr = node.this
        return median_of
    if (
        isinstance(node, exp.WithinGroup)
        and isinstance(node.this, exp.PercentileCont)
        and node.this.this.name == "0.5"
    ):
        target: exp.Expr = node.expression.expressions[0].this
        return target
    return None


def _rewrite(tree: exp.Query) -> exp.Query:
    """Deterministic rewrites that keep results exact whatever SQL style the model chose."""
    rewritten = tree.copy()

    # PostgreSQL computes percentile_cont in double precision; averaging the two middle values
    # from percentile_disc gives the median as an exact NUMERIC value.
    for node in list(rewritten.find_all(exp.Filter, exp.WithinGroup, exp.Median)):
        if node.parent is None:
            continue
        if isinstance(node, exp.Filter):
            target = _median_target(node.this)
            if target is not None:
                node.replace(_exact_median(target, node.expression))
        elif not isinstance(node.parent, exp.Filter):
            target = _median_target(node)
            if target is not None:
                node.replace(_exact_median(target, None))

    # Integer division truncates in PostgreSQL and division by zero is an error; every division
    # is made exact and yields NULL when the divisor is zero. Deepest divisions go first so an
    # outer division wraps already-rewritten operands.
    for node in reversed(list(rewritten.find_all(exp.Div))):
        divisor = node.expression
        if not (isinstance(divisor, exp.Literal) and divisor.is_number and divisor.to_py() != 0):
            divisor = exp.Nullif(this=divisor, expression=exp.Literal.number(0))
        node.replace(
            exp.Div(
                this=exp.Cast(this=node.this, to=exp.DataType.build("DECIMAL")),
                expression=divisor,
            )
        )
    return rewritten


def _surface_ctes() -> list[exp.CTE]:
    return [
        exp.CTE(
            this=sqlglot.parse_one(relation.definition, dialect=DIALECT),
            alias=exp.TableAlias(this=exp.to_identifier(relation.name)),
            materialized=False,
        )
        for relation in RELATIONS.values()
    ]


def _with_surface(query: exp.Query) -> exp.Query:
    """Prepend the surface definitions, so employees and fx_rates resolve to them."""
    wrapped = query.copy()
    existing = wrapped.args.get("with_")
    ctes: list[exp.Expr] = [*_surface_ctes(), *(existing.expressions if existing else [])]
    wrapped.set("with_", exp.With(expressions=ctes))
    return wrapped


def _parameterize(query: exp.Query) -> tuple[exp.Query, dict[str, str]]:
    """Replace every string literal with a bound parameter.

    The executed SQL then contains no text taken from the model: values reach PostgreSQL only
    as parameters, and ``%`` in a LIKE pattern cannot be mistaken for a driver placeholder.
    """
    parameterized = query.copy()
    parameters: dict[str, str] = {}
    for literal in list(parameterized.find_all(exp.Literal)):
        if literal.is_string:
            name = f"p{len(parameters)}"
            parameters[name] = str(literal.this)
            literal.replace(exp.Placeholder(this=name))
    return parameterized, parameters


def _render(node: exp.Expr) -> str:
    return node.sql(dialect=DIALECT, comments=False)


def _output_unit(unit: Any, name: str, percent_columns: set[str]) -> Unit:
    if name in percent_columns:
        if unit in ("money", "money_local", "rate", "text", "id"):
            raise InvalidSqlError(f"The column {name} is not a percentage.")
        return "percent"
    if unit == LITERAL:
        return "number"
    resolved: Unit = unit
    return resolved


def validate_sql(sql: str, percent_columns: frozenset[str] = frozenset()) -> ValidatedSql:
    text = sql.strip()
    if not text:
        raise InvalidSqlError("The query is empty.")
    if len(text) > MAX_SQL_LENGTH:
        raise InvalidSqlError(f"The query is longer than {MAX_SQL_LENGTH} characters.")
    try:
        statements = [statement for statement in sqlglot.parse(text, dialect=DIALECT) if statement]
    except SqlglotError as error:
        raise InvalidSqlError(f"The query could not be parsed: {error}") from error
    if len(statements) != 1:
        raise ForbiddenSqlError("Exactly one SQL statement is allowed.")
    statement = statements[0]
    _check_nodes(statement)
    if not isinstance(statement, exp.Query):
        raise ForbiddenSqlError("Only SELECT queries are allowed.")

    _check_relations(statement)
    _check_columns(statement)
    _check_bounds(statement)

    try:
        qualified = qualify(
            statement,
            schema=dict(schema_mapping()),
            dialect=DIALECT,
            validate_qualify_columns=True,
            quote_identifiers=False,
        )
    except (OptimizeError, SqlglotError) as error:
        raise InvalidSqlError(str(error)) from error
    if not isinstance(qualified, exp.Query):
        raise InvalidSqlError("Only SELECT queries are allowed.")

    try:
        inference = UnitInference(qualified)
        check_local_money(inference)
        check_projections(inference)
        outputs = inference.outputs(qualified)
    except UnitError as error:
        raise InvalidSqlError(str(error)) from error

    percent = {name.lower() for name in percent_columns}
    columns = tuple(OutputColumn(name, _output_unit(unit, name, percent)) for name, unit in outputs)
    names = [column.name for column in columns]
    if "money_local" in {column.unit for column in columns} and "salary_currency" not in names:
        raise InvalidSqlError("Show salary_currency beside salary_local so amounts are labelled.")

    rewritten = _rewrite(qualified)
    own_limit = _literal_int(rewritten.args.get("limit"), "LIMIT")
    row_cap = None if own_limit is not None else MAX_ROWS
    parameterized, parameters = _parameterize(rewritten)
    capped = parameterized if row_cap is None else parameterized.limit(MAX_ROWS + 1, copy=True)
    counted = exp.select(exp.Count(this=exp.Star()).as_("total")).from_(
        exp.Subquery(this=parameterized, alias=exp.TableAlias(this=exp.to_identifier("result")))
    )
    return ValidatedSql(
        sql=_render(rewritten),
        executable=_render(_with_surface(capped)),
        count_sql=_render(_with_surface(counted)),
        columns=columns,
        parameters=parameters,
        row_cap=row_cap,
        tree=rewritten,
    )
