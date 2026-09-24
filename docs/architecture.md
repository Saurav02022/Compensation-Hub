# Compensation Hub — Architecture

## Overview

Compensation Hub is a modular web application with a Next.js frontend, a FastAPI backend, and PostgreSQL as the system of record.

The production request path is:

```text
Browser
   |
   | HTTPS
   v
Next.js / Cloud Run
   |
   | server-side REST / JSON
   v
FastAPI / Cloud Run
   |
   +----------------------+
   |                      |
   | SQL                  | structured planning request
   v                      v
Supabase PostgreSQL    Gemini API
```

The browser interacts with the Next.js application. Backend API access stays server-side in the frontend, including page data loading and Server Actions. The browser does not receive the backend base URL as public configuration and does not call PostgreSQL or the Gemini API directly.

The backend owns product rules, validation, compensation calculations, analytics, persistence, and Ask Compensation orchestration.

PostgreSQL is authoritative for employee, compensation, FX-rate, and analytics data.

The system remains a modular monolith. The current product scope and 10,000-employee dataset do not justify distributed backend services, caches, queues, or additional data stores.

---

## Technology

### Frontend

- Next.js
- React
- TypeScript

The frontend owns presentation, navigation, user interactions, loading and error states, and server-side calls to the backend API.

Search, filter, pagination, and analytics state are represented in URLs where useful so views survive refresh and browser navigation.

### Backend

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy 2
- Alembic
- Psycopg

FastAPI exposes the product API.

Pydantic validates API contracts and the planner's structured responses.

sqlglot parses and validates the SQL Ask Compensation's planner writes before it is executed.

SQLAlchemy owns query construction and database access.

Alembic manages schema changes.

### Database

PostgreSQL stores:

- employees,
- current compensation,
- deterministic currency-to-USD exchange rates.

Monetary values use fixed-precision numeric types rather than binary floating point.

The production PostgreSQL instance is hosted on Supabase and reached through the session-mode connection pooler.

---

## Application Boundaries

The backend is one deployable application with explicit internal responsibilities.

```text
FastAPI
 |
 +-- Employee
 |
 +-- Compensation
 |
 +-- Analytics
 |
 +-- Ask Compensation
 |
 +-- Database / Configuration
```

### Employee

Responsible for:

- employee directory,
- search,
- filtering,
- pagination,
- filter options,
- employee details.

### Compensation

Responsible for:

- current salary retrieval,
- salary updates,
- compensation validation,
- supported-currency validation.

Compensation writes are deterministic application operations. Ask Compensation is not involved in this path.

### Analytics

Responsible for:

- employee count,
- total annual payroll,
- average annual salary,
- grouping by country, department, and job title,
- filtering,
- currency normalization.

Aggregations execute in PostgreSQL rather than loading the full employee dataset into Python or the browser.

### Ask Compensation

Responsible for answering natural-language questions from the stored employee and compensation data with controlled read-only SQL, and for explaining which data is missing when a question cannot be answered.

It is organized by responsibility:

- `surface` — the approved relations and columns Ask Compensation can query, with their units and definitions,
- `plan` — the structured response the planner must return,
- `sql_validation` — parses candidate SQL, checks it against the allowlists and bounds, rewrites it deterministically, and renders the executable query,
- `sql_units` — traces result columns to the surface and enforces the money rules,
- `execution` — runs validated SQL in a read-only transaction and types the result,
- `answers` — composes the answer text and finds the matching Analytics view,
- `provider` — the planner interface and the Gemini adapter,
- `service` and `router` — orchestration, the single correction attempt, and the HTTP boundary.

Ask Compensation reads the same joins and salary normalization as Analytics, so equivalent questions give the same figures.

---

## Data Model

The MVP uses three core relational models.

### Employee

```text
id
employee_code
full_name
country
department
job_title
```

`employee_code` is unique.

### Compensation

```text
employee_id
annual_salary
currency_code
```

Each employee has one current compensation record.

Compensation is modeled separately from employee identity so compensation rules remain isolated without introducing salary-history complexity.

### FX Rate

```text
currency_code
rate_to_usd
```

Rates are deterministic seeded values.

Cross-country analytics calculate normalized salary when needed:

```text
salary_in_usd = annual_salary * rate_to_usd
```

Normalized salary is not persisted as a second salary value, avoiding duplicated monetary data that could diverge from the configured exchange rate.

---

## API

The backend API is intentionally small and aligned with product workflows.

```text
GET    /health

GET    /employees
GET    /employees/filter-options
GET    /employees/{employee_id}

PATCH  /employees/{employee_id}/compensation

GET    /analytics/summary
GET    /analytics/breakdown

POST   /analytics/ask
```

### Employee listing

`GET /employees` supports:

- page,
- page size,
- search,
- country,
- department,
- job title.

