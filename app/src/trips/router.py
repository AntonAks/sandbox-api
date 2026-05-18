from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.db import get_session
from src.models import User
from src.trips.schemas import (
    CustomerNested,
    DriverNested,
    FuelSummary,
    LoadNested,
    RouteNested,
    TrailerNested,
    TripDetailResponse,
    TripSearchItem,
    TripSearchRequest,
    TripSearchResponse,
    TruckNested,
)
from src.trips.service import get_trip_detail, search_trips

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("/{trip_id}", response_model=TripDetailResponse)
async def trip_detail(
    trip_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> TripDetailResponse:
    data = await get_trip_detail(session, trip_id)
    trip = data["trip"]
    driver = data["driver"]
    truck = data["truck"]
    trailer = data["trailer"]
    return TripDetailResponse(
        trip_id=trip.trip_id,
        dispatch_date=trip.dispatch_date,
        actual_distance_miles=trip.actual_distance_miles,
        trip_status=trip.trip_status,
        load=LoadNested(
            load_id=data["load"].load_id,
            load_type=data["load"].load_type,
            weight_lbs=data["load"].weight_lbs,
            pieces=data["load"].pieces,
            revenue=data["load"].revenue,
            load_status=data["load"].load_status,
            customer=CustomerNested(
                customer_id=data["customer"].customer_id,
                customer_name=data["customer"].customer_name,
            ),
        ),
        driver=DriverNested(
            driver_id=driver.driver_id,
            name=f"{driver.first_name} {driver.last_name}",
        )
        if driver
        else None,
        truck=TruckNested(
            truck_id=truck.truck_id,
            unit_number=truck.unit_number,
        )
        if truck
        else None,
        trailer=TrailerNested(
            trailer_id=trailer.trailer_id,
            trailer_number=trailer.trailer_number,
        )
        if trailer
        else None,
        route=RouteNested(
            origin_city=data["route"].origin_city,
            origin_state=data["route"].origin_state,
            destination_city=data["route"].destination_city,
            destination_state=data["route"].destination_state,
        ),
        fuel_summary=FuelSummary(**data["fuel"]),
        delivery_events_count=data["events_count"],
    )


@router.post("/search", response_model=TripSearchResponse)
async def trips_search(
    body: TripSearchRequest,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> TripSearchResponse:
    data = await search_trips(
        session,
        driver_ids=body.driver_ids,
        truck_ids=body.truck_ids,
        load_status=body.load_status,
        date_from=body.date_from,
        date_to=body.date_to,
        destination_state=body.destination_state,
        min_distance=body.min_distance,
        max_distance=body.max_distance,
        limit=body.limit,
        offset=body.offset,
    )
    return TripSearchResponse(
        total=data["total"],
        items=[TripSearchItem(**i) for i in data["items"]],
    )
