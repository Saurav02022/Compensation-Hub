"""Unit inference for validated SQL, which is where the money rules are enforced.

Every expression is traced back through CTEs, subqueries, and correlated references to the
surface columns it is computed from. That decides how each result column is shown and rejects
calculations that would produce a wrong amount: combining local salaries paid in different
currencies, multiplying money by money, adding money to a headcount, or converting currencies
in SQL, which the application does with the seeded rates instead.
"""

from sqlglot import exp
from sqlglot.optimizer.scope import Scope, traverse_scope

from compensation_hub.ask_compensation.surface import RELATIONS, Unit

# Internal marker for numeric literals, which take the unit of whatever they are combined with.
LITERAL = "literal"
InferredUnit = Unit | str

COUNTING = (exp.Rank, exp.DenseRank, exp.RowNumber, exp.Ntile)
# Operations that would combine or transform local amounts across employees or currencies.
LOCAL_MONEY_BARRIERS = (
    exp.AggFunc,
    exp.Window,
    exp.Add,
    exp.Sub,
    exp.Mul,
    exp.Div,
    exp.Neg,
    exp.Round,
    exp.Abs,
    exp.Floor,
    exp.Ceil,
    exp.Greatest,
    exp.Least,
)
SAME_UNIT_FUNCTIONS = (
    exp.Sum,
    exp.Avg,
    exp.Min,
    exp.Max,
    exp.Stddev,
    exp.StddevPop,
    exp.StddevSamp,
    exp.Median,
    exp.Round,
    exp.Abs,
    exp.Floor,
    exp.Ceil,
    exp.Lag,
    exp.Lead,
    exp.FirstValue,
    exp.LastValue,
)
FIRST_ARGUMENT_FUNCTIONS = (exp.Coalesce, exp.Nullif, exp.Greatest, exp.Least)
TEXT_FUNCTIONS = (exp.Lower, exp.Upper)
LOCAL_MONEY_MESSAGE = (
    "salary_local is in each employee's own currency and cannot be aggregated or used in "
    "calculations; use salary_usd instead."
)
PREDICATES = (
    exp.EQ,
    exp.NEQ,
    exp.GT,
    exp.GTE,
    exp.LT,
    exp.LTE,
    exp.And,
    exp.Or,
    exp.Not,
    exp.Is,
    exp.In,
    exp.Like,
    exp.ILike,
    exp.Between,
    exp.Exists,
    exp.Boolean,
)


class UnitError(Exception):
    """An expression combines units in a way that does not describe a valid figure."""


def _describe(unit: InferredUnit) -> str:
    return {
        "money": "a USD amount",
        "money_local": "a local-currency amount",
        "count": "a count",
        "rate": "an exchange rate",
    }.get(unit, "a number")


