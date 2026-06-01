"""Admin endpoints — seed CSV data and inspect row counts.

Endpoints require any authenticated user (no separate admin role yet — workshop
sandbox). Seed runs in a FastAPI BackgroundTask, returning immediately; poll
GET /admin/seed-status to see row counts grow.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.db import get_session
from src.domain_tables import DOMAIN_TABLES
from src.scripts.seed_csv import _seed

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/seed-csv", status_code=202)
async def seed_csv(
    background_tasks: BackgroundTasks,
    reset: bool = False,
    _: object = Depends(get_current_user),
) -> dict:
    """Trigger CSV seed from /app/data/*.csv into Postgres via COPY.

    Returns 202 immediately. Seed runs in background — poll GET /admin/seed-status.
    Idempotent: if reset=false and trips table is not empty, the background task
    exits cleanly without rewriting.
    """
    background_tasks.add_task(_seed, reset)
    return {
        "status": "seeding_started",
        "reset": reset,
        "check_progress": "GET /admin/seed-status",
        "expected_total_rows": 549_706,
        "estimated_duration_seconds": 60,
    }


@router.get("/seed-status")
async def seed_status(
    session: AsyncSession = Depends(get_session),
    _: object = Depends(get_current_user),
) -> dict:
    """Row counts per domain table. Useful for watching seed progress."""
    counts: dict[str, int] = {}
    for name, model in DOMAIN_TABLES.items():
        result = await session.execute(select(func.count()).select_from(model))
        counts[name] = result.scalar_one()
    counts["total"] = sum(counts.values())
    return counts
