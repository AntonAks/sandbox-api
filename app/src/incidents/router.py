from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.db import get_session
from src.incidents.schemas import (
    IncidentSearchItem,
    IncidentSearchRequest,
    IncidentSearchResponse,
)
from src.incidents.service import search_incidents
from src.models import User

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("/search", response_model=IncidentSearchResponse)
async def incidents_search(
    body: IncidentSearchRequest,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> IncidentSearchResponse:
    data = await search_incidents(
        session,
        driver_ids=body.driver_ids,
        truck_ids=body.truck_ids,
        location_state=body.location_state,
        date_from=body.date_from,
        date_to=body.date_to,
        limit=body.limit,
        offset=body.offset,
    )
    return IncidentSearchResponse(
        total=data["total"],
        items=[IncidentSearchItem(**i) for i in data["items"]],
    )