Search, filtering, ordering, and pagination are executed in PostgreSQL.

`GET /employees/filter-options` returns the distinct countries, departments, and job titles used by exact-match directory filters.

### Compensation update

`PATCH /employees/{employee_id}/compensation` updates current compensation only.

The backend validates the salary amount and currency before persistence.

### Analytics

The analytics endpoints expose the analytics service behind the Overview and Analytics pages. Ask Compensation runs its own validated queries over the same joins and the same `salary_in_usd` expression, and its tests compare results with this service.

### Ask Compensation

`POST /analytics/ask` takes a question and up to four earlier questions with the validated SQL and answer currency they used. It returns the status (`answered`, `missing_data`, or `unsupported`), the answer text, the planner's plain-language reading of the query, the validated SQL and currency for follow-ups, the result as typed columns and rows, and the equivalent Analytics view when one exists.

---

## Ask Compensation

If Compensation Hub has the data required to answer a factual read-only question, Ask Compensation derives the answer from that data. If the required data is not stored, it reports what is missing rather than inventing it. Answerability is bounded by the stored data, by read-only queries over the approved relations, by the SQL constructs the validator allows, and by the size and time limits below.

```text
HR question (+ up to 4 earlier questions with their validated SQL)
    |
    v
Gemini: candidate read-only SQL, or missing_data / unsupported
    |
    v
sqlglot parser -> syntax tree
    |
    v
Allowlist and bounds validation, qualification against the surface, money rules
    |
    v
Deterministic rewrites, literals bound as parameters, SQL rendered from the tree
    |
    v
Surface CTEs + validated query in a READ ONLY PostgreSQL transaction with a timeout
    |
    v
Exact result, amounts converted with the seeded rates, answer composed by application code
```

### Approved data surface

The planner never sees the database's tables. It queries two logical relations that the executor defines as `NOT MATERIALIZED` CTEs over the real tables in front of every query:

```text
employees    employee_id, employee_code, full_name, country, department, job_title,
             salary_currency, salary_local, salary_usd
fx_rates     currency_code, rate_to_usd
```

`salary_usd` is `annual_salary * rate_to_usd`. `salary_local` is the salary in the employee's own currency. Employees without compensation keep a row with NULL salary columns, so they count as employees but contribute no salary. These relations are the complete description of what Ask Compensation can know; exposing a new attribute means adding it to the surface deliberately.

### Validation

Model output is parsed with sqlglot's PostgreSQL dialect and rejected unless:

- it is exactly one SELECT (including WITH, UNION, INTERSECT, EXCEPT),
- every syntax node is on the allowlist: joins, WHERE with AND/OR/NOT, IN, LIKE/ILIKE, BETWEEN, IS, CASE, arithmetic, DISTINCT, GROUP BY, HAVING, ORDER BY, LIMIT/OFFSET, CTEs, subqueries, EXISTS, FILTER, WITHIN GROUP, and window functions,
- every function is on the allowlist: COUNT, SUM, AVG, MIN, MAX, STDDEV, MEDIAN, PERCENTILE_CONT/DISC, ROUND, ABS, FLOOR, CEIL, COALESCE, NULLIF, GREATEST, LEAST, LOWER, UPPER, TRIM, LENGTH, CONCAT, RANK, DENSE_RANK, ROW_NUMBER, NTILE, LAG, LEAD, FIRST_VALUE, LAST_VALUE,
- it reads only `employees`, `fx_rates`, and its own CTEs, with no schema-qualified, system, or catalog relation,
- every column exists, casts are to NUMERIC, integer, or text types only, and nothing is recursive, lateral, parameterized, or locking,
- it stays within the bounds: 5,000 characters, 1,000 syntax nodes, 4 levels of nesting, 8 CTEs, 4 joins per SELECT, 4 set operations, a final LIMIT of at most 100, and inner LIMIT or OFFSET of at most 10,000.

Statements such as INSERT, UPDATE, DELETE, MERGE, DDL, COPY, CALL, DO, SET, transaction control, SELECT INTO, and FOR UPDATE, and functions such as `pg_sleep`, `pg_read_file`, `set_config`, or `current_setting`, are refused outright. Unknown relations and columns are reported by name, which is how a question needing absent data becomes a missing-data answer.

The bounds are sized for a 10,000-employee surface: generous enough for multi-step analytical questions, small enough that a runaway query is rejected before it reaches the statement timeout.

### Money rules

Every result column is traced through CTEs, subqueries, and correlated references back to the surface columns it is computed from. That decides how the column is shown (text, count, money, percent, or number) and rejects calculations that would produce a wrong amount:

