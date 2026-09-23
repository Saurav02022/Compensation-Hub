# Compensation Hub — Project Plan

This document is the execution tracker for Compensation Hub.

It defines the order of work and the exit condition for each phase. Product scope belongs in `requirements.md`, accepted choices in `decisions.md`, system design in `architecture.md`, and AI-specific rules in `ai-usage.md`.

**Current phase:** Phase 7 — Final Product Review and Delivery (demo recording pending)

## Status

- [x] Complete
- [ ] Not complete

---

## Phase 0 — Product and Repository Foundation

- [x] Initialize the Next.js frontend and FastAPI backend.
- [x] Remove generated template content and leave both applications in a minimal working state.
- [x] Verify frontend linting and production build.
- [x] Verify backend startup and `GET /health`.
- [x] Normalize repository line endings.
- [x] Define MVP requirements.
- [x] Record product and engineering decisions.
- [x] Document the system architecture.
- [x] Document AI usage and boundaries.
- [x] Add the project execution plan.
- [x] Add project-specific coding-agent instructions.
- [x] Configure Claude Code project context.
- [x] Add the project README.

**Exit condition:** complete — the repository has a verified foundation and the agreed product and engineering context required before feature implementation.

---

## Phase 1 — Database Foundation and Seed Data

### Configuration and PostgreSQL

- [x] Add backend settings for database and runtime configuration.
- [x] Add tracked `.env.example` files without real credentials.
- [x] Add PostgreSQL for local development.
- [x] Configure SQLAlchemy sessions and database connectivity.
- [x] Configure Alembic migrations.

### Data Model

- [x] Implement `Employee`.
- [x] Implement `Compensation`.
- [x] Implement `FxRate`.
- [x] Enforce required relational and monetary constraints.
- [x] Create and verify the initial migration.

### Seed Data

- [x] Implement deterministic generation of 10,000 employees.
- [x] Seed current compensation in appropriate local currencies.
- [x] Seed deterministic currency-to-USD exchange rates.
- [x] Make the seed process safe to run in a clean development environment.
- [x] Add tests for important data constraints and seed reproducibility.

**Exit condition:** complete — a clean PostgreSQL database can be migrated with `alembic upgrade head` and deterministically populated with the complete 10,000-employee MVP dataset through the seed command.

---

## Phase 2 — Employee Directory and Compensation Management

### Backend

- [x] Implement paginated employee listing.
- [x] Implement search by employee name and employee code.
- [x] Implement filters for country, department, and job title.
- [x] Implement employee detail retrieval.
- [x] Implement current-compensation updates.
- [x] Validate salary amounts and supported currencies.
- [x] Add automated tests for employee and compensation behavior.

### Frontend

- [x] Build the employee directory.
- [x] Add search, filters, and server-backed pagination.
- [x] Handle loading, empty, and error states.
- [x] Build the employee detail view.
- [x] Build the current-compensation edit flow.
- [x] Add tests for important user behavior.

**Exit condition:** complete — the HR Manager can search and filter the directory, open an employee, and update the current salary end to end through the Next.js UI and FastAPI API.

---

## Phase 3 — Compensation Analytics

### Backend

- [x] Implement employee-count analytics.
- [x] Implement total annual payroll.
- [x] Implement average annual salary.
- [x] Implement breakdowns by country, department, and job title.
- [x] Normalize cross-country monetary metrics to USD using seeded FX rates.
- [x] Keep filtering and aggregation in PostgreSQL.
- [x] Add correctness tests for metrics, grouping, filtering, and currency normalization.

### Frontend

- [x] Build the compensation overview.
- [x] Present organization-level metrics with explicit currency context.
- [x] Add breakdown views for the supported dimensions.
- [x] Handle loading, empty, and error states.

### Performance Review

- [x] Review employee-directory query behavior.
- [x] Review analytics query behavior.
- [x] Add or adjust indexes only where query patterns justify them.
- [x] Confirm listing and analytics do not load the complete employee dataset into application memory.

**Exit condition:** complete — employee count, total payroll, average salary, and breakdowns by country, department, and job title are computed in PostgreSQL with USD normalization and shown in the compensation overview, without any AI involvement.

