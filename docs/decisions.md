# Compensation Hub — Product & Engineering Decisions

This document records the key decisions that shape the MVP and the reasoning behind them.

## D001 — Manage current compensation only

The MVP manages an employee's current annual salary.

Salary history is deliberately excluded.

**Why**

Current compensation covers the core salary-management workflow without introducing versioning, effective dates, audit history, and historical reporting before those capabilities are needed.

**Trade-off**

The product cannot answer questions about how an employee's compensation changed over time.

---

## D002 — Assume a single trusted HR Manager

The MVP does not include authentication, authorization, or role-based access control.

**Why**

The first version has one user persona and no requirement for different levels of access. Identity and permission infrastructure would add complexity without improving the core compensation workflow.

**Trade-off**

The MVP is not suitable for a multi-user environment with different permissions.

---

## D003 — Keep the employee model intentionally small

Employee data is limited to the information required for compensation management and analysis:

- employee identifier,
- employee code,
- name,
- country,
- department,
- job title.

Compensation is modeled separately from employee identity.

**Why**

Each field should support an actual product workflow. Adding broader HR data would turn Compensation Hub into an employee-management system rather than a focused compensation product.

**Trade-off**

Questions requiring information such as tenure, performance, level, or employment type cannot be answered unless those fields are introduced later.

---

## D004 — Store salary in local currency and normalize analytics to USD

An employee's salary is stored in their local currency.

Organization-wide monetary analytics use USD as a common comparison currency.

The MVP uses a fixed, seeded set of exchange rates.

**Why**

Local currency preserves the value HR expects to see for an individual employee, while a common analytics currency makes cross-country totals and comparisons meaningful.

Fixed exchange rates keep results reproducible and remove a runtime dependency on an external foreign-exchange service.

**Trade-off**

Normalized values are suitable for product analytics but do not represent live market exchange rates.

---

## D005 — Provide focused analytics instead of a general report builder

The MVP supports a small set of compensation metrics:

- employee count,
- total annual payroll,
- average annual salary,
- breakdowns by country, department, and job title.

**Why**

These metrics answer common questions about workforce size and compensation distribution without introducing a generic reporting system.

A smaller analytics surface is easier to make correct, test, and understand.

**Trade-off**

Users cannot construct arbitrary reports or calculations outside the supported analytics model.

---

## D006 — Use PostgreSQL as the source of truth

Compensation Hub uses PostgreSQL for employee, compensation, exchange-rate, and analytics data.

**Why**

The product works with structured relational data and requires filtering, aggregation, constraints, indexing, and reliable monetary calculations.

PostgreSQL provides these capabilities without introducing additional data stores.

**Trade-off**

It requires more local and deployment setup than an embedded database such as SQLite.

---

## D007 — Use a modular monolith

The product consists of:

- a Next.js frontend,
- a FastAPI backend,
- a PostgreSQL database.

The backend remains one deployable application with clear internal boundaries rather than being split into multiple services.

**Why**

The current scale and feature set do not justify the operational and development cost of distributed services.

A modular monolith keeps the system simple while still allowing employee, compensation, analytics, and AI concerns to remain separated in code.

**Trade-off**

If the product later develops independently scaling workloads or independently owned domains, some boundaries may need to be extracted.

---

## D008 — Use REST between the frontend and backend

The frontend communicates with the backend through a typed REST API.

**Why**

The product has a straightforward client-server interaction model. REST is easy to inspect, test, document, and operate, and it is sufficient for the MVP.

**Trade-off**

The API is intentionally designed around supported product workflows rather than exposing a fully flexible query interface.

---

## D009 — Use AI for language understanding, not authoritative calculation

Ask Compensation uses an LLM to interpret a natural-language question and map it to a constrained, structured analytics request.

Application code validates that request and PostgreSQL performs the actual calculation.

The LLM does not:

- receive database credentials,
- generate or execute arbitrary SQL,
- update employee or compensation data,
- calculate authoritative compensation totals,
- make salary recommendations.

**Why**

Natural language makes analytics easier to access, but compensation data requires predictable and verifiable results.

Keeping interpretation probabilistic and calculation deterministic gives the AI feature a useful role without making it the source of truth.

**Trade-off**

Ask Compensation can answer only questions supported by the product's analytics model.

---

## D010 — Do not use RAG or a vector database in the MVP

The MVP does not use document retrieval, embeddings, or vector search.

**Why**

The product's source data is structured relational data, and the questions it needs to answer require exact filtering and aggregation rather than semantic document retrieval.

RAG would become useful if the product later included unstructured sources such as compensation policies, country-specific HR documents, or salary guidelines.

**Trade-off**

Ask Compensation cannot answer questions whose answers exist only in external or unstructured documents.

---

## D011 — Seed data must be deterministic

The product includes a repeatable seed process for 10,000 synthetic employees, their current compensation, and required exchange rates.

**Why**

Deterministic data makes development, testing, debugging, analytics verification, and demonstrations reproducible.

**Trade-off**

The seeded dataset is designed to exercise product behavior and should not be treated as representative of a real organization's workforce.
---

## D012 — Use Google Gemini as the Ask Compensation language model

Ask Compensation calls the Gemini API through the official `google-genai` Python SDK, behind the backend's small planner interface.

The model is configured through `GEMINI_MODEL` (default `gemini-3.8-flash`) and the key through `GEMINI_API_KEY`. When no key is configured the feature reports itself unavailable.

**Why**

The product owner has a Gemini API key available, and the SDK supports JSON-schema-constrained responses, which fits the constrained query-plan contract in D009. Keeping the adapter behind the planner interface means the rest of Ask Compensation, and all of its automated tests, remain provider-independent.

**Trade-off**

Live-model behavior is verified only by the optional evaluation set, not by routine tests. Switching providers later requires a new adapter and a fresh run of that evaluation.
