# Compensation Hub — AI Usage

This document defines how AI is used in Compensation Hub and how AI-assisted development is handled.

## Product AI

### Ask Compensation

Ask Compensation provides natural-language, read-only access to data Compensation Hub actually stores.

Its responsibility is to interpret an HR question and return a constrained structured plan. The application validates that plan, constructs the executable query with SQLAlchemy, and uses PostgreSQL plus deterministic application logic for the authoritative result.

The flow is:

```text
Current question
      +
prior validated plans
      |
      v
LLM
      |
      v
Structured read-only plan
      |
      v
Validation
      |
      v
SQLAlchemy / deterministic calculation
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
- generate SQL that is executed by the application,
- update employee or compensation data,
- calculate authoritative compensation values,
- receive the complete employee dataset,
- receive prior result rows or salary values as conversation memory,
- infer missing employee attributes,
- make salary recommendations,
- decide who should receive a raise.

All executable database operations are constructed by application code from validated plan fields.

If a question requires data the product does not store, the response identifies the missing data rather than guessing.

### Structured Output

The model returns a generic read-only query AST rather than SQL or a question-specific command.

The AST is built from application-owned primitives:

- approved stored or derived fields,
- validated predicates,
- projection and distinct selection,
- grouping and ordering,
- bounded result limits,
- count, distinct count, sum, average, minimum, maximum, and median,
- conditional aggregates,
- arithmetic expressions,
- FX conversion for USD-based monetary expressions.

The application validates the AST before SQLAlchemy constructs any database query. A generated response cannot represent an insert, update, delete, schema change, arbitrary SQL fragment, unrestricted database function, or unbounded result fetch.

Controlled-value filters and target currencies are checked against current database values before execution.

### Contextual Follow-ups

Ask Compensation can use up to six prior successful turns to interpret conversational references and refinements.

Only the prior user question and its already validated plan are sent back to the planner. Previous result rows and compensation values are not included.

The current question must always produce a complete new validated plan before it can execute.

### Why RAG Is Not Used

The product's source of truth is structured relational data.

Questions about employees, current compensation, aggregates, comparisons, and currency conversion require exact relational queries and deterministic calculations rather than semantic document retrieval.

RAG would become appropriate if Compensation Hub later added unstructured sources such as compensation policies, country guidelines, or HR documents.

### Reliability

Ask Compensation is an optional product capability.

If the LLM provider is unavailable:

- employee search still works,
- compensation management still works,
- deterministic analytics still work,
- Ask Compensation reports that the feature is unavailable.

The product never falls back to invented compensation results.

### Testing

Routine automated tests do not depend on live LLM calls.

The planner boundary is mocked so the suite can verify:

- valid and invalid query ASTs,
- contextual follow-up history,
- missing-data responses,
- generic filtering, projection, grouping, ordering, aggregation, conditional aggregation, arithmetic, and FX behavior,
- expression and result bounds,
- rejection of SQL-like or write-like model output,
- provider failure isolation.

A separate live-model evaluation suite covers representative supported, unsupported, and follow-up questions. It is intentionally excluded from routine CI and requires an explicit provider credential.

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

### Entries

```text
Date: 2026-09-22
Tool: Claude Code
Task: Phase 1 — database foundation and deterministic seed data
How AI was used: Implemented runtime settings, SQLAlchemy models, the Alembic
  initial migration, the deterministic 10,000-employee dataset generator, the seed
  command, and the PostgreSQL-backed test suite from the documented requirements
  and architecture.
What was accepted: One compensation row per employee enforced by primary key;
  positive salary and rate check constraints; a foreign key from compensation
  currency to the seeded FX rates so every stored salary can be normalized; a
  dataset generator that draws only from Random.random() so output is stable
  across Python versions; a seed command that refuses to run on a populated
  database unless --reset is passed.
What was changed or rejected: Autogenerated migration was reformatted and
  reviewed by hand; helper generics were switched to PEP 695 syntax to satisfy
  the configured linter.
How it was verified: Migration upgraded, downgraded, and upgraded again against
  PostgreSQL 16 with no autogenerate drift; seed loaded 10,000 employees on a
  freshly created database; pytest (29 tests including integration tests),
  ruff check, ruff format --check, and mypy all pass.
```

```text
Date: 2026-09-22
Tool: Claude Code
Task: Phase 2 — employee directory and compensation management
How AI was used: Implemented the paginated, searchable, filterable employee API,
  the compensation update endpoint, and the Next.js directory, detail, and
  compensation edit screens with their loading, empty, error, and not-found
  states, plus backend API tests and frontend component tests.
