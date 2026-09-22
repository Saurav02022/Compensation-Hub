# Compensation Hub — Agent Instructions

This file defines how coding agents must work in this repository.

The goal is not to produce the most code. The goal is to make small, correct, explainable engineering changes that stay aligned with the product requirements, recorded decisions, and system architecture.

## 1. Source of Truth

Before changing product behavior or architecture, read:

- `docs/requirements.md` — what the MVP must do
- `docs/decisions.md` — accepted product and engineering decisions
- `docs/architecture.md` — system structure and responsibility boundaries
- `docs/ai-usage.md` — product-AI boundaries and AI-assisted development rules
- `docs/project-plan.md` — execution order and current progress
- `README.md` — developer-facing setup and usage once finalized

When documents conflict, use this priority:

1. `docs/requirements.md`
2. `docs/decisions.md`
3. `docs/architecture.md`
4. verified tests and current implementation

Do not silently invent a business rule.

If a task requires a material product decision that is not covered by the documents, stop and ask before implementing it.

For small reversible implementation details, follow existing repository conventions and keep the choice simple.

## 2. How an Agent Should Work

For every non-trivial task, follow this sequence.

### Understand

1. Read the task carefully.
2. Read the relevant project documents.
3. Inspect the existing implementation before proposing changes.
4. Identify the smallest complete outcome required by the task.
5. Identify affected tests, configuration, migrations, documentation, and public API contracts.

Do not start coding from the prompt alone.

### Verify Current Reality

Do not rely on remembered framework or library behavior when it may be version-sensitive.

Before using an API or configuration option:

1. inspect the versions in `frontend/package.json`, `backend/pyproject.toml`, and lock files,
2. inspect existing code and local type definitions,
3. consult current official documentation when behavior is version-specific or uncertain.

Prefer primary documentation for:

- Next.js,
- React,
- TypeScript,
- FastAPI,
- Pydantic,
- SQLAlchemy,
- Alembic,
- PostgreSQL,
- the selected LLM provider.

Do not copy patterns from old tutorials when they conflict with the installed version.

If current official documentation cannot be checked and correctness depends on it, state the uncertainty instead of guessing.

### Plan

Before editing, form a short implementation plan:

- files that need to change,
- behavior being added or changed,
- tests required,
- failure cases,
- verification commands.

Do not create new layers, abstractions, folders, or dependencies unless the task needs them.

### Implement

- Work in the smallest useful vertical slice.
- Keep changes focused on the current phase in `docs/project-plan.md`.
- Follow existing naming and module boundaries.
- Keep business rules in the backend, not in route handlers or React components.
- Keep external integrations behind small interfaces.
- Preserve backward compatibility unless the task explicitly changes a contract.
- Do not refactor unrelated code while implementing a feature.

### Verify

Run the checks relevant to the files changed.

Do not say something works unless it was actually verified.

At minimum, consider:

- unit tests,
- integration tests,
- frontend tests,
- lint,
- formatting,
- type checks,
- production build,
- migration checks,
- manual smoke verification when appropriate.

Review the final diff before committing.

### Finish

A task is complete only when:

- behavior matches the documented requirement,
- relevant tests pass,
- expected failure states are handled,
- lint/type/build checks pass where applicable,
- documentation is updated if behavior or a decision changed,
- `docs/project-plan.md` is updated only after verification,
- no unrelated changes are included.

## 3. Product Boundaries

Compensation Hub is an MVP for a single trusted HR Manager managing compensation for 10,000 employees across multiple countries.

Do not add the following unless the project documents are intentionally updated first:

- authentication or RBAC,
- salary history,
- employee onboarding/offboarding,
- payroll processing,
- compensation approval workflows,
- bonuses, benefits, equity, or tax calculations,
- live FX synchronization,
- salary recommendations,
- arbitrary text-to-SQL,
- RAG or vector search,
- microservices,
- Kubernetes.

Do not describe the repository, UI, code, commits, or documentation as an assignment, take-home exercise, coding challenge, or evaluator demo.

Do not invent customers, production usage, business history, metrics, or operational claims.

## 4. Repository Structure

Keep the root intentionally small.

```text
Compensation-Hub/
├── frontend/
├── backend/
├── docs/
│   ├── requirements.md
│   ├── decisions.md
│   ├── architecture.md
│   ├── ai-usage.md
│   └── project-plan.md
├── README.md
├── AGENTS.md
├── CLAUDE.md
├── .gitignore
└── .gitattributes
```

Additional root files such as `.env.example`, Docker configuration, or CI configuration should be added only when the relevant project phase requires them.

Do not create generic root folders such as `shared`, `common`, `utils`, `services`, `infra`, or `scripts` without a concrete use case.

## 5. Frontend Structure

The frontend uses the Next.js App Router, React, and TypeScript.

Target structure:

```text
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   └── ...route segments as product screens are added
├── components/
│   ├── ui/
│   ├── employees/
│   ├── compensation/
│   ├── analytics/
│   └── ask-compensation/
├── lib/
│   ├── api/
│   ├── formatting/
│   └── validation/
├── hooks/
├── types/
├── public/
├── package.json
└── tsconfig.json
```