class UnitInference:
    def __init__(self, tree: exp.Query) -> None:
        self._scopes = traverse_scope(tree)
        self._scope_of = {id(scope.expression): scope for scope in self._scopes}

    @property
    def scopes(self) -> list[Scope]:
        return self._scopes

    def outputs(self, tree: exp.Query) -> list[tuple[str, InferredUnit]]:
        scope = self._scope_of[id(tree)]
        return [(name, self._output(scope, name)) for name in tree.named_selects]

    def column(self, column: exp.Column, scope: Scope) -> InferredUnit:
        current: Scope | None = scope
        while current is not None:
            source = current.sources.get(column.table)
            if source is not None:
                if isinstance(source, exp.Table):
                    relation = RELATIONS.get(source.name)
                    spec = relation.column(column.name) if relation else None
                    return spec.unit if spec else "number"
                return self._output(source, column.name)
            current = current.parent
        return "number"

    def _output(self, scope: Scope, name: str) -> InferredUnit:
        query = scope.expression
        if isinstance(query, exp.SetOperation):
            # The first branch names and types the columns of a UNION, INTERSECT, or EXCEPT.
            return self._output(scope.set_operation_scopes[0], name)
        if not isinstance(query, exp.Query):
            return "number"
        for projection in query.selects:
            if projection.alias_or_name == name:
                return self.expression(projection.unalias(), scope)
        return "number"

    def expression(self, node: exp.Expr, scope: Scope) -> InferredUnit:
        if isinstance(node, (exp.Paren, exp.Alias)):
            return self.expression(node.this, scope)
        if isinstance(node, exp.Column):
            return self.column(node, scope)
        if isinstance(node, exp.Literal):
            return "text" if node.is_string else LITERAL
        if isinstance(node, exp.Null):
            return LITERAL
        if isinstance(node, exp.Subquery):
            inner = self._scope_of.get(id(node.this))
            if inner is None or not isinstance(inner.expression, exp.Query):
                return "number"
            names = inner.expression.named_selects
            return self._output(inner, names[0]) if names else "number"
        if isinstance(node, exp.Filter):
            return self.expression(node.this, scope)
        if isinstance(node, exp.WithinGroup):
            ordered = node.expression.expressions[0]
            return self.expression(ordered.this, scope)
        if isinstance(node, exp.Window):
            return self._no_local_money(self.expression(node.this, scope))
        if isinstance(node, (exp.Count, *COUNTING)):
            return "count"
        if isinstance(node, (exp.PercentileCont, exp.PercentileDisc)):
            return "number"
        if isinstance(node, exp.Avg):
            unit = self._no_local_money(self.expression(node.this, scope))
            return "number" if unit == "count" else unit
        if isinstance(node, SAME_UNIT_FUNCTIONS):
            return self._no_local_money(self.expression(node.this, scope))
        if isinstance(node, FIRST_ARGUMENT_FUNCTIONS):
            units = [self.expression(arg, scope) for arg in [node.this, *node.expressions]]
            return next((unit for unit in units if unit != LITERAL), LITERAL)
        if isinstance(node, exp.Cast):
            return (
                "text"
                if node.to.is_type(*exp.DataType.TEXT_TYPES)
                else self.expression(node.this, scope)
            )
        if isinstance(node, exp.Case):
            return self._case(node, scope)
        if isinstance(node, exp.Neg):
            return self.expression(node.this, scope)
        if isinstance(node, (exp.Add, exp.Sub, exp.Mul, exp.Div)):
            return self._arithmetic(node, scope)
        if isinstance(node, (*TEXT_FUNCTIONS, *PREDICATES)):
            return "text"
        return "number"

    @staticmethod
    def _no_local_money(unit: InferredUnit) -> InferredUnit:
        # Column references are checked by check_local_money; this also covers local amounts
        # that reach an aggregate or calculation through a scalar subquery or a CTE column.
        if unit == "money_local":
            raise UnitError(LOCAL_MONEY_MESSAGE)
        return unit

    def _case(self, node: exp.Case, scope: Scope) -> InferredUnit:
        branches = [branch.args["true"] for branch in node.args.get("ifs", [])]
        if node.args.get("default") is not None:
            branches.append(node.args["default"])
        units = {self.expression(branch, scope) for branch in branches} - {LITERAL}
        if not units:
            return LITERAL
        if len(units) == 1:
            return units.pop()
        if "text" in units:
            return "text"
        if units & {"money", "money_local", "rate"}:
            raise UnitError("A CASE expression mixes amounts with other kinds of values.")
        return "number"

    def _arithmetic(self, node: exp.Binary, scope: Scope) -> InferredUnit:
        left = self._no_local_money(self.expression(node.this, scope))
        right = self._no_local_money(self.expression(node.expression, scope))
        if "rate" in (left, right):
            if "money" in (left, right):
                raise UnitError(
                    "Amounts must stay in USD in SQL; the answer currency is applied afterwards "
                    "with the seeded rates."
                )
            # Anything computed from a rate is still a rate, so a scaled or cross rate cannot
            # later be used to convert an amount.
            return "rate"
        if isinstance(node, (exp.Add, exp.Sub)):
            return _additive(left, right)
        if isinstance(node, exp.Mul):
            return _multiplicative(left, right)
        if isinstance(node, exp.Div):
            return _division(left, right)
        return "number"


def _additive(left: InferredUnit, right: InferredUnit) -> InferredUnit:
    if left == LITERAL:
        return right
    if right == LITERAL or left == right:
        return left
    if "money" in (left, right):
        raise UnitError(f"Cannot add or subtract {_describe(left)} and {_describe(right)}.")
    return "number"


def _multiplicative(left: InferredUnit, right: InferredUnit) -> InferredUnit:
    if left == "money" and right == "money":
        raise UnitError("Multiplying two amounts of money does not give an amount.")
    if "money" in (left, right):
        return "money"
    if left == LITERAL and right == LITERAL:
        return LITERAL
    return "number"


def _division(left: InferredUnit, right: InferredUnit) -> InferredUnit:
    if left == "money" and right == "money":
        return "number"
    if left == "money":
        return "money"
    if right == "money":
        raise UnitError(f"Dividing {_describe(left)} by a USD amount does not give a figure.")
    if left == LITERAL and right == LITERAL:
        return LITERAL
    return "number"


def check_local_money(inference: UnitInference) -> None:
    """Reject any calculation over local salaries, which are in different currencies."""
    for scope in inference.scopes:
        for column in scope.columns:
            if inference.column(column, scope) != "money_local":
                continue
            parent = column.parent
            while parent is not None and not isinstance(parent, (exp.Select, exp.SetOperation)):
                if isinstance(parent, LOCAL_MONEY_BARRIERS):
                    raise UnitError(LOCAL_MONEY_MESSAGE)
                parent = parent.parent


def check_projections(inference: UnitInference) -> None:
    """Infer every projection in every scope so that invalid money arithmetic is rejected."""
    for scope in inference.scopes:
        query = scope.expression
        if isinstance(query, exp.Select):
            for projection in query.selects:
                inference.expression(projection.unalias(), scope)
