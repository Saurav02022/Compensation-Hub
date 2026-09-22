"""Boundary between Ask Compensation and the LLM provider.

A planner receives a natural-language question plus the vocabulary of supported dimension
values and returns the model's raw JSON text. It never sees database credentials, employee
records, or salaries, and it cannot execute anything: the service validates the text against
the constrained query-plan schema before any analytics run.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from compensation_hub.core.config import Settings


@dataclass(frozen=True)
class PlannerContext:
    countries: Sequence[str]
    departments: Sequence[str]
    job_titles: Sequence[str]


class PlannerUnavailableError(Exception):
    """The provider could not be reached or is not configured."""


class QueryPlanner(Protocol):
    def plan(self, question: str, context: PlannerContext) -> str:
        """Return the provider's raw response text for the question."""
        ...


class UnconfiguredQueryPlanner:
    """Planner used when no provider is configured; the feature reports itself unavailable."""

    def plan(self, question: str, context: PlannerContext) -> str:
        raise PlannerUnavailableError("No LLM provider is configured")


def build_query_planner(settings: Settings) -> QueryPlanner:
    return UnconfiguredQueryPlanner()
