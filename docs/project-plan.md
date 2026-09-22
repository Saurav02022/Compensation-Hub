# Compensation Hub — Project Plan

This document is the execution tracker for Compensation Hub.

It defines the order of work and the exit condition for each phase. Product scope belongs in `requirements.md`, accepted choices in `decisions.md`, system design in `architecture.md`, and AI-specific rules in `ai-usage.md`.

**Current phase:** Phase 7 — Final Product Review and Delivery

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

- [x] Define the constrained analytics query-plan schema.
- [x] Add the LLM provider behind a small backend interface.
- [x] Convert supported natural-language questions into structured query plans.
- [x] Validate every generated plan before execution.
- [x] Execute valid plans through the existing analytics capability.
- [x] Return clear responses for unsupported or invalid questions.
- [x] Ensure the AI path cannot mutate employee or compensation data.
- [x] Handle LLM-provider failure without affecting core workflows.
- [x] Build the Ask Compensation frontend experience.
- [x] Add deterministic tests with the LLM boundary mocked.
- [x] Add a small optional live-model evaluation set.
- [x] Record meaningful AI-assisted engineering work in `ai-usage.md`.

**Exit condition:** complete — supported questions are mapped by Gemini to validated query plans and answered by the same analytics service as the overview page; with no provider configured or the provider failing, the API returns a clear 503 for Ask Compensation while the directory, compensation updates, and analytics keep working.

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
- [x] Add Docker Compose for the local application stack (both images verified by Cloud Build; the full compose stack has not been run on the development machine, which has no Docker).
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

- [ ] Review implemented behavior against `requirements.md`.
- [ ] Confirm implementation remains consistent with `decisions.md` and `architecture.md`.
- [ ] Reconcile documentation where an accepted decision changed during implementation.
- [ ] Finalize README setup, testing, and deployment instructions.
- [ ] Review the AI-assisted development record.
- [ ] Verify Git history is incremental and understandable.
- [ ] Perform a clean-clone setup and full verification run.
- [ ] Record a concise demo of the primary HR workflows.
- [ ] Verify repository, deployment, and demo links.

**Exit condition:** the product is reproducible, documented, deployed, and ready to understand and use without additional setup guidance.