What was accepted: Filtering, search, and pagination executed in PostgreSQL;
  salaries serialized as exact decimal strings; PATCH replacing both salary and
  currency with the currency validated against seeded FX rates; server-rendered
  pages with a GET filter form and a Server Action for the update so the API
  base URL stays server-only; a GET /employees/filter-options endpoint added to
  the documented API for the filter dropdowns.
What was changed or rejected: A test fixture that ran the FastAPI lifespan was
  pointing the API under test at the development database and was replaced;
  a form remount key that erased the success message after saving was removed;
  the Next.js dev server's generated agent rule files were disabled.
How it was verified: 64 backend tests, ruff, and mypy pass; 21 frontend tests,
  eslint, tsc, and next build pass; the directory, filters, pagination, detail,
  valid and invalid compensation updates, not-found, and API-down error states
  were exercised end to end in a browser against the seeded database.
```

```text
Date: 2026-09-22
Tool: Claude Code
Task: Phase 3 — compensation analytics and performance review
How AI was used: Implemented the analytics service and endpoints, the
  compensation overview page, correctness tests against expected values
  computed independently in Decimal arithmetic, and an EXPLAIN ANALYZE review
  of the directory and analytics queries on the 10,000-row dataset.
What was accepted: All aggregation in PostgreSQL over employees LEFT JOIN
  compensation LEFT JOIN fx_rates with salary * rate_to_usd in NUMERIC
  arithmetic; employees without compensation counted in headcount but excluded
  from payroll and average; a missing exchange rate raising a controlled
  error, proven by a test that temporarily lifts the foreign key; breakdown
  sorting and limits so Ask Compensation can reuse the same service; indexes
  on (full_name, employee_code), country, department, and job_title, which the
  plans showed cut the ordered directory page from 7-23 ms of sorting to under
  2 ms and turned filtered scans into index scans.
What was changed or rejected: No index was added for the search box, since a
  contains-match ILIKE cannot use a B-tree index and the full scan completes in
  about 12 ms at this scale; no caching or extra infrastructure was added.
How it was verified: 77 backend tests, ruff, and mypy pass; 29 frontend tests,
  eslint, tsc, and next build pass; the overview and filtered breakdowns were
  checked against the API and in the browser with the full seeded dataset;
  migration 0002 applied with no autogenerate drift.
```

```text
Date: 2026-09-22
Tool: Claude Code
Task: Phase 4 — Ask Compensation
How AI was used: Designed the constrained query-plan schema, the planner
  interface, the validation and execution service, the deterministic answer
  composition, the Gemini adapter and its system instruction, the Ask page,
  the mocked-planner tests, and the optional live evaluation set.
What was accepted: A flat query plan (metric, exact filters, group by, sort,
  limit) as the only model output that is ever executed; strict Pydantic
  validation with unknown non-null keys rejected; filter values checked against
  the real dimension values before execution; answers composed by application
  code from analytics results, never by the model; a 503 for provider outages
  with every other feature unaffected; the planner receives only the question
  and the dimension vocabulary; Gemini selected as the provider (D012).
What was changed or rejected: The first live run showed Gemini emitting
  "reason": null beside a plan because the response schema lists both
  properties, which the strict schema rejected; null-valued top-level keys are
  now dropped before validation, with regression tests, while non-null extras
  remain rejected. The provider adapter was written only after the provider
  decision was made explicitly rather than assumed.
How it was verified: 107 backend tests with the planner mocked, ruff, and mypy
  pass; 32 frontend tests, eslint, tsc, and next build pass; the 8-case live
  evaluation (5 supported questions mapped to the expected plans, 3 unsupported
  questions declined) passed on three consecutive runs; the Ask page was
  exercised in the browser against the seeded database with the real model,
  and a grouped answer matched the overview page figures.
```

```text
Date: 2026-09-22
Tool: Claude Code
Task: Phase 5 — quality checks and continuous integration
How AI was used: Wrote the GitHub Actions workflow, reviewed error handling,
  logging, and secret handling, added a controlled database-outage response,
  and ran the full quality suite from fresh clones and in CI.
What was accepted: Backend and frontend jobs with a PostgreSQL 16 service and
  no LLM credential; LOG_LEVEL-driven logging configured at startup; a 503
  without connection details when the database is unreachable while /health
  stays a liveness check; explicit byte-order collation on the employee text
  columns after CI on Linux sorted "Accountant" before "Account Executive"
  while Windows and Python sorted them the other way.
What was changed or rejected: The setup-uv action's README suggested a major
  tag that is not published, so the workflow pins a release tag; a test that
  tried to check query validation through a failing session factory was
  removed because FastAPI resolves the session dependency first; a fresh clone
  under the long scratchpad path hit the Windows path limit inside mypy and was
  repeated from a short path.
