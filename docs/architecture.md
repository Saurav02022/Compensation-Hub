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

Pydantic validates API contracts and the structured queries Ask Compensation plans.

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

Responsible for converting natural-language questions into validated read-only queries over the stored employee and compensation data, running them in PostgreSQL, and explaining which data is missing when a question cannot be answered.

It is organized by responsibility:

- `catalog` — the fields Ask Compensation can reason about and the operations each field kind allows,
- `plan` — the query representation the model produces, with its structural limits,
- `validation` — checks a query against the catalog, the category values in the data, and the configured currencies,
- `execution` — turns a validated query into one bounded SQLAlchemy SELECT in a read-only transaction,
- `answers` — composes the answer text, the plain-language reading of the query, and the matching Analytics view,
- `provider` — the planner interface and the Gemini adapter,
- `service` and `router` — orchestration and the HTTP boundary.

Ask Compensation reads the same tables with the same joins and salary normalization as Analytics, so equivalent questions give the same figures.

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

The analytics endpoints expose the analytics service behind the Overview and Analytics pages. Ask Compensation runs its own validated queries but uses the same joins and the same `salary_in_usd` expression, and its tests compare results with this service.

### Ask Compensation

`POST /analytics/ask` takes a question and up to four earlier questions with the validated queries they produced. It returns the status (`answered`, `missing_data`, or `unsupported`), the answer text, the validated query, a plain-language reading of it, the result as typed columns and rows, and the equivalent Analytics view when one exists.

---

## Ask Compensation

Ask Compensation answers a question from the stored data whenever the question can be expressed as a supported read-only query, and says which data is missing otherwise.

```text
HR question (+ earlier questions and their validated queries)
    |
    v
Gemini: planning only
    |
    v
Structured query or a missing-data / unsupported response
    |
    v
Pydantic structure checks
    |
    v
Validation against the field catalog, category values, and currencies
    |
    v
One bounded SELECT in a read-only PostgreSQL transaction
    |
    v
Exact result, composed into an answer by application code
```

### Field catalog

The catalog is the complete description of what Ask Compensation can know:

```text
employee_code   text       filter; count
full_name       text       filter; count
country         category   filter; group; count
department      category   filter; group; count
job_title       category   filter; group; count
currency        category   filter; group; count
salary          money      filter; count, sum, avg, median, min, max; order
local_salary    money      employee rows only, in the employee's own currency
```

`salary` is `annual_salary * rate_to_usd`, expressed in the query's answer currency. `local_salary` is never aggregated or compared, because amounts in different currencies cannot be combined. A field that is not in the catalog does not exist for Ask Compensation; exposing a new attribute means adding it to the catalog deliberately.

### Query representation

A query is either a list of employee rows or a set of aggregate measures:

```text
kind            rows | aggregate
filters         conditions on catalog fields, all of which must hold
fields          fields to show (rows)
group_by        up to two category fields (aggregate)
measures        count, count_distinct, sum, avg, median, min, max, each with optional own filters
calculations    add, subtract, multiply, divide, percent over measures, earlier calculations, or numbers
having          conditions on measures or calculations
order_by        fields (rows) or grouped fields, measures, and calculations (aggregate)
limit           at most 100 rows or groups; employee lists default to 25
currency        the answer currency, USD unless another configured currency is asked for
```

The representation has no way to name a table, write SQL, or describe a write.

### Validation and execution

The application, not the model, decides what is valid. Before any data is read it checks that every field exists in the catalog, every operation suits its field kind, category values exist in the data (matched without regard to case), currencies have a seeded rate, names are unique and references point backwards, arithmetic combines compatible units (no money multiplied by money, no money added to a headcount), expressions nest at most three levels, and limits are within bounds.

Execution builds one SELECT over employees LEFT JOIN compensation LEFT JOIN fx_rates, with every plan value bound as a parameter, inside a `READ ONLY` transaction with a statement timeout. Employees without compensation count as employees but contribute no salary. Text matching escapes wildcard characters. Division by a zero aggregate yields no value rather than an error. Medians average the lower and upper middle values from `percentile_disc`, so they stay exact NUMERIC values; `percentile_cont` would compute in double precision. Row and group results that hit their limit also report the total number of matches.

### Conversation

The frontend keeps the conversation in the application shell and sends up to four earlier answered questions with their validated queries. The planner receives them as prior turns and must still return a complete query, which is validated like any other. Result rows are never sent back to the model.

### Model boundary

The planner receives the question, the prior turns, the catalog, the category values present in the data, and the configured currency codes. It:

- has no database credentials,
- does not generate executable SQL,
- cannot perform writes,
- does not calculate or phrase authoritative values,
- does not receive employee records or results.

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
