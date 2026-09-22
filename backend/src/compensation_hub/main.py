from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from compensation_hub.core.config import get_settings
from compensation_hub.db.session import create_database_engine, create_session_factory


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = create_database_engine(str(settings.database_url))
    app.state.session_factory = create_session_factory(engine)
    try:
        yield
    finally:
        engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Compensation Hub API", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "compensation-hub-api"}

    return app


app = create_app()