- `salary_local` may be shown beside `salary_currency` or compared, but never aggregated, windowed, or used in arithmetic, because it mixes currencies,
- amounts cannot be multiplied by amounts, added to counts, or divided into counts,
- amounts are never converted in SQL; they stay in USD and the application converts results to the answer currency with the seeded rates in Decimal.

### Rewrites and execution

The validated tree is rewritten before rendering. Medians (`MEDIAN` or `PERCENTILE_CONT(0.5)`) become the average of the lower and upper middle values from `percentile_disc`, which stays an exact NUMERIC value where `percentile_cont` would compute in double precision. Every division casts its dividend to NUMERIC and divides by `NULLIF(divisor, 0)`, so integer division never truncates and a zero divisor yields no value. Every string literal becomes a bound parameter, so no text from the model is spliced into the executed SQL, and comments are dropped.

The executed SQL is the surface CTEs followed by the rendered query. It runs in a `READ ONLY` transaction with a 5-second statement timeout. At most 100 rows are returned; when there are more, the total is counted separately. If the planner's response is rejected, or PostgreSQL reports a syntax, data, or cardinality error, the planner gets one correction attempt with the reason; a write or out-of-surface request gets none.

### Conversation

The frontend keeps the conversation in the application shell and sends up to four earlier answered questions with their validated SQL and answer currency. The backend validates that SQL again but never executes it. The planner decides whether a new question refers back to earlier turns; the currency and filters of earlier turns carry over only when it does. Result rows are never sent back to the model.

### Model boundary

The planner receives the question, the prior turns, the surface description, the distinct values of the category columns, and the configured currency codes. It:

- has no database credentials,
- never executes SQL; its SQL runs only after validation and re-rendering,
- cannot perform writes,
- does not calculate or phrase authoritative values,
- does not receive employee records or results.

Answer text is composed by application code from the returned rows. The planner's one-sentence reading of its query is written before the query runs, so it contains no results.

Provider-specific code is isolated behind a small planner interface. If the provider is unavailable, only Ask Compensation is unavailable; deterministic product workflows continue to operate.

---

## Currency Handling

Employee-level compensation is stored and displayed in local currency.

Organization-level monetary analytics use USD.

For example:

```text
Employee view
₹2,400,000 INR

Organization analytics
$28,800 USD
```

The backend performs normalization using the seeded FX-rate table.

A missing exchange rate is an error. The application does not silently exclude affected employees or treat different currencies as directly comparable.

---

## Data Access and Performance

The application is designed around 10,000 employee records.

The directory uses bounded server-side access:

```text
search / filters / page
        |
        v
Next.js server
        |
        v
FastAPI
        |
        v
PostgreSQL
        |
        v
bounded employee page
```

The system:

- uses server-side pagination,
- performs search and filtering in PostgreSQL,
- performs analytics aggregation in PostgreSQL,
- avoids loading all employees into application or browser memory,
- validates maximum page sizes,
- uses indexes for demonstrated access patterns,
- uses deterministic text collation for stable ordering across environments.

Directory prefetch behavior is also bounded. Employee detail data is fetched when the employee is opened rather than solely to construct per-employee page metadata.

No Redis, search engine, cache, queue, or additional database is introduced without measured need.

---

## Frontend Interaction Model

The final application shell keeps the primary product areas available while preserving working context.

- Employee directory state is URL-addressable.
- Analytics dimension, measure, and filter state are URL-addressable.
- Ask Compensation is available across primary pages.
- The assistant remains beside the page on wide screens and uses an overlay presentation at narrower widths.
- Ask Compensation answers that correspond to an Analytics view link into it.

These are presentation choices; product rules and authoritative calculations remain in the backend.

---

## Failure Boundaries

Core workflows do not depend on the language-model provider.

```text
Employee directory       works
Compensation management  works
Analytics                works
Ask Compensation         unavailable
```

Invalid model output is rejected before any data is read.

Database or application failures return controlled API errors rather than partial compensation results.

Sensitive configuration such as database credentials and the Gemini API key is provided through runtime configuration and is not committed to the repository.

---

## Deployment

Production uses independently deployable frontend and backend services:

```text
Browser
   |
   v
Cloud Run: compensation-hub-web
   |
   v
Cloud Run: compensation-hub-api
   |
   +-----------------------------+
   |                             |
   v                             v
Supabase PostgreSQL          Gemini API
```

Deployment characteristics:

- frontend: Cloud Run in `asia-south1`,
- backend: Cloud Run in `asia-south1`,
- database: Supabase PostgreSQL in `ap-south-1`,
- images: built by Cloud Build from the repository Dockerfiles,
- secrets: stored in Google Secret Manager,
- local runtime: uses the same frontend/backend/database boundaries through Docker Compose.

The backend remains one application internally even though the frontend and backend are deployed independently.

No additional infrastructure is introduced unless product behavior, measured performance, or operational requirements justify it.
