from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.db import wait_for_db
from src.logging import configure_logging
from src.middleware import RequestIDMiddleware
from src.routes import health


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    await wait_for_db()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)
app.include_router(health.router)

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
