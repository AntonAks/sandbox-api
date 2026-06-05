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
    # One statement: all filters in SQL (joining Load/Route for the relational ones),
    # related rows eager-loaded, and pagination + count done by the DB. The driver_id +
    # dispatch_date filter is backed by ix_trips_driver_id_dispatch_date (migration 0006).
    stmt = (
        select(Trip)
        .join(Load, Trip.load_id == Load.load_id)
        .join(Route, Load.route_id == Route.route_id)
        .options(
            selectinload(Trip.load).selectinload(Load.route),
            selectinload(Trip.driver),
            selectinload(Trip.truck),
        )
    )
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
    if destination_state:
        stmt = stmt.where(Route.destination_state == destination_state)
    if load_status:
        stmt = stmt.where(Load.load_status == load_status)

    total = await session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = (
        (await session.execute(stmt.order_by(Trip.trip_id).limit(limit).offset(offset)))
        .scalars()
        .all()
    )

    items = []
    for t in rows:
        route = t.load.route
        items.append(
            {
                "trip_id": t.trip_id,
                "dispatch_date": t.dispatch_date,
                "driver_name": (f"{t.driver.first_name} {t.driver.last_name}" if t.driver else "—"),
                "truck_unit": t.truck.unit_number if t.truck else "—",
                "route_summary": (
                    f"{route.origin_city}, {route.origin_state} → "
                    f"{route.destination_city}, {route.destination_state}"
                ),
                "distance_miles": t.actual_distance_miles,
                "trip_status": t.trip_status,
            }
        )

    return {"total": total or 0, "items": items}
