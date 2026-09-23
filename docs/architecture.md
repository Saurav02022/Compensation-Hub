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

Pydantic validates API contracts and structured Ask Compensation plans.

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

Ask Compensation is a constrained natural-language interface over the employee, current-compensation, and FX data model.

The governing contract is:

> If Compensation Hub has the data required to answer the question, Ask Compensation derives the answer from that data. If the required data is not available, it identifies what is missing rather than inventing an answer.

The request path is:

```text
Current question
      +
bounded prior validated intent
      |
      v
Gemini
      |
      v
Generic read-only query program
      |
      v
Pydantic structural validation
      |
      v
Field / operator / value / bound validation
      |
      v
SQLAlchemy query construction
      |
      v
PostgreSQL
      |
      +---- optional deterministic arithmetic
      |
      v
Grounded result
```

### Logical query surface

The planner can reference only fields exposed by the application:

```text
employee_code
full_name
country
department
job_title
annual_salary
currency_code
salary_usd
rate_to_usd
has_compensation
```

`salary_usd` is a derived expression using the configured FX rate; it is not a second persisted salary.

The generic program can combine safe read-only primitives:

- field projection,
- exact and text filters,
- numeric comparisons,
- distinct values,
- grouping,
- ordering,
- bounded limits,
- count and count-distinct,
- sum, average, minimum, maximum, median, standard deviation, variance, and percentile,
- deterministic arithmetic across scalar query results,
- normalized monetary conversion through the FX table.

This query language exists so answerability is determined by available data rather than a hard-coded list of natural-language question templates.

### Validation and execution

Every generated program is validated before execution.

The application enforces:

- an allowlist of fields,
- an allowlist of filter and aggregate operations,
- bounded query count and row limits,
- valid projection and grouping combinations,
- deterministic handling of local versus normalized salary,
- current dimension and currency values for exact controlled-value filters,
- valid references between deterministic calculation steps.

The model cannot express insert, update, delete, schema changes, arbitrary SQL, database functions outside the allowlist, or unbounded result retrieval.

The SQL executed by PostgreSQL is constructed by SQLAlchemy from validated application-owned operations.

### Conversational context

The frontend keeps the conversation across page navigation.

For a follow-up turn, the backend may send the planner at most six previous user questions together with their already validated query programs. Previous result rows and compensation values are not replayed to the model.

The planner must return a complete new program for the current turn. References such as "that", "same", "only", or "what about" therefore resolve to validated intent rather than to model-generated memory.

### Missing data

The language model is expected to return an unsupported result when a required field or source is not present.

The response names the missing data or product boundary rather than estimating, inferring an employee attribute, or substituting external knowledge.

RAG and a vector database are not used because the current source of truth is structured relational data. They would become relevant only if the product later introduced unstructured sources that need semantic retrieval.

### Failure boundary

Provider-specific code remains behind the planner interface. A provider outage affects Ask Compensation only; the employee directory, compensation management, and deterministic Analytics workspace continue to operate.

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
- Ask Compensation preserves validated intent across a bounded number of turns for contextual follow-ups.
- Results that map directly to the fixed Analytics workspace can link into the corresponding Analytics view.

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

Invalid model output is rejected before reaching the analytics layer.

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
