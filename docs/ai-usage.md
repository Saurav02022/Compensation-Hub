# Compensation Hub — AI Usage

This document defines how AI is used in Compensation Hub and how AI-assisted development is handled.

## Product AI

### Ask Compensation

Ask Compensation provides a natural-language interface over the employee and compensation data Compensation Hub stores.

If the stored data can answer a question, Ask Compensation derives the answer from that data. If it cannot, Ask Compensation names the data that is missing instead of guessing.

The model's responsibility is limited to interpreting the question, together with any earlier questions it follows up, and writing a candidate read-only SQL query over the approved data, or reporting that the question needs data that is not stored or is not a question about the data.

The flow is:

```text
HR question
    |
    v
LLM
    |
    v
Candidate read-only SQL
    |
    v
Parsing and validation of the syntax tree
    |
    v
Read-only execution of the SQL rebuilt from the validated tree
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
- execute SQL, or have its SQL run without validation,
- update employee or compensation data,
- calculate authoritative compensation values,
- write the answer text,
- make salary recommendations,
- decide who should receive a raise,
- infer attributes that are not stored, such as gender from a name.

All calculations are performed by PostgreSQL and deterministic application logic, and answers are composed by application code.

### Structured Output

The model returns one of three responses:

- a query: one SELECT over the approved `employees` and `fx_rates` relations, the answer currency, a one-sentence reading of what the query computes, which result columns are percentages, and which column holds the headline figure,
- a missing-data response naming the data the question needs,
- an unsupported response for requests that are not factual questions about the data; the product answers these with fixed wording rather than the model's reason.

The backend parses every query, accepts only allowlisted read-only constructs and functions within size limits, enforces the money rules, and executes SQL rebuilt from the validated syntax tree in a read-only transaction. A rejected response gets one correction attempt; a write or out-of-surface request gets none.

Invalid or unsafe output is rejected before any data is read.

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

The SQL validator is tested on parsed queries, and validated SQL is run against PostgreSQL with expected results computed independently from the seed data. The LLM boundary is mocked so tests can also verify:

- valid, malformed, and unsafe SQL and planner responses,
- the correction attempt,
- missing-data and unsupported responses,
- follow-up context and its bounds,
- attempts to use AI for write operations, system catalog access, or SQL injection.

A small set of live-model evaluation cases may be run separately to check that varied natural-language questions, follow-ups, questions needing absent data, and adversarial requests map to the expected results. They evaluate interpretation; they do not define which questions are supported.

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
Date: 2026-09-24
Tool: Claude Code
Task: Data-grounded Ask Compensation
How AI was used: Researched structured output, SQL parsers, and PostgreSQL
  read-only and aggregate semantics; compared a fixed intent catalogue, RAG, a
  custom query representation, unrestricted text-to-SQL, and controlled SQL;
  built the approved data surface, the sqlglot-based validator, unit inference
  for money rules, read-only execution, the correction attempt, conversation
  context, generic result rendering, the tests, and the live evaluation.
What was accepted: Controlled read-only SQL over two approved relations defined
  as CTEs (D019); allowlisted syntax, relations, columns, and functions with size
  bounds; money rules enforced by tracing columns to the surface; exact medians,
  exact division, and bound literals as deterministic rewrites; execution in a
  READ ONLY transaction with a statement timeout; follow-up context carried as
  earlier SQL, never results (D020); sqlglot (MIT) over pglast (GPL-3.0).
What was changed or rejected: A custom query representation was built and
  tested first, then replaced because it rejected answerable questions (OR
  conditions, group-relative comparisons, per-group rankings) that SQL expresses
  directly. A dedicated database role was rejected for needing CREATEROLE in
  every environment. The model at first wrote correlated subqueries that took
  18-40 seconds on 10,000 employees; sqlglot's subquery unnesting produced invalid
  SQL under GROUP BY, so the prompt now steers to window functions or grouped
  CTEs (about 11 ms) and a timeout earns one correction. Missing-data responses
  were rejected at first because schema-guided output adds keys; responses that
  carry no SQL now ignore extra keys. A timeout test caught the context queries
  sharing the planned-query timeout, which now has its own.
  A final review then found that rate arithmetic could launder a currency
  conversion past the money rules (rate * 1, rate / rate), that local salaries
  could reach an aggregate through a scalar subquery, that dynamic-SQL and
  session functions such as query_to_xml and version() were offered a
  correction instead of being refused, that a missing privilege or table was
  retried as a planner mistake, that declined answers showed the model's own
  wording, and that a model LIMIT equal to the row cap hid the total; each was
  fixed with regression tests, and unused text functions were removed.
How it was verified: 276 backend tests (122 validator cases on parsed SQL, 23
  execution cases against PostgreSQL, 37 API cases), ruff, and mypy; 70
  frontend tests, eslint, tsc, and next build, all repeated from a fresh clone;
  the live evaluation passed 35 of 35 on four runs, then 44 of 44 on two runs
  after it was extended, at the low thinking level, which was kept after medium
  scored 34 of 35 and ran 45% slower; representative query shapes ran in 1-19
  ms on 10,000 employees; questions written after implementation, follow-ups,
  topic resets, missing-data, write, and injection requests were exercised
  through the UI and API with twenty figures checked by independent SQL; salary
  edits were reflected in answers and restored; the provider-unavailable
  response was checked with no key.
```

## Working Principle

AI can accelerate the work, but it does not replace ownership.

> AI interprets intent. Application code enforces rules. PostgreSQL provides authoritative data.
