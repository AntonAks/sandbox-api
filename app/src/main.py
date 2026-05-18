from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.admin.router import router as admin_router
from src.auth.router import router as auth_router
from src.db import wait_for_db
from src.drivers.router import router as drivers_router
from src.health.router import router as health_router
from src.loads.router import router as loads_router
from src.logging import configure_logging
from src.middleware import RequestIDMiddleware
from src.reports.router import router as reports_router
from src.trips.router import router as trips_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    await wait_for_db()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(drivers_router)
app.include_router(trips_router)
app.include_router(loads_router)
app.include_router(reports_router)
app.include_router(admin_router)

logger = structlog.get_logger()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
