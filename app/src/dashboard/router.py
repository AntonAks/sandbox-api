from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from src.dashboard import store

router = APIRouter(tags=["dashboard"])

_INDEX_HTML = Path(__file__).parent / "templates" / "index.html"


@router.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(_INDEX_HTML, media_type="text/html")


@router.get("/dashboard/stats")
async def stats() -> dict[str, dict[str, int]]:
    return store.read_merged()
