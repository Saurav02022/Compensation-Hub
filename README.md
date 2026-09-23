# Compensation Hub

Compensation Hub is a web application for HR teams to manage current employee compensation and understand how compensation is distributed across a multi-country workforce.

The product is designed around a 10,000-employee dataset and focuses on three jobs: finding an employee quickly, managing current compensation, and answering organization-level compensation questions reliably.

## Live Product

[Open Compensation Hub](https://compensation-hub-web-757075627159.asia-south1.run.app)

The application is deployed on Google Cloud Run in India.

## Core Capabilities

- Search and filter employees by name, employee code, country, department, and job title.
- View and update an employee's current annual salary.
- Keep employee compensation in local currency while using USD for cross-country analytics.
- View employee count, total annual payroll, average annual salary, and compensation breakdowns.
- Ask compensation questions in natural language, including follow-ups, through **Ask Compensation**.

## Compensation Model

Employee salary is stored in local currency.

Organization-wide monetary analytics are normalized to USD using deterministic seeded exchange rates. This keeps cross-country comparisons meaningful and results reproducible without making core product behavior depend on a live FX service.

The MVP manages current compensation only. Salary history, payroll processing, approval workflows, and broader HR lifecycle features are outside the current scope.

## Ask Compensation

If Compensation Hub stores the data a question needs, Ask Compensation derives the answer from that data. If it does not, Ask Compensation says which data is missing instead of guessing.

```text
HR question (+ earlier questions in the conversation)
    |
    v
LLM
    |
    v
Structured read-only query
    |
    v
Validation against the stored fields and data
    |
    v
PostgreSQL (read-only transaction)
    |
    v
Exact result
```

Questions are not matched against a fixed list. The model expresses each question as a query over the stored fields (filters, employee rows, counts, totals, averages, medians, minimums and maximums, grouping, shares, differences, and currency conversion with the seeded rates), and the backend validates it before running it. Follow-up questions such as "Convert that to INR" refine the previous question.

The LLM interprets intent; it is not the source of truth. It does not receive database credentials or employee records, does not write SQL, cannot change data, and does not calculate or phrase the figures in an answer.

## Architecture

```text
Browser
   |
   v
Next.js + TypeScript
   |
   | server-side REST / JSON
   v
FastAPI + Python
   |
   +----------------------+
   |                      |
   v                      v
PostgreSQL             Gemini API
```

The browser interacts with the Next.js application; backend API calls stay server-side in the frontend. The backend is a modular monolith. Product rules, validation, analytics, currency normalization, persistence, and Ask Compensation orchestration stay in the backend, while the frontend owns presentation and user interaction.

## Technology

| Area | Technology |
| --- | --- |
| Frontend | Next.js, React, TypeScript |
| Backend | Python 3.12, FastAPI, Pydantic |
| Data access | SQLAlchemy 2, Psycopg |
| Migrations | Alembic |
| Database | PostgreSQL |
| Ask Compensation provider | Google Gemini |
| Backend environment | uv |
| Frontend package manager | npm |

## Repository Structure

```text
Compensation-Hub/
├── frontend/               # Next.js application (Dockerfile included)
├── backend/                # FastAPI application (Dockerfile, Alembic migrations, tests)
│   └── src/
│       └── compensation_hub/
├── docs/
│   ├── requirements.md
│   ├── decisions.md
│   ├── architecture.md
│   ├── ai-usage.md
│   └── project-plan.md
├── docker/                 # PostgreSQL init script for the local container stack
├── .github/workflows/      # Continuous integration
├── compose.yaml            # Local PostgreSQL and full container stack
├── AGENTS.md
├── CLAUDE.md
└── README.md
```

## Local Development

### Prerequisites

- Node.js and npm
- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- PostgreSQL 16, either through Docker Compose (below) or an existing local server

### PostgreSQL

The repository includes a Docker Compose service for local PostgreSQL:

```bash
docker compose up -d postgres
```

It creates the `compensation_hub` development database and a separate `compensation_hub_test` database for the automated test suite, both owned by the `compensation_hub` role with password `compensation_hub`.

If you use your own PostgreSQL server instead, create the two databases yourself and point `DATABASE_URL` and `TEST_DATABASE_URL` at them.

### Backend

```bash
cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m compensation_hub.seed
uv run uvicorn compensation_hub.main:app --reload
```

`.env.example` documents every backend environment variable. The API reads `DATABASE_URL` at startup.

Ask Compensation uses the Gemini API through the official `google-genai` SDK. Set `GEMINI_API_KEY` (and optionally `GEMINI_MODEL`) in `.env` to enable it. Without a key the API answers `POST /analytics/ask` with `503` and a clear message, and every other feature keeps working.

The seed command loads the deterministic dataset of 10,000 employees, their current compensation, and the exchange rates. It refuses to run against a database that already contains employees; pass `--reset` to truncate the MVP tables and load the same dataset again.

The API is available at `http://localhost:8000`.

The health endpoint is:

```text
GET /health
```

### Backend checks

```bash
cd backend
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

PostgreSQL integration tests run only when `TEST_DATABASE_URL` is set, either in `.env` or in the environment. Without it they are skipped and only the pure unit tests run. The test database is migrated from scratch and its tables are truncated between tests, so it must never point at the development database.

Routine tests never call the LLM provider; the Ask Compensation tests use a mocked planner. A small live evaluation of representative questions runs only on request and needs `GEMINI_API_KEY`:

```bash
uv run pytest -m live
```

### Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

The frontend is available at `http://localhost:3000` and needs the API running. `API_BASE_URL` (default `http://localhost:8000`) is read only on the server: page data and product actions reach the backend through server-side code, so the browser never calls the API directly.

### Frontend checks

```bash
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

### Container stack

`compose.yaml` also defines `backend` and `frontend` services built from the two Dockerfiles, so the whole product can run in containers:

```bash
docker compose up --build -d
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m compensation_hub.seed
```

The frontend is then at `http://localhost:3000` and the API at `http://localhost:8000`. Set `GEMINI_API_KEY` in a root `.env` file next to `compose.yaml` to enable Ask Compensation in the container stack; it is optional.

### Continuous integration

GitHub Actions runs the backend checks against a PostgreSQL service and the frontend checks on every push to `main` and every pull request (`.github/workflows/ci.yml`). CI has no LLM credentials; the Ask Compensation tests use a mocked planner and the live evaluation is excluded.


## Deployment

The product is deployed in India:

| Component | Where |
| --- | --- |
| Frontend | Cloud Run `compensation-hub-web`, `asia-south1` — https://compensation-hub-web-757075627159.asia-south1.run.app |
| Backend | Cloud Run `compensation-hub-api`, `asia-south1` — https://compensation-hub-api-757075627159.asia-south1.run.app |
| Database | Supabase PostgreSQL, `ap-south-1`, via the session-mode pooler |

Google Cloud project: `compensation-hub-mvp`. Images are built by Cloud Build from the repository Dockerfiles into Artifact Registry (`asia-south1-docker.pkg.dev/compensation-hub-mvp/compensation-hub`). `DATABASE_URL` and `GEMINI_API_KEY` live in Secret Manager and are mounted into the backend service, which runs as the `compensation-hub-api` service account.

To ship a new version (from the repository root, with `gcloud` authenticated on the project):

```bash
gcloud builds submit backend --tag asia-south1-docker.pkg.dev/compensation-hub-mvp/compensation-hub/api:$(git rev-parse --short HEAD) --region asia-south1 --project compensation-hub-mvp
gcloud run deploy compensation-hub-api --image asia-south1-docker.pkg.dev/compensation-hub-mvp/compensation-hub/api:$(git rev-parse --short HEAD) --region asia-south1 --project compensation-hub-mvp
gcloud builds submit frontend --tag asia-south1-docker.pkg.dev/compensation-hub-mvp/compensation-hub/web:$(git rev-parse --short HEAD) --region asia-south1 --project compensation-hub-mvp
gcloud run deploy compensation-hub-web --image asia-south1-docker.pkg.dev/compensation-hub-mvp/compensation-hub/web:$(git rev-parse --short HEAD) --region asia-south1 --project compensation-hub-mvp
```

Existing service settings (secrets, environment variables, service accounts) are kept across deploys. Migrations run against the deployed database from a machine with the connection string in `DATABASE_URL`:

```bash
cd backend
uv run alembic upgrade head
```

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
- Use the language model for interpretation, not authoritative calculation.
- Keep large-dataset operations bounded and database-backed.
- Prefer simple architecture over speculative infrastructure.
- Add complexity only when a product, performance, or operational need justifies it.
- Keep product behavior, documentation, tests, and production reality aligned as the system evolves.
