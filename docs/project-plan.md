# Compensation Hub — Project Plan

This document is the execution tracker for Compensation Hub.

It defines the order of work and the completion criteria for each phase. Product requirements live in `requirements.md`, product and engineering choices live in `decisions.md`, architecture lives in `architecture.md`, and AI-specific rules live in `ai-usage.md`.

## Status

- [x] Complete
- [ ] Not complete

---

## Phase 0 — Product and Repository Foundation

- [x] Initialize the frontend and backend projects.
- [x] Remove generated template content.
- [x] Verify the frontend builds and lints successfully.
- [x] Verify the backend application starts and exposes `/health`.
- [x] Normalize repository line endings.
- [x] Define MVP requirements.
- [x] Record product and engineering decisions.
- [x] Document the system architecture.
- [x] Document AI usage and boundaries.
- [ ] Add this project plan.
- [ ] Replace the temporary root `AGENTS.md` with project-specific agent instructions.
- [ ] Update `CLAUDE.md` to load the project context.
- [ ] Replace the temporary root `README.md` with the product README.

**Exit condition:** the repository contains the agreed product context and agent instructions before feature implementation begins.

---

## Phase 1 — Database Foundation and Seed Data

- [ ] Configure application settings and environment variables.
- [ ] Add PostgreSQL for local development.
- [ ] Configure SQLAlchemy database access.
- [ ] Configure Alembic migrations.
- [ ] Implement the Employee, Compensation, and FX Rate models.
- [ ] Create the initial migration.
- [ ] Implement deterministic seed generation for 10,000 employees and required exchange rates.
- [ ] Verify the database can be created and seeded from a clean environment.
- [ ] Add tests for data constraints and seed reproducibility.

**Exit condition:** a clean database can be migrated and deterministically populated with the complete MVP dataset.

---

## Phase 2 — Employee Directory and Compensation Management

### Backend

- [ ] Implement paginated employee listing.
- [ ] Implement search by employee name and employee code.
- [ ] Implement filters for country, department, and job title.
- [ ] Implement employee detail retrieval.
- [ ] Implement current compensation updates.
- [ ] Validate salary amounts and currency codes.
- [ ] Add automated tests for the core employee and compensation workflows.

### Frontend

- [ ] Build the employee directory.
- [ ] Add search, filters, pagination, and loading/error states.
- [ ] Build the employee detail view.
- [ ] Build the current-compensation edit flow.
- [ ] Add frontend tests for important user behavior.

**Exit condition:** the HR Manager can find an employee, view current compensation, and update salary end to end.

---

## Phase 3 — Compensation Analytics

### Backend

- [ ] Implement employee-count analytics.
- [ ] Implement total annual payroll.
- [ ] Implement average annual salary.
- [ ] Implement breakdowns by country, department, and job title.
- [ ] Normalize cross-country monetary metrics to USD using seeded FX rates.
- [ ] Ensure aggregations execute in PostgreSQL.
- [ ] Add correctness tests for metrics, filters, grouping, and currency normalization.

### Frontend

- [ ] Build the compensation overview.
- [ ] Present organization-level metrics clearly.
- [ ] Add useful breakdown views for supported dimensions.
- [ ] Handle empty and error states.

### Performance

- [ ] Review employee-directory query behavior.
- [ ] Review analytics query behavior.
- [ ] Add or adjust indexes only where query patterns justify them.
- [ ] Confirm the application does not load the complete employee dataset into memory for listing or analytics.

**Exit condition:** the product answers the supported compensation questions reliably without using AI.

---

## Phase 4 — Ask Compensation

- [ ] Define the structured analytics query-plan schema.
- [ ] Add the LLM provider adapter behind an application interface.
- [ ] Implement natural-language-to-query-plan conversion.
- [ ] Validate every generated query plan before execution.
- [ ] Route valid plans through the existing analytics capability.
- [ ] Reject unsupported or invalid questions clearly.
- [ ] Ensure the AI path cannot mutate employee or compensation data.
- [ ] Add graceful behavior when the LLM provider is unavailable.
- [ ] Build the Ask Compensation frontend experience.
- [ ] Add deterministic automated tests using mocked LLM responses.
- [ ] Add a small set of optional live-model evaluation cases.
- [ ] Record meaningful AI-assisted implementation work in `ai-usage.md`.

**Exit condition:** supported natural-language questions produce results through the same trusted analytics logic used by the rest of the product, and core workflows remain functional without the LLM.

---

## Phase 5 — Quality and Continuous Integration

- [ ] Add backend lint, formatting, typing, and test commands.
- [ ] Add frontend lint, type-check, test, and build commands.
- [ ] Add GitHub Actions for automated quality checks.
- [ ] Verify CI does not depend on a live LLM call.
- [ ] Review API error handling and validation.
- [ ] Review application logging and health checks.
- [ ] Review environment-variable handling and confirm secrets are not committed.
- [ ] Run the complete test suite from a clean checkout.

**Exit condition:** the repository passes all automated quality checks from a clean environment.

---

## Phase 6 — Local Runtime and Deployment

- [ ] Add Dockerfiles where they improve repeatable deployment.
- [ ] Add Docker Compose for the local application stack.
- [ ] Document required environment variables in `.env.example`.
- [ ] Verify the complete product can be started locally from documented commands.
- [ ] Choose appropriate managed deployment targets.
- [ ] Provision the production PostgreSQL database.
- [ ] Deploy the backend.
- [ ] Deploy the frontend.
- [ ] Configure production environment variables and secrets.
- [ ] Run migrations and seed the deployed database.
- [ ] Smoke-test the deployed product.
- [ ] Verify failure of the LLM provider does not affect core compensation workflows.

**Exit condition:** the deployed product is accessible and the documented local setup remains reproducible.

---

## Phase 7 — Final Product Review and Delivery

- [ ] Review the implemented product against `requirements.md`.
- [ ] Confirm code and behavior remain consistent with `decisions.md` and `architecture.md`.
- [ ] Update documentation where implementation intentionally changed an earlier decision.
- [ ] Finalize the root `README.md` with setup, architecture overview, testing, and deployment instructions.
- [ ] Review the AI development record.
- [ ] Verify Git history remains incremental and understandable.
- [ ] Perform a final clean-clone setup and test run.
- [ ] Record a concise product demo covering the primary HR workflows.
- [ ] Verify repository, deployment, and demo links before sharing.

**Exit condition:** the product is reproducible, documented, deployed, and ready to be reviewed without additional explanation.
