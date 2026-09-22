from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from compensation_hub.analytics.router import router as analytics_router
from compensation_hub.analytics.service import MissingFxRateError
from compensation_hub.compensation.router import router as compensation_router
from compensation_hub.compensation.service import UnsupportedCurrencyError
from compensation_hub.core.config import get_settings
from compensation_hub.db.session import create_database_engine, create_session_factory
from compensation_hub.employees.router import router as employees_router
from compensation_hub.employees.service import EmployeeNotFoundError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = create_database_engine(str(settings.database_url))
    app.state.session_factory = create_session_factory(engine)
    try:
        yield
    finally:
        engine.dispose()


def employee_not_found(_: Request, error: EmployeeNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(error)})


def unsupported_currency(_: Request, error: UnsupportedCurrencyError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(error)})


def missing_fx_rate(_: Request, error: MissingFxRateError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(error)})


def create_app() -> FastAPI:
    app = FastAPI(title="Compensation Hub API", lifespan=lifespan)

    app.add_exception_handler(EmployeeNotFoundError, employee_not_found)  # type: ignore[arg-type]
    app.add_exception_handler(UnsupportedCurrencyError, unsupported_currency)  # type: ignore[arg-type]
    app.add_exception_handler(MissingFxRateError, missing_fx_rate)  # type: ignore[arg-type]

    app.include_router(employees_router)
    app.include_router(compensation_router)
    app.include_router(analytics_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "compensation-hub-api"}

    return app


app = create_app()
