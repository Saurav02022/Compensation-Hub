# Compensation Hub — AI Usage

This document defines how AI is used in Compensation Hub and how AI-assisted development is handled.

## Product AI

### Ask Compensation

Ask Compensation provides a natural-language interface over the product's existing analytics capabilities.

Its responsibility is limited to interpreting a user's question and converting it into a supported, structured analytics request.

The flow is:

```text
HR question
    |
    v
LLM
    |
    v
Structured Query Plan
    |
    v
Validation
    |
    v
Analytics Service
    |
    v
PostgreSQL
    |
    v
Result
```

The LLM is not the source of truth for compensation data.

It does not:

- receive database credentials,
- generate or execute arbitrary SQL,
- update employee or compensation data,
- calculate authoritative compensation values,
- make salary recommendations,
- decide who should receive a raise.

All calculations are performed by deterministic application and database logic.

If a question cannot be represented by the supported analytics model, the product returns a clear unsupported response rather than guessing.

### Structured Output

The model returns a constrained query plan containing only supported concepts such as:

- metric,
- filters,
- grouping,
- sorting,
- result limit.

The backend validates the plan before execution.

Invalid or unsupported output is rejected before it reaches the analytics layer.

### Reliability

Ask Compensation is an optional product capability.

If the LLM provider is unavailable:

- employee search still works,
- compensation management still works,
- dashboard analytics still work,
- Ask Compensation reports that the feature is unavailable.

The product must never fall back to invented compensation results.

### Testing

Automated tests do not depend on live LLM calls.

The LLM boundary is mocked so tests can verify:

- valid query plans,
- invalid query plans,
- unsupported questions,
- filtering and grouping behavior,
- attempts to use AI for write operations.

A small set of live-model evaluation cases may be run separately to verify that representative natural-language questions map to the expected structured requests.

## AI-Assisted Development

AI is used as a development tool for planning, implementation, testing, refactoring, and review.

The engineer remains responsible for:

- product decisions,
- architecture,
- code review,
- correctness,
- security,
- testing,
- accepting or rejecting generated suggestions.

Generated code or recommendations are not treated as correct until they are reviewed and verified with the relevant checks.

AI should not introduce a new product requirement or architectural dependency without an explicit decision being recorded first.

## Development Record

Only meaningful AI-assisted work needs to be recorded. The purpose is to capture engineering judgment, not every prompt.

Use the following format when adding an entry:

```text
Date:
Tool:
Task:
How AI was used:
What was accepted:
What was changed or rejected:
How it was verified:
```

Examples of work worth recording include:

- product or architecture exploration,
- non-trivial implementation,
- test generation or review,
- debugging,
- refactoring,
- AI feature design,
- security or correctness review.

Routine commands, formatting, Git operations, and minor text edits do not need individual entries.

## Working Principle

AI can accelerate the work, but it does not replace ownership.

> AI interprets intent. Application code enforces rules. PostgreSQL provides authoritative data.
