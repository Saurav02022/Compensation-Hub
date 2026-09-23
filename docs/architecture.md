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

Responsible for converting supported natural-language questions into constrained analytics operations.

It does not own compensation calculations. Validated plans are executed through the same analytics capability used by the rest of the application, so natural-language answers and analytics views share one source of truth.

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

The analytics endpoints expose the same analytics service used by Ask Compensation. There is no separate calculation path for natural-language answers.

---

## Ask Compensation

Natural-language analytics follows a constrained flow:

```text
HR question
    |
    v
Gemini
    |
    v
Structured Query Plan
    |
    v
Pydantic Validation
    |
    v
Analytics Service
    |
    v
SQLAlchemy
    |
    v
PostgreSQL
    |
    v
Exact Result
```

A plan can contain supported concepts such as:

```text
metric
filters
group_by
sort
limit
```

Supported metrics include:

```text
employee_count
average_salary
total_payroll
```

Supported dimensions include:

```text
country
department
job_title
```

The model is responsible for language interpretation only.

It:

- has no database credentials,
- does not generate executable SQL,
- cannot perform writes,
- does not calculate authoritative compensation values,
- does not receive the complete employee dataset.

The backend validates every generated plan before execution. Unsupported questions are rejected rather than approximated.

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
- Supported Ask Compensation results can link into the corresponding Analytics view.

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
