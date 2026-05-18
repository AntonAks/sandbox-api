from datetime import date as _date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.db import get_session
from src.drivers.schemas import (
    DashboardMetrics,
    DashboardTrip,
    DriverDashboardResponse,
    DriverListItem,
)
from src.drivers.service import build_driver_dashboard, list_drivers
from src.models import User

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.get("", response_model=list[DriverListItem])
async def get_drivers(
    status: str | None = None,
    terminal: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[DriverListItem]:
    drivers = await list_drivers(session, status=status, terminal=terminal)
    return [DriverListItem.model_validate(d) for d in drivers]


@router.get("/{driver_id}/dashboard", response_model=DriverDashboardResponse)
async def driver_dashboard(
    driver_id: int,
    since: _date | None = None,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> DriverDashboardResponse:
    data = await build_driver_dashboard(session, driver_id, since=since)
    return DriverDashboardResponse(
        driver=DriverListItem.model_validate(data["driver"]),
        recent_trips=[DashboardTrip(**t) for t in data["recent_trips"]],
        current_month_metrics=DashboardMetrics(**data["current_month_metrics"]),
        open_incidents_count=data["open_incidents_count"],
    )