How it was verified: 109 backend tests, ruff, and mypy; 32 frontend tests,
  eslint, tsc, and next build; both suites from a fresh clone; CI green on
  GitHub Actions for both jobs.
```

```text
Date: 2026-09-22
Tool: Claude Code
Task: Phase 6 — container images and deployment to Google Cloud and Supabase
How AI was used: Wrote the backend and frontend Dockerfiles and the full-stack
  compose services, created the dedicated Google Cloud project with billing,
  APIs, Artifact Registry, Secret Manager, and least-privilege service accounts,
  created the Supabase project in Mumbai, migrated and seeded it, built the
  images with Cloud Build, deployed both Cloud Run services in asia-south1,
  and smoke-tested the deployed product.
What was accepted: Cloud Run in Mumbai plus Supabase in Mumbai as recorded in
  D013; Supabase reached through its IPv4 session-mode pooler because Cloud Run
  egress is IPv4 only; the database URL held only in Secret Manager and mounted
  into the API service; the Ask Compensation API key provisioned outside the
  repository and stored in Secret Manager.
What was changed or rejected: BuildKit cache mounts were removed from the
  backend image because Cloud Build's classic builder rejects them; the frontend
  ignore file needed recursive patterns so test files stayed out of the image;
  Supabase project creation initially failed because of an account billing
  issue, which was resolved before retrying.
How it was verified: Both images built by Cloud Build; migrations 0001-0003 and
  the 10,000-employee seed applied to Supabase with counts confirmed; deployed
  health, directory, filters, detail, salary update and revert, analytics, and
  the Ask page's unavailable state exercised in the browser against the live
  services; the deployed summary matches the local dataset figures.
```

```text
Date: 2026-09-22
Tool: Claude Code
Task: Phase 7 — final product review
How AI was used: Checked the implementation against every requirement, decision,
  and architecture boundary; finalized the README; reviewed the commit history
  and the development record; reran the full quality suite from a fresh clone;
  and, once Docker became available, ran the complete container stack from the
  documented compose commands.
What was accepted: All requirements and success criteria are covered by
  implemented, tested, and deployed behavior; D012 and D013 record the two
  decisions made during implementation; the commit history is a linear series
  of small conventional commits without tooling signatures.
What was changed or rejected: The container run found that a blank
  GEMINI_API_KEY, which the env example and compose environment both produce,
  was treated as a configured secret and crashed the API at startup; a blank
  value now means the provider is unconfigured, with a regression test, and the
  fix was redeployed to Cloud Run.
How it was verified: 111 backend tests, ruff, and mypy; 32 frontend tests,
  eslint, tsc, and next build; CI green on the final commit; the compose stack
  migrated, seeded, and served the directory, detail, analytics, and Ask pages;
  the redeployed backend answers health, analytics, and a live Ask question.
```

```text
Date: 2026-09-22
Tool: Claude Code
Task: Phase 8 — product design and UX refinement
How AI was used: Audited the implemented UI against the product workflows, set a
  restrained visual system (neutral canvas, one accent hue, shared radius and
  control height, a handful of primitives), and reworked the shell, directory,
  employee detail, analytics, overview, and Ask Compensation surfaces without
  changing the API, business rules, or architecture.
What was accepted: A sticky header with an active section marker; Ask
  Compensation as a global right-side drawer with focus trapping, Escape,
  suggested questions limited to supported capabilities, and a log that
  survives navigation, replacing the separate page; a directory toolbar that
  debounces search by 300 ms, applies filters immediately, resets to page one,
  and keeps all state in the URL through router transitions so the visible
  table never flashes; a range summary and filtered-empty state; an edit-on-
  request compensation panel; analytics led by KPI tiles, shared filters, and
  three horizontal bar charts sized from the breakdown endpoint with exact
  values behind disclosures and bar labels that filter the page; an overview
  built from the summary and two top-five breakdowns.
What was changed or rejected: No chart library was added; the three single-
  series bar charts are plain HTML lists, which keeps values as text, works
  without JavaScript, and avoids a dependency. Raw query plans are not shown;
  the drawer gives a one-line plain-language reading instead. The header
  overflowed at phone widths in review and now wraps its navigation.
How it was verified: 48 frontend tests, eslint, tsc, and next build; 112
  backend tests including a new search-plus-filter-plus-pagination case; a
  browser walkthrough against the seeded API confirmed the sticky header,
  active navigation, one API request for a fast-typed search, filters and
  pagination combining in the URL, salary edit, backend error, and revert,
  chart-to-filter links, the drawer answering a live question and closing on
  Escape, and no horizontal overflow at 375 px.
