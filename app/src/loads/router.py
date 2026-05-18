from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.db import get_session
from src.loads.schemas import UpcomingLoadItem
from src.loads.service import list_upcoming
from src.models import User

router = APIRouter(prefix="/loads", tags=["loads"])


@router.get("/upcoming", response_model=list[UpcomingLoadItem])
async def upcoming(
    days: int = 3,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[UpcomingLoadItem]:
    loads = await list_upcoming(session, days=days)
    return [
        UpcomingLoadItem(
            load_id=load.load_id,
            customer_name=load.customer.customer_name,
            route_summary=(
                f"{load.route.origin_city}, {load.route.origin_state} → "
                f"{load.route.destination_city}, {load.route.destination_state}"
            ),
            weight_lbs=load.weight_lbs,
            load_status=load.load_status,
            load_date=load.load_date,
        )
        for load in loads
    ]
