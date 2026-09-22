# Compensation Hub

Compensation Hub is a web application for HR teams to manage current employee compensation and understand how compensation is distributed across a multi-country workforce.

The product is designed around a 10,000-employee dataset and focuses on three jobs: finding an employee quickly, managing current compensation, and answering organization-level compensation questions reliably.

## Core Capabilities

- Search and filter employees by name, employee code, country, department, and job title.
- View and update an employee's current annual salary.
- Keep employee compensation in local currency while using USD for cross-country analytics.
- View employee count, total annual payroll, average annual salary, and compensation breakdowns.
- Ask supported compensation questions in natural language through **Ask Compensation**.

## Compensation Model

Employee salary is stored in local currency.

Organization-wide monetary analytics are normalized to USD using deterministic seeded exchange rates. This keeps cross-country comparisons meaningful and results reproducible without making core product behavior depend on a live FX service.

The MVP manages current compensation only. Salary history, payroll processing, approval workflows, and broader HR lifecycle features are outside the current scope.

## Ask Compensation

Ask Compensation provides natural-language access to the product's existing analytics capabilities.

```text
HR question
    |
    v
LLM
    |
    v
Validated structured query
    |
    v
Analytics service
    |
    v
PostgreSQL
    |
    v
Authoritative result
```

The LLM interprets intent; it is not the source of truth.

It does not receive database credentials, execute arbitrary SQL, update compensation data, or calculate authoritative compensation values.

## Architecture

```text
Browser
   |
   v
Next.js + TypeScript
   |
   | REST / JSON
   v
FastAPI + Python
   |
   v
PostgreSQL
```

The backend is a modular monolith. Product rules, validation, analytics, currency normalization, and AI orchestration stay in the backend, while the frontend owns presentation and user interaction.

## Technology

| Area | Technology |
| --- | --- |
| Frontend | Next.js, React, TypeScript |
| Backend | Python 3.12, FastAPI, Pydantic |
| Data access | SQLAlchemy 2, Psycopg |
| Migrations | Alembic |
| Database | PostgreSQL |
| Backend environment | uv |
| Frontend package manager | npm |

## Repository Structure

```text
Compensation-Hub/
├── frontend/               # Next.js application
├── backend/                # FastAPI application
│   └── src/
│       └── compensation_hub/
├── docs/
│   ├── requirements.md
│   ├── decisions.md
│   ├── architecture.md
│   ├── ai-usage.md
│   └── project-plan.md
├── AGENTS.md
├── CLAUDE.md
└── README.md
```

## Local Development

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend is available at `http://localhost:3000`.

### Backend

```bash
cd backend
uv sync
uv run uvicorn compensation_hub.main:app --reload
```

The API is available at `http://localhost:8000`.

The health endpoint is:

```text
GET /health
```

Database setup, migrations, seed data, and full-stack runtime commands are added as their implementation phases are completed.

## Project Documentation

The repository keeps product and engineering context separate:

- [`docs/requirements.md`](docs/requirements.md) — MVP behavior and scope
- [`docs/decisions.md`](docs/decisions.md) — accepted choices and trade-offs
- [`docs/architecture.md`](docs/architecture.md) — system structure and responsibility boundaries
- [`docs/ai-usage.md`](docs/ai-usage.md) — product AI boundaries and AI-assisted development record
- [`docs/project-plan.md`](docs/project-plan.md) — implementation phases and progress
- [`AGENTS.md`](AGENTS.md) — engineering rules for coding agents
- [`CLAUDE.md`](CLAUDE.md) — Claude Code project context

## Engineering Principles

- Keep compensation calculations deterministic and testable.
- Treat PostgreSQL as the source of truth.
- Use AI for language understanding, not authoritative calculation.
- Prefer simple architecture over speculative infrastructure.
- Add complexity only when a product or operational need justifies it.
- Keep product behavior, documentation, and tests aligned as the system evolves.