Do not create empty folders ahead of need. Add a folder when its first real file is introduced.

### Frontend responsibilities

The frontend owns:

- rendering,
- user interactions,
- form state,
- loading/empty/error states,
- calling backend APIs,
- presentation formatting.

The frontend must not:

- access PostgreSQL directly,
- duplicate compensation business rules,
- perform authoritative compensation calculations,
- contain LLM provider credentials,
- make direct LLM calls from the browser.

### Frontend coding practices

- Keep TypeScript strict.
- Prefer explicit types at API boundaries.
- Keep page and route components small.
- Extract components when they have a clear responsibility or reuse.
- Avoid large generic `utils.ts` or `helpers.ts` files.
- Keep server-state logic separate from presentational components.
- Do not mirror backend validation unless the UI needs immediate user feedback; backend validation remains authoritative.
- Prefer accessible HTML and predictable UI behavior over visual complexity.
- Test user-visible behavior, not component internals.

## 6. Backend Structure

The backend uses Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic, and Psycopg.

Target structure:

```text
backend/
├── src/
│   └── compensation_hub/
│       ├── main.py
│       ├── core/
│       │   └── config.py
│       ├── db/
│       │   ├── session.py
│       │   └── models/
│       │       ├── employee.py
│       │       ├── compensation.py
│       │       └── fx_rate.py
│       ├── employees/
│       │   ├── router.py
│       │   ├── schemas.py
│       │   └── service.py
│       ├── compensation/
│       │   ├── router.py
│       │   ├── schemas.py
│       │   └── service.py
│       ├── analytics/
│       │   ├── router.py
│       │   ├── schemas.py
│       │   └── service.py
│       └── ask_compensation/
│           ├── router.py
│           ├── schemas.py
│           ├── service.py
│           └── provider.py
├── tests/
├── alembic/
├── alembic.ini
├── pyproject.toml
└── uv.lock
```

This is the intended direction, not a requirement to create every file immediately.

Only create modules required by the current implementation phase.

If a module becomes large, split it by responsibility. Do not pre-emptively create repository, domain, command, handler, factory, or interface layers without a real need.

### Backend responsibilities

The backend owns:

- validation,
- business rules,
- employee and compensation operations,
- currency normalization,
- analytics,
- database access,
- AI orchestration.

### Backend coding practices

- Use type hints for application code.
- Use `Decimal` and fixed-precision database numeric types for money.
- Never use binary floating point for stored compensation values or authoritative monetary calculations.
- Keep FastAPI route handlers thin.
- Validate external input with Pydantic.
- Keep database access explicit and testable.
- Prefer clear SQLAlchemy queries over unnecessary generic repository abstractions.
- Use Alembic for every schema change.
- Do not use global mutable application state.
- Keep provider-specific AI code isolated from business logic.
- Convert expected domain failures into controlled API responses.

## 7. Database Rules

PostgreSQL is the source of truth.

The MVP data model contains:

- Employee,
- Compensation,
- FX Rate.

Rules:

- employee code must be unique,
- each employee has one current compensation record,
- monetary values use fixed precision,
- currency codes are explicit,
- seeded FX rates are deterministic,
- normalized salary is calculated when needed rather than persisted as duplicated salary data.

Use database constraints for invariants that the database can enforce reliably.

Use server-side pagination and database-side filtering.

Run aggregations in PostgreSQL rather than loading all employees into Python.

Add indexes for demonstrated access patterns, not by guessing.

Before adding an index, know which query it supports.

Migration files should be small, understandable, and reversible where practical.

Never edit a migration that has already been treated as applied/shared; create a new migration.

## 8. AI Product Boundary

Ask Compensation is read-only.

The LLM may:

- interpret a natural-language question,
- return a constrained structured analytics request.

The LLM must not:

- receive database credentials,
- generate or execute arbitrary SQL,
- update employee or compensation data,
- calculate authoritative compensation values,
- make salary recommendations,
- decide who should receive a raise.

Validate all model output before using it.

All authoritative compensation results come from application logic and PostgreSQL.

The AI feature must fail independently. If the LLM provider is unavailable, employee search, compensation management, and deterministic analytics must continue to work.

Do not send the complete employee dataset to the model.

Mock the LLM boundary in normal automated tests. Keep live-model evaluation separate from CI.

## 9. No Assumption Rule

Do not guess when a missing answer can materially change:

- product behavior,
- data semantics,
- security,
- money calculations,
- API contracts,
- database schema,
- architecture.

First check:

1. requirements,
2. decisions,
3. architecture,
4. existing code,
5. tests,
6. current official technical documentation.

If the answer is still unclear, stop and ask.

Do not hide an assumption inside implementation code.

If a deliberate assumption is accepted, record it in the appropriate project document before relying on it broadly.

## 10. Comments and Documentation

Code should be understandable primarily through naming and structure.

