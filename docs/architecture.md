# Compensation Hub — Architecture

## Overview

Compensation Hub is a small modular web application with three primary runtime components:

```text
Browser
   |
   v
Next.js Frontend
   |
   | REST / JSON
   v
FastAPI Backend
   |
   v
PostgreSQL
```

The frontend is responsible for user interaction and presentation.

The backend owns product rules, validation, compensation calculations, analytics, and AI orchestration.

PostgreSQL is the source of truth for employee and compensation data.

The system remains a modular monolith. The current scale and product scope do not require independently deployed backend services.

---

## Technology

### Frontend

* Next.js
* React
* TypeScript

The frontend communicates with the backend only through the public REST API. It does not access the database or duplicate compensation business rules.

### Backend

* Python 3.12
* FastAPI
* Pydantic
* SQLAlchemy 2
* Alembic
* Psycopg

FastAPI exposes the application API.

Pydantic defines and validates API contracts and AI-generated structured requests.

SQLAlchemy owns database access and query construction.

Alembic manages schema migrations.

### Database

PostgreSQL stores:

* employees,
* current compensation,
* seeded foreign-exchange rates.

Monetary values use fixed-precision numeric types rather than floating-point values.

---

## Backend Boundaries

The backend is one deployable application with clear internal modules.

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

* employee directory,
* search,
* filtering,
* pagination,
* employee details.

### Compensation

Responsible for:

* current salary retrieval,
* salary updates,
* compensation validation.

Compensation writes remain deterministic application operations. AI is not involved in this path.

### Analytics

Responsible for:

* employee count,
* total annual payroll,
* average annual salary,
* grouping by country, department, and job title,
* currency normalization.

Aggregations are executed by PostgreSQL rather than by loading the full employee dataset into application memory.

### Ask Compensation

Responsible for converting natural-language questions into supported analytics operations.

It does not own compensation calculations. It delegates validated requests to the same analytics capability used by the rest of the application.

This keeps dashboard results and natural-language results consistent.

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

Compensation is modeled separately so employee identity and compensation concerns remain distinct, while avoiding salary-history complexity in the MVP.

### FX Rate

```text
currency_code
rate_to_usd
```

Rates are seeded and deterministic.

Cross-country analytics calculate normalized values using:

```text
salary_in_usd = annual_salary * rate_to_usd
```

The normalized salary is calculated when needed rather than stored as a second salary value. This avoids duplicated monetary data becoming inconsistent with the configured exchange rate.

---

## API

The initial API surface is intentionally small.

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

* page,
* page size,
* search,
* country,
* department,
* job title.

Pagination is performed in PostgreSQL.

`GET /employees/filter-options` returns the distinct countries, departments, and job titles so the directory can offer exact-match filters.

### Compensation update

`PATCH /employees/{employee_id}/compensation` updates current compensation only.

The backend validates monetary values and currency before persistence.

### Analytics

The analytics endpoints expose the same underlying analytics service used by Ask Compensation.

This prevents separate implementations of the same compensation calculations.

---

## Ask Compensation

Natural-language analytics follows a constrained flow:

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

The LLM is responsible only for interpreting language.

A query plan can contain supported concepts such as:

```text
metric
filters
group_by
sort
limit
```

Examples of supported metrics include:

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

The application validates the plan before execution.

The LLM:

* has no database credentials,
* does not generate executable SQL,
* cannot perform writes,
* does not calculate authoritative compensation values,
* does not receive the complete employee dataset.

If a question cannot be represented by the supported analytics model, the request is rejected as unsupported rather than approximated.

The LLM provider is kept behind a small application interface so provider-specific code does not leak into product logic.

---

## Currency Handling

The employee experience uses local salary and local currency.

Organization-level monetary analytics use USD.

For example:

```text
Employee view
₹2,400,000 INR

Organization analytics
$28,800 USD
```

The backend performs normalization using the seeded FX-rate table.

A missing exchange rate is treated as an error. The application must not silently exclude an employee or treat currencies as directly comparable.

---

## Data Access and Performance

The application is designed around 10,000 employee records.

This does not require distributed infrastructure, but it does require sensible database access.

The system will:

* use server-side pagination,
* perform aggregations in PostgreSQL,
* avoid loading all employees into application memory,
* use a unique index for employee code,
* index common filter fields where query behavior justifies it,
* validate maximum page sizes.

Additional indexes should be introduced based on actual query patterns rather than added speculatively.

---

## Failure Boundaries

Core compensation workflows must not depend on the AI provider.

If the LLM service is unavailable:

```text
Employee directory       works
Compensation management  works
Dashboard analytics      works
Ask Compensation         unavailable
```

Invalid AI output is rejected before reaching the analytics layer.

Database or application failures return controlled API errors rather than partial compensation results.

Sensitive configuration such as database credentials and LLM API keys is provided through environment variables and is never committed to the repository.

---

## Deployment Shape

The product is deployed as:

```text
Next.js application
        |
FastAPI application
        |
PostgreSQL database
```

Frontend and backend are independently deployable, while the backend remains one application internally.

Local development will use the same boundaries so behavior does not depend on a special development-only architecture.

No additional infrastructure is introduced unless a demonstrated product or operational need requires it.
