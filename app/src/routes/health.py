from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from src.db import get_session

router = APIRouter(prefix="/health", tags=["health"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(session: SessionDep) -> JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "db": "unreachable"},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "db": "ok"},
    )