---

## Phase 4 — Ask Compensation

- [x] Define a generic constrained read-only query AST over the available product data.
- [x] Add the LLM provider behind a small backend interface.
- [x] Translate natural-language questions into the generic query AST rather than a fixed question catalog.
- [x] Validate every generated plan structurally and semantically before execution.
- [x] Construct database operations with SQLAlchemy; do not execute model-generated SQL.
- [x] Support projection, filtering, distinct values, grouping, ordering, bounded limits, aggregates, conditional aggregates, arithmetic, and FX conversion.
- [x] Carry bounded prior validated intent for conversational follow-up questions.
- [x] Return the missing data boundary when a question cannot be derived from available data.
- [x] Ensure Ask Compensation remains read-only.
- [x] Handle provider failure without affecting core workflows.
- [x] Build generic scalar/table result rendering in the frontend.
- [x] Add deterministic tests with the provider boundary mocked.
- [x] Add an optional live-model evaluation set covering varied answerable and missing-data questions.
- [x] Record the product AI boundary in `ai-usage.md`.

**Exit condition:** complete — Ask Compensation can derive read-only answers from the employee, current-compensation, and FX data through a validated generic query AST; questions requiring unavailable data identify that gap, and a provider failure does not affect the directory, compensation updates, or deterministic analytics.

---

## Phase 5 — Quality and Continuous Integration

- [x] Finalize backend linting, formatting, typing, and test commands.
- [x] Finalize frontend linting, type-checking, testing, and build commands.
- [x] Add GitHub Actions for automated quality checks.
- [x] Ensure CI does not require a live LLM call.
- [x] Review API validation and error handling.
- [x] Review application logging and health checks.
- [x] Review environment-variable handling and secret hygiene.
- [x] Run the complete quality suite from a clean checkout.

**Exit condition:** complete — GitHub Actions runs ruff, mypy, pytest against PostgreSQL, eslint, tsc, vitest, and the production build on every push and pull request without any LLM credential, and the same commands pass from a fresh clone.

---

## Phase 6 — Local Runtime and Deployment

### Local Runtime

- [x] Add Dockerfiles where they improve repeatable runtime behavior.
- [x] Add Docker Compose for the local application stack.
- [x] Verify `.env.example` documents all required runtime configuration.
- [x] Verify the complete product starts from documented local commands.

### Deployment

- [x] Select appropriate managed deployment targets.
- [x] Provision PostgreSQL.
- [x] Deploy the backend.
- [x] Deploy the frontend.
- [x] Configure production environment variables and secrets.
- [x] Run database migrations and seed the deployed dataset.
- [x] Smoke-test the deployed product.
- [x] Verify an LLM-provider outage does not break core compensation workflows.

**Exit condition:** complete — Compensation Hub runs on Cloud Run in Mumbai against a Supabase database in Mumbai, with `DATABASE_URL` and `GEMINI_API_KEY` mounted from Secret Manager, and remains reproducible locally from the documented setup steps.

---

## Phase 7 — Final Product Review and Delivery

- [x] Review implemented behavior against `requirements.md`.
- [x] Confirm implementation remains consistent with `decisions.md` and `architecture.md`.
- [x] Reconcile documentation where an accepted decision changed during implementation.
- [x] Finalize README setup, testing, and deployment instructions.
- [x] Review the AI-assisted development record.
- [x] Verify Git history is incremental and understandable.
- [x] Perform a clean-clone setup and full verification run.
- [ ] Record a concise demo of the primary HR workflows: directory search and filters, employee detail, salary update, compensation overview, analytics, and Ask Compensation.
- [ ] Verify repository, deployment, and demo links. The repository and deployed application are verified; the demo link is pending the recording.

**Exit condition:** the product is reproducible, documented, deployed, and ready to understand and use without additional setup guidance.

---

## Phase 8 — Product Design and UX Refinement

After the end-to-end product was working, the interface was refined to make the application feel coherent and polished without changing its architecture or scope.

