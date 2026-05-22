from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import (
    DeliveryEvent,
    FuelPurchase,
    Load,
    Route,
    Trip,
)


async def get_trip_detail(session: AsyncSession, trip_id: int) -> dict:
    trip_stmt = (
        select(Trip)
        .where(Trip.trip_id == trip_id)
        .options(
            selectinload(Trip.load).selectinload(Load.customer),
            selectinload(Trip.load).selectinload(Load.route),
            selectinload(Trip.driver),
            selectinload(Trip.truck),
            selectinload(Trip.trailer),
        )
    )
    trip = (await session.execute(trip_stmt)).scalar_one_or_none()
    if trip is None:
        raise HTTPException(status_code=404, detail="trip not found")

    fuel_stmt = select(
        func.count(FuelPurchase.fuel_purchase_id),
        func.coalesce(func.sum(FuelPurchase.gallons), 0),
        func.coalesce(func.sum(FuelPurchase.total_cost), 0),
    ).where(FuelPurchase.trip_id == trip_id)
    purchases_count, total_gallons, total_cost = (await session.execute(fuel_stmt)).one()

    events_count = (
        await session.execute(
            select(func.count(DeliveryEvent.event_id)).where(DeliveryEvent.trip_id == trip_id)
        )
    ).scalar_one()

    return {
        "trip": trip,
        "load": trip.load,
        "customer": trip.load.customer,
        "route": trip.load.route,
        "driver": trip.driver,
        "truck": trip.truck,
        "trailer": trip.trailer,
        "fuel": {
            "purchases_count": int(purchases_count),
            "total_gallons": Decimal(total_gallons),
            "total_cost": Decimal(total_cost),
        },
        "events_count": int(events_count),
    }


async def search_trips(
    session: AsyncSession,
    *,
    driver_ids: list[int] | None = None,
    truck_ids: list[int] | None = None,
    load_status: str | None = None,
    date_from=None,
    date_to=None,
    destination_state: str | None = None,
    min_distance: int | None = None,
    max_distance: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    stmt = select(Trip)

    if load_status is not None or destination_state is not None:
        stmt = stmt.join(Trip.load)
        if load_status is not None:
            stmt = stmt.where(Load.load_status == load_status)
        if destination_state is not None:
            stmt = stmt.join(Load.route).where(Route.destination_state == destination_state)

    if driver_ids:
        stmt = stmt.where(Trip.driver_id.in_(driver_ids))
    if truck_ids:
        stmt = stmt.where(Trip.truck_id.in_(truck_ids))
    if date_from is not None:
        stmt = stmt.where(Trip.dispatch_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Trip.dispatch_date <= date_to)
    if min_distance is not None:
        stmt = stmt.where(Trip.actual_distance_miles >= min_distance)
    if max_distance is not None:
        stmt = stmt.where(Trip.actual_distance_miles <= max_distance)

    total = int(
        (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    )

    page_stmt = (
        stmt.options(
            selectinload(Trip.load).selectinload(Load.route),
            selectinload(Trip.driver),
            selectinload(Trip.truck),
        )
        .order_by(Trip.trip_id)
        .limit(limit)
        .offset(offset)
    )
    trips = list((await session.execute(page_stmt)).scalars().all())

    items = [
        {
            "trip_id": t.trip_id,
            "dispatch_date": t.dispatch_date,
            "driver_name": f"{t.driver.first_name} {t.driver.last_name}" if t.driver else "—",
            "truck_unit": t.truck.unit_number if t.truck else "—",
            "route_summary": (
                f"{t.load.route.origin_city}, {t.load.route.origin_state} → "
                f"{t.load.route.destination_city}, {t.load.route.destination_state}"
            ),
            "distance_miles": t.actual_distance_miles,
            "trip_status": t.trip_status,
        }
        for t in trips
    ]

    return {"total": total, "items": items}
