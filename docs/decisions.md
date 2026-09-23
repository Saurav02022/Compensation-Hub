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

Ask Compensation uses an LLM to interpret a natural-language question and map it to a constrained, structured read-only data request.

Application code validates that request and constructs the database operation with SQLAlchemy. PostgreSQL and deterministic application logic perform the authoritative query or calculation.

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

Ask Compensation can answer only questions that can be represented by the validated read-only query model and derived from data the product actually stores.

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

Gemini supports JSON-schema-constrained responses, which fits the constrained query-plan contract in D009. Keeping the adapter behind the planner interface means the rest of Ask Compensation, including routine automated tests, remains provider-independent.

**Trade-off**

Live-model behavior is verified only by the optional evaluation set, not by routine tests. Switching providers later requires a new adapter and a fresh run of that evaluation.

---

## D013 — Deploy to Google Cloud Run in Mumbai with a Supabase PostgreSQL database

The frontend and backend run as separate Cloud Run services in `asia-south1` (Mumbai) inside a dedicated Google Cloud project, built by Cloud Build from the repository Dockerfiles. PostgreSQL is a Supabase project in `ap-south-1` (Mumbai), reached through Supabase's IPv4 connection pooler in session mode.

Secrets are held in Secret Manager and mounted into the backend service, which runs under its own service account with access to nothing else. The frontend keeps the API base URL server-side and calls the backend over HTTPS.

**Why**

Cloud Run fits the frontend/backend deployment shape without introducing infrastructure to operate, and Cloud Build validates the same Dockerfiles used by the local container stack. Keeping the application and database in India gives the deployment one clear regional shape. Supabase's pooler is required because Cloud Run egress is IPv4 only while Supabase direct connections are IPv6.

**Trade-off**

Both services are publicly reachable, consistent with D002's single trusted user and absence of authentication; the backend is not restricted to the frontend. Cold starts apply with the minimum instance count of zero.


---

## D014 — Keep employee discovery bounded and server-side

Employee search, filtering, and pagination are executed by PostgreSQL through the backend API.

The frontend requests only the current bounded page of employees instead of loading the complete 10,000-employee dataset into the browser. Search, filter, and page state are URL-addressable, and filter choices come from a dedicated filter-options endpoint.

**Why**

The directory is an operational data workflow over 10,000 records. Server-side operations keep network payloads and browser memory bounded while making search, filters, pagination, refresh, and browser back/forward behavior predictable.

URL-addressable state also makes a directory view reproducible without introducing a client-side copy of the workforce dataset.

**Trade-off**

Directory interactions require server round trips, so the UI must handle loading and transition states well rather than relying on instant in-memory filtering.

---

## D015 — Make Ask Compensation a global contextual assistant

Ask Compensation is available from every primary application page instead of being a separate destination.

On wide screens it is presented beside the current page; on narrower screens it becomes an overlay sheet. Its conversation is preserved while the user navigates, and supported answers can link into the equivalent Analytics view.

**Why**

Natural-language analytics is most useful while the HR Manager is already working in the directory, employee detail, overview, or analytics. Keeping the assistant global preserves workflow context and makes it a product capability rather than a separate chatbot application.

**Trade-off**

The application shell owns additional cross-page state and responsive behavior. The assistant remains read-only and grounded in Compensation Hub data rather than becoming an unrestricted general-purpose chatbot.

---

## D016 — Use one focused analytics breakdown workspace

The final analytics experience uses a single breakdown workspace where the HR Manager chooses a dimension and measure, sees exact values alongside visual bars, and can drill into a selected row.

The selected dimension, metric, and filters are represented in the URL. Only the active breakdown is fetched. The visualization uses simple application UI rather than introducing a charting library.

**Why**

A focused workspace makes comparison and drill-down clearer than presenting several disconnected charts at once.

Keeping exact values visible preserves precision for compensation data, while URL state makes an analysis reproducible. The current single-series comparisons do not require a charting dependency.

**Trade-off**

The product exposes fewer simultaneous visualizations and less advanced chart interaction than a general-purpose BI tool.

---

## D017 — Make text ordering deterministic across environments

Employee text fields used for ordered directory pages, filter options, and breakdown keys use an explicit byte-order database collation.

**Why**

Default PostgreSQL collation depends on the host environment. During verification, Linux and Windows produced different ordering for the same seeded data, which would make pagination and tests environment-dependent.

An explicit collation makes ordering stable across local development, CI, and production.

**Trade-off**

Byte-order sorting is deterministic but is not intended to provide locale-aware linguistic ordering for every language.

---

## D018 — Avoid data fetches that exist only for dynamic page metadata

Employee detail pages use the product-level browser tab title rather than fetching an employee during route prefetch solely to generate a per-employee title.

**Why**

A production build showed that Next.js prefetching could resolve dynamic metadata for every visible employee link in the directory, causing up to 25 unnecessary employee-detail API requests for a single results page.

Removing that metadata fetch keeps directory navigation bounded to the list and filter-options requests until the user actually opens an employee.

**Trade-off**

Employee detail browser tabs show the generic Compensation Hub title instead of the employee's name.

---

## D019 — Ask Compensation is data-grounded, not question-list-driven

Ask Compensation is defined by the data available to the product rather than by a fixed catalogue of supported questions.

The governing rule is:

> If Compensation Hub has the data required to answer the question, Ask Compensation derives the answer from that data. If the required data is not available, it identifies what is missing rather than inventing an answer.

The language model translates natural language into a generic constrained read-only query AST. The AST is built from application-owned relational primitives: field projection, validated predicates, distinct rows, grouping, ordering, bounded limits, approved aggregates, conditional aggregates, arithmetic expressions, and deterministic FX conversion.

Application code validates the structure and semantics before constructing SQLAlchemy expressions. The model never supplies executable SQL and cannot represent writes.

For conversational follow-ups, the planner receives a bounded history of previous questions and their validated plans. It does not receive previous result rows or compensation values as conversational memory.

**Why**

A fixed list of question shapes makes a conversational interface fail on questions that are answerable from data the application already has. The useful product boundary is the available data and safe read-only operations over that data, not the set of questions anticipated during implementation.

RAG does not solve this problem because the current source of truth is structured relational data, not unstructured documents. Free-form text-to-SQL would broaden the execution surface unnecessarily. A constrained query AST keeps language interpretation flexible while preserving application-owned validation and execution.

**Trade-off**

The assistant can only derive answers from fields and relationships that exist in Compensation Hub and from operations represented by the validated AST. Questions requiring absent fields, historical information, external knowledge, or subjective compensation decisions remain unanswerable and are reported with the missing-data boundary.