- [x] Establish the visual foundations: tokens, typography, spacing, and the reusable UI primitives the product needs.
- [x] Build the application shell with a sticky header, product identity, and primary navigation with a clear active state.
- [x] Make Ask Compensation a global assistant available from every primary page, and retire the separate page.
- [x] Verify the employee directory relies only on server-side pagination, search, and filtering.
- [x] Refine directory search, filters, pagination, and URL-addressable state.
- [x] Refine the employee detail and compensation editing workflow.
- [x] Redesign analytics as a workspace with KPI summary, shared filters, focused charts, and exact values.
- [x] Turn the landing page into an overview that orients the HR Manager.
- [x] Make loading, empty, error, and success states intentional on every primary surface.
- [x] Complete a responsive and accessibility pass.
- [x] Align visual consistency across pages.
- [x] Update tests and run the full frontend and backend verification.

**Exit condition:** complete — the application uses one visual language, the header is sticky with clear navigation, Ask Compensation is reachable everywhere, directory and analytics remain server-backed, and lint, type, test, and build checks pass.

---

## Phase 9 — Product Design Rebuild

A second design pass rebuilt the interface around patterns observed in current B2B product interfaces so Compensation Hub reads as a focused operational product rather than a generic dashboard, without changing its API, business rules, or architecture.

- [x] Research product UI from YC-backed HR, finance, data, and analytics products.
- [x] Synthesize the research into a design direction for Compensation Hub.
- [x] Rebuild the visual foundations: typography, color, density, and the shared primitives.
- [x] Replace the top header with a sticky sidebar shell and compact mobile navigation.
- [x] Dock Ask Compensation beside the page, reachable from every screen and by keyboard.
- [x] Rebuild the employee directory toolbar, table, and pagination for 10,000 records.
- [x] Keep directory search, filters, and pagination server-side and URL-addressable.
- [x] Rebuild the employee detail page and the salary editing workflow.
- [x] Rebuild analytics as one breakdown workspace with exact values beside the bars.
- [x] Focus the overview on orientation and next steps.
- [x] Design loading, refresh, empty, error, and unavailable states on every surface.
- [x] Complete a responsive and accessibility pass.
- [x] Review the rendered product visually, refine it, and run the full verification.
- [x] Redeploy the rebuilt frontend to Cloud Run and verify it in production.

**Exit condition:** complete — the product runs in a sticky sidebar shell with Ask Compensation docked beside every page and on Ctrl/⌘ K, the directory and analytics stay server-backed and URL-addressable with bounded requests, analytics shows every measure beside its bars in one drill-down workspace, and lint, type, test, and build checks pass.


---

## Phase 10 — Data-Grounded Ask Compensation

Generalize the conversational assistant so answerability is determined by the data Compensation Hub has, not by a fixed list of anticipated question shapes.

- [x] Define the product contract: derive an answer whenever the required stored data is available; otherwise identify the missing data.
- [x] Replace the fixed analytics-plan shape with a generic constrained read-only query program.
- [x] Expose only approved employee, current-compensation, normalized salary, and FX fields to the planner.
- [x] Validate filter operators, projections, aggregates, grouping, ordering, row limits, currency handling, and arithmetic references before execution.
- [x] Construct all executable database operations with SQLAlchemy; do not execute model-generated SQL.
- [x] Keep every result set bounded.
- [x] Carry a bounded history of previous questions and validated programs so follow-up turns can refine prior intent.
- [x] Keep previous result rows and salary values out of model conversation history.
- [x] Return a specific missing-data boundary rather than infer absent employee attributes or external facts.
- [x] Preserve the provider-outage boundary so core product workflows remain independent of the language model.
- [x] Render generic scalar and tabular results in the existing assistant.
- [x] Expand deterministic tests and the optional live-model evaluation around the data-grounding contract.
- [x] Reconcile requirements, decisions, architecture, README, and AI-usage documentation.

**Exit condition:** complete — Ask Compensation uses a generic validated read-only query language over Compensation Hub data, supports bounded conversational refinement, derives authoritative results through PostgreSQL and deterministic application code, and refuses only when the required data or permitted operation is unavailable.
