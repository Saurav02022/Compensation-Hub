"""Boundary between Ask Compensation and the LLM provider.

A planner receives a natural-language question plus the vocabulary of supported dimension
values and returns the model's raw JSON text. It never sees database credentials, employee
records, or salaries, and it cannot execute anything: the service validates the text against
the constrained query-plan schema before any analytics run.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx
from google import genai
from google.genai import errors, types

from compensation_hub.core.config import Settings

logger = logging.getLogger(__name__)


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


# A deliberately flat schema in the JSON Schema subset the Gemini API accepts. It only guides
# generation; the service re-validates every response against the strict Pydantic schema.
PLANNER_RESPONSE_JSON_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["plan", "unsupported"]},
        "plan": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "enum": ["employee_count", "average_salary", "total_payroll"],
                },
                "filters": {
                    "type": "object",
                    "properties": {
                        "country": {"type": "string", "nullable": True},
                        "department": {"type": "string", "nullable": True},
                        "job_title": {"type": "string", "nullable": True},
                    },
                },
                "group_by": {
                    "type": "string",
                    "enum": ["country", "department", "job_title"],
                    "nullable": True,
                },
                "sort": {"type": "string", "enum": ["asc", "desc"], "nullable": True},
                "limit": {"type": "integer", "nullable": True},
            },
            "required": ["metric"],
            "nullable": True,
        },
        "reason": {"type": "string", "nullable": True},
    },
    "required": ["status"],
}


def build_system_instruction(context: PlannerContext) -> str:
    def listing(values: Sequence[str]) -> str:
        return ", ".join(f'"{value}"' for value in values)

    lines = [
        "You translate an HR manager's compensation question into one JSON request for a fixed",
        "analytics service. You do not answer the question yourself and you never invent numbers.",
        "",
        "Respond with JSON only, matching one of two shapes:",
        '1. {"status": "plan", "plan": {...}} when the question maps onto the supported analytics.',
        '2. {"status": "unsupported", "reason": "<short reason>"} when it does not.',
        "",
        "A plan has these fields:",
        '- "metric": exactly one of "employee_count" (headcount), "average_salary" (average',
        '  annual salary), "total_payroll" (sum of annual salaries). Compensation, pay, salary,',
        '  and payroll questions about averages use "average_salary"; totals use "total_payroll".',
        '- "filters": optional exact-match filters. Use only these values, copied exactly:',
        f'  - "country": one of {listing(context.countries)}',
        f'  - "department": one of {listing(context.departments)}',
        f'  - "job_title": one of {listing(context.job_titles)}',
        '  Map casual names to the exact value (for example "engineers" means department',
        '  "Engineering", "the UK" means country "United Kingdom"). Omit a filter you do not',
        "  need. Never set a filter to a value outside these lists; if the question names a",
        '  country, department, or job title that is not listed, respond with "unsupported".',
        '- "group_by": "country", "department", or "job_title" when the question asks for a',
        '  breakdown ("by department", "per country", "which countries"); otherwise null.',
        '- "sort": "desc" for highest/largest/top first, "asc" for lowest/smallest first,',
        '  otherwise null. Only meaningful with "group_by".',
        '- "limit": the number of groups requested ("top 3", "five largest"), otherwise null.',
        "",
        'Respond with "unsupported" for anything the analytics cannot answer reliably, including:',
        "individual employees, salary history or changes over time, medians, minimums, maximums,",
        "percentiles, bonuses, benefits, taxes, budgets, headcount planning, recommendations about",
        "who should get a raise or how much to pay, comparisons that need data outside these",
        "metrics, and questions unrelated to compensation.",
    ]
    return "\n".join(lines)


class GeminiQueryPlanner:
    """Plans questions with the Gemini API through the official google-genai SDK."""

    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
        )
        self._model = model

    def plan(self, question: str, context: PlannerContext) -> str:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=question,
                config=types.GenerateContentConfig(
                    system_instruction=build_system_instruction(context),
                    temperature=0,
                    response_mime_type="application/json",
                    response_json_schema=PLANNER_RESPONSE_JSON_SCHEMA,
                    max_output_tokens=512,
                ),
            )
        except errors.APIError as error:
            logger.warning("Gemini request failed with status %s: %s", error.code, error.message)
            raise PlannerUnavailableError(
                f"Gemini request failed with status {error.code}"
            ) from error
        except httpx.HTTPError as error:
            logger.warning("Gemini request failed: %s", error)
            raise PlannerUnavailableError("Gemini could not be reached") from error

        text = response.text
        if not text:
            raise PlannerUnavailableError("Gemini returned an empty response")
        return text


def build_query_planner(settings: Settings) -> QueryPlanner:
    if settings.gemini_api_key is None:
        return UnconfiguredQueryPlanner()
    return GeminiQueryPlanner(
        api_key=settings.gemini_api_key.get_secret_value(),
        model=settings.gemini_model,
        timeout_seconds=settings.gemini_timeout_seconds,
    )
