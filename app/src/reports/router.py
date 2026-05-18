from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.db import get_session
from src.models import User
from src.reports.schemas import FleetUtilizationResponse, TruckUtilizationItem
from src.reports.service import fleet_utilization

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/fleet-utilization", response_model=FleetUtilizationResponse)
async def fleet_utilization_report(
    month: str,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> FleetUtilizationResponse:
    data = await fleet_utilization(session, month=month)
    return FleetUtilizationResponse(
        month=data["month"],
        trucks=[TruckUtilizationItem(**t) for t in data["trucks"]],
        data_computed_at=data["data_computed_at"],
    )
