# Compensation Hub — Project Plan

This document is the execution tracker for Compensation Hub.

It defines the order of work and the exit condition for each phase. Product scope belongs in `requirements.md`, accepted choices in `decisions.md`, system design in `architecture.md`, and AI-specific rules in `ai-usage.md`.

**Current phase:** Phase 2 — Employee Directory and Compensation Management

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

- [ ] Build the employee directory.
- [ ] Add search, filters, and server-backed pagination.
- [ ] Handle loading, empty, and error states.
- [ ] Build the employee detail view.
- [ ] Build the current-compensation edit flow.
- [ ] Add tests for important user behavior.

**Exit condition:** the HR Manager can find an employee, view current compensation, and update salary end to end.

---

## Phase 3 — Compensation Analytics

### Backend

- [ ] Implement employee-count analytics.
- [ ] Implement total annual payroll.
- [ ] Implement average annual salary.
- [ ] Implement breakdowns by country, department, and job title.
- [ ] Normalize cross-country monetary metrics to USD using seeded FX rates.
- [ ] Keep filtering and aggregation in PostgreSQL.
- [ ] Add correctness tests for metrics, grouping, filtering, and currency normalization.

### Frontend

- [ ] Build the compensation overview.
- [ ] Present organization-level metrics with explicit currency context.
- [ ] Add breakdown views for the supported dimensions.
- [ ] Handle loading, empty, and error states.

### Performance Review

- [ ] Review employee-directory query behavior.
- [ ] Review analytics query behavior.
- [ ] Add or adjust indexes only where query patterns justify them.
- [ ] Confirm listing and analytics do not load the complete employee dataset into application memory.

**Exit condition:** the supported compensation questions can be answered reliably through deterministic application and database logic without AI.

---

## Phase 4 — Ask Compensation

- [ ] Define the constrained analytics query-plan schema.
- [ ] Add the LLM provider behind a small backend interface.
- [ ] Convert supported natural-language questions into structured query plans.
- [ ] Validate every generated plan before execution.
- [ ] Execute valid plans through the existing analytics capability.
- [ ] Return clear responses for unsupported or invalid questions.
- [ ] Ensure the AI path cannot mutate employee or compensation data.
- [ ] Handle LLM-provider failure without affecting core workflows.
- [ ] Build the Ask Compensation frontend experience.
- [ ] Add deterministic tests with the LLM boundary mocked.
- [ ] Add a small optional live-model evaluation set.
- [ ] Record meaningful AI-assisted engineering work in `ai-usage.md`.

**Exit condition:** supported natural-language questions use the same trusted analytics logic as the rest of the product, while core workflows remain independent of the LLM provider.

---

## Phase 5 — Quality and Continuous Integration

- [ ] Finalize backend linting, formatting, typing, and test commands.
- [ ] Finalize frontend linting, type-checking, testing, and build commands.
- [ ] Add GitHub Actions for automated quality checks.
- [ ] Ensure CI does not require a live LLM call.
- [ ] Review API validation and error handling.
- [ ] Review application logging and health checks.
- [ ] Review environment-variable handling and secret hygiene.
- [ ] Run the complete quality suite from a clean checkout.

**Exit condition:** a clean checkout passes the configured automated quality checks without relying on local machine state or live AI services.

---

## Phase 6 — Local Runtime and Deployment

### Local Runtime

- [ ] Add Dockerfiles where they improve repeatable runtime behavior.
- [ ] Add Docker Compose for the local application stack.
- [ ] Verify `.env.example` documents all required runtime configuration.
- [ ] Verify the complete product starts from documented local commands.

### Deployment

- [ ] Select appropriate managed deployment targets.
- [ ] Provision PostgreSQL.
- [ ] Deploy the backend.
- [ ] Deploy the frontend.
- [ ] Configure production environment variables and secrets.
- [ ] Run database migrations and seed the deployed dataset.
- [ ] Smoke-test the deployed product.
- [ ] Verify an LLM-provider outage does not break core compensation workflows.

**Exit condition:** Compensation Hub is accessible through a deployed environment and remains reproducible locally from documented setup steps.

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
