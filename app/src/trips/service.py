from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import (
    DeliveryEvent,
    Driver,
    FuelPurchase,
    Load,
    Route,
    Trip,
    Truck,
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
    """Search trips with filters. Naive implementation — Bug A lives here."""
    stmt = select(Trip)
    if driver_ids:
        stmt = stmt.where(Trip.driver_id.in_(driver_ids))
    if truck_ids:
        stmt = stmt.where(Trip.truck_id.in_(truck_ids))
    if date_from is not None:
        stmt = stmt.where(Trip.dispatch_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Trip.dispatch_date <= date_to)

    trips = list((await session.execute(stmt)).scalars().all())

    # Python-side filter for distance
    if min_distance is not None:
        trips = [t for t in trips if t.actual_distance_miles >= min_distance]
    if max_distance is not None:
        trips = [t for t in trips if t.actual_distance_miles <= max_distance]

    # destination_state / load_status via per-trip db.get
    if destination_state or load_status:
        filtered = []
        for t in trips:
            load = await session.get(Load, t.load_id)
            route = await session.get(Route, load.route_id)
            if destination_state and route.destination_state != destination_state:
                continue
            if load_status and load.load_status != load_status:
                continue
            filtered.append(t)
        trips = filtered

    total = len(trips)
    page = trips[offset : offset + limit]

    # Result enrichment — N+1 (driver, truck, load, route per item)
    items = []
    for t in page:
        load = await session.get(Load, t.load_id)
        route = await session.get(Route, load.route_id)
        driver = await session.get(Driver, t.driver_id) if t.driver_id else None
        truck = await session.get(Truck, t.truck_id) if t.truck_id else None
        items.append(
            {
                "trip_id": t.trip_id,
                "dispatch_date": t.dispatch_date,
                "driver_name": f"{driver.first_name} {driver.last_name}" if driver else "—",
                "truck_unit": truck.unit_number if truck else "—",
                "route_summary": (
                    f"{route.origin_city}, {route.origin_state} → "
                    f"{route.destination_city}, {route.destination_state}"
                ),
                "distance_miles": t.actual_distance_miles,
                "trip_status": t.trip_status,
            }
        )

    return {"total": total, "items": items}