Add comments when they explain:

- why a non-obvious decision exists,
- a business invariant,
- a subtle edge case,
- a workaround with an external dependency,
- a safety or correctness constraint.

Do not add comments that merely restate the code.

Avoid comments such as:

```text
# Loop through employees
# Call the service
# Return the response
```

Do not add decorative comments, tutorial-style explanations, generated summaries, or comments aimed at proving that code was written carefully.

Use docstrings where they add useful contract or behavior information. Do not add a docstring to every private function automatically.

Remove stale comments when behavior changes.

## 11. AI Footprint and Repository Hygiene

Do not add AI-generated meta-content to source files.

Do not include phrases such as:

- "Generated by Claude"
- "Generated by ChatGPT"
- "AI-generated"
- "As requested by the prompt"
- "For the assessment"
- "The evaluator expects"

Do not add AI tool signatures, generated-by comments, or automatic co-author trailers unless explicitly requested.

Do not leave prompt text, scratch notes, analysis files, temporary plans, or agent conversation logs in the repository.

Meaningful AI-assisted engineering work belongs only in the concise development record defined by `docs/ai-usage.md`.

Do not hide or misrepresent AI use. The goal is a clean product repository, while `docs/ai-usage.md` records meaningful AI involvement transparently.

## 12. Dependencies

Before adding a dependency:

1. identify the concrete problem it solves,
2. check whether the existing stack already solves it,
3. verify compatibility with installed versions,
4. prefer a small, maintained dependency,
5. avoid adding a framework for one trivial helper.

Do not add technology simply because it appears in a job description or is commonly used in similar systems.

Update lock files through the package manager; do not edit them manually.

Use:

- `npm` for frontend dependencies,
- `uv` for backend dependencies.

## 13. Testing

Tests should be fast, deterministic, and easy to understand.

Use the appropriate level:

- unit tests for business rules and validation,
- integration tests for PostgreSQL and API behavior,
- frontend tests for important user workflows,
- mocked LLM tests for structured-query behavior,
- optional live-model evaluations outside CI.

Important rules:

- test behavior, not implementation details,
- include expected failure paths,
- do not call live external services from normal tests,
- do not use random test data without a fixed seed,
- avoid tests that depend on execution order,
- do not weaken assertions just to make a failing test pass.

A regression fix should include a regression test when practical.

## 14. Error Handling

Expected failures should be explicit.

Examples:

- employee not found,
- invalid salary,
- unsupported currency,
- missing FX rate,
- invalid AI query plan,
- unsupported compensation question,
- unavailable LLM provider.

Do not catch broad exceptions simply to return success-like behavior.

Do not expose stack traces, secrets, or internal credentials in API responses.

Log enough context to diagnose failures without logging sensitive data unnecessarily.

## 15. Performance

The expected dataset is 10,000 employees.

Use simple database-backed solutions first:

- server-side pagination,
- database filtering,
- database aggregation,
- bounded page sizes,
- justified indexes.

Do not introduce:

- Redis,
- Elasticsearch,
- Kafka,
- background workers,
- caches,
- additional databases,

without measured or documented need.

Optimize based on query behavior and evidence, not assumptions.

## 16. Security and Secrets

Never commit:

- API keys,
- database passwords,
- tokens,
- `.env` files containing secrets.

Use environment variables for runtime configuration.

Keep `.env.example` free of real credentials.

Do not expose server-only configuration through `NEXT_PUBLIC_*`.

Validate external input at trust boundaries.

Do not log sensitive compensation data unnecessarily.

## 17. Git and Change Discipline

Keep commits small and focused.

Prefer messages such as:

- `feat: add employee data model`
- `feat: add paginated employee listing`
- `test: cover compensation validation`
- `docs: record currency decision`

Avoid:

- `done`
- `final`
- `fix stuff`
- `updates`
- `complete project`

Before committing:

1. review `git status`,
2. review the diff,
3. ensure generated files and secrets are not included,
4. run relevant verification,
5. stage only intended files.

Do not force push, amend shared commits, or rewrite history unless explicitly instructed.

## 18. Project Tracker

`docs/project-plan.md` is the execution tracker.

Only mark an item complete after the related work has been implemented and verified.

Do not mark future work complete based on intent or partial implementation.

Do not move to a later phase because it is more interesting if the current phase still has required work.

## 19. Final Review Checklist

Before declaring a task complete, confirm:

- Did I read the relevant project documents?
- Did I inspect the current implementation before changing it?
- Did I avoid assumptions that materially affect behavior?
- Did I use current framework/library behavior rather than stale memory?
- Is the change within the current project phase?
- Is the implementation simpler than the alternatives without sacrificing correctness?
- Are money calculations deterministic and precise?
- Are AI boundaries preserved?
- Are expected failure cases handled?
- Are relevant tests present and passing?
- Did I run the relevant lint, type-check, test, and build commands?
- Did I review the final diff?
- Does the repository contain no secrets, scratch files, or AI meta-content?
- Is the project tracker accurate?
