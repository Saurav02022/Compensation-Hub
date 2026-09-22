FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies are installed before the source is copied so they cache independently.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

COPY . /app
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# PORT is provided by hosting platforms such as Cloud Run; 8000 matches local development.
CMD ["sh", "-c", "uvicorn compensation_hub.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