```

```text
Date: 2026-09-23
Tool: Claude Code
Task: Phase 9 — product design rebuild
How AI was used: Researched product UI from YC-backed companies (Rippling, Deel,
  Gusto, Brex, Plane, Pave, Retool, Vanta, Supabase, Airbyte, Front, PostHog,
  Mixpanel, Amplitude, Finch) through help centers, documentation, and product
  screenshots; synthesized the recurring patterns; audited the running product
  at four widths; rebuilt the shell, directory, detail, analytics, overview,
  and Ask Compensation surfaces; and reviewed the rendered result in a browser.
What was accepted: A sticky sidebar shell; Ask Compensation as a panel docked
  beside the page on wide screens (a modal sheet below 1280 px) with Ctrl/Cmd K,
  a conversation kept across navigation, answers shown as figures with a plain
  reading and a link to the same view in Analytics; compact filter controls over
  native selects; table columns that collapse by container width so the docked
  panel never squeezes the directory; one transition shared by filters, search,
  and pagination so results dim in place instead of flashing; analytics as a
  single breakdown workspace (dimension and measure in the URL, every measure
  beside its bar, click-to-drill); headline figures rounded with exact values on
  hover; Geist through next/font; salary edits with inline validation and a
  before/after preview.
What was changed or rejected: The Frame primitive first used overflow-hidden,
  which made it the scroll container, so the sticky table header covered the
  first row on narrow screens; it now uses overflow-clip. A share-of-total
  column, trend deltas, and a chart library were rejected because they would
  compute or imply figures the backend does not provide.
How it was verified: 66 frontend tests, eslint, tsc, and next build; 112
  backend tests, ruff, and mypy; a scripted browser journey covering search by
  name and code (one request per typed query), combined filters, pagination,
  reload and back/forward, a salary edit and revert, analytics drill-down, a
  live Ask question, an unsupported question, the panel across navigation,
  empty, out-of-range, and not-found states, and no horizontal overflow at
  375 px.
```

```text
Date: 2026-09-23
Tool: Claude Code
Task: Phase 9 — production redeploy of the rebuilt frontend
How AI was used: Built the frontend image for main with Cloud Build, deployed
  it to the existing Cloud Run web service, ran the production smoke test in a
  browser, and reviewed the Cloud Run request and error logs.
What was accepted: The backend was left on its running image because the only
  backend change since it was built is a test file, and no migration was added
  after 0003; the frontend kept its existing service account and API base URL.
What was changed or rejected: The API logs showed 132 employee-detail requests
  during a journey that opened a handful of employees. Production builds
  prefetch every visible directory row, and the detail page resolved
  generateMetadata during that prefetch, so each results page fetched up to 25
  employees; the per-employee page title was dropped, which a local production
  build confirmed reduces a directory view to the list and filter-option
  requests, and the fix was redeployed.
How it was verified: 66 frontend tests, eslint, tsc, and next build; CI green;
  the redesign visible in production at 1440 and 390 px; search by name and
  code, combined filters, pagination, reload and back/forward, a salary edit
  restored to its original value, analytics drill-down and measure switching,
  a live Ask question, an unsupported question, and the panel across
  navigation all passed; no warnings, errors, or non-200 responses in either
  service log after the deploy.
```

```text
Date: 2026-09-23
Tool: ChatGPT
Task: Phase 10 — data-grounded Ask Compensation
How AI was used: Reviewed the gap between the conversational UI and the original
  three-metric planner, then implemented a broader constrained read-only query
  model, bounded validated-plan history for follow-ups, deterministic execution,
  generalized result rendering, tests, documentation, and CI fixes.
What was accepted: Five explicit query kinds for aggregates, employees, distinct
  values, shares, and comparisons; minimum, maximum, and median salary; bounded
  employee ranking; deterministic target-currency conversion through seeded FX
  rates; up to six prior questions with their validated plans as follow-up
  context; SQLAlchemy-built queries only; specific missing-data explanations.
What was changed or rejected: RAG and a vector database were rejected because
  the source of truth is structured relational data, not documents. Arbitrary
  text-to-SQL was rejected because it would broaden the executable surface and
  weaken validation. Prior result rows and salary values were kept out of model
  conversation context. CI exposed formatting, URL-encoding, and UI assertion
  issues, which were corrected without weakening the intended behavior.
How it was verified: GitHub Actions passed ruff check, ruff format --check,
  mypy, and 110 backend tests against PostgreSQL with 10 live-model cases
  deselected; the frontend passed eslint, TypeScript checking, 67 Vitest tests,
  and the production Next.js build. The optional live-model evaluation was
  expanded for the new capabilities but was not run in routine CI.
```

## Working Principle

AI can accelerate the work, but it does not replace ownership.

> AI interprets intent. Application code enforces rules. PostgreSQL provides authoritative data.
