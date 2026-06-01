from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.dashboard import store
from src.dashboard.seed_check import seed_check
from src.db import get_session

router = APIRouter(tags=["dashboard"])

_INDEX_HTML = Path(__file__).parent / "templates" / "index.html"


@router.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(_INDEX_HTML, media_type="text/html")


@router.get("/dashboard/stats")
async def stats() -> dict[str, dict[str, int]]:
    return store.read_merged()


@router.get("/dashboard/seed-check")
async def seed_check_report(session: AsyncSession = Depends(get_session)) -> dict:
    return await seed_check(session)
