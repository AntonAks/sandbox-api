from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Customer, DeliveryEvent, Driver, Load, Route, SafetyIncident, Trip


async def list_drivers(
    session: AsyncSession,
    *,
    status: str | None = None,
    terminal: str | None = None,
) -> list[Driver]:
    stmt = select(Driver).order_by(Driver.driver_id)
    if status:
        stmt = stmt.where(Driver.employment_status == status)
    if terminal:
        stmt = stmt.where(Driver.home_terminal == terminal)
    return list((await session.execute(stmt)).scalars().all())


async def get_driver_or_404(session: AsyncSession, driver_id: int) -> Driver:
    driver = await session.get(Driver, driver_id)
    if driver is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="driver not found")
    return driver


async def build_driver_dashboard(
    session: AsyncSession,
    driver_id: int,
    *,
    since: date | None = None,
) -> dict:
    """Builds dashboard payload.

    NOTE: This is the 'naive first implementation'. Performance issues live here.
    """
    driver = await get_driver_or_404(session, driver_id)

    if since is None:
        since = date.today() - timedelta(days=30)

    # Recent trips
    trips_stmt = (
        select(Trip)
        .where((Trip.driver_id == driver_id) & (Trip.dispatch_date >= since))
        .order_by(Trip.dispatch_date.desc())
        .limit(20)
    )
    recent_trips = list((await session.execute(trips_stmt)).scalars().all())

    recent_payload = []
    for t in recent_trips:
        # N+1 on load / customer / route per trip
        load = await session.get(Load, t.load_id)
        customer = await session.get(Customer, load.customer_id)
        route = await session.get(Route, load.route_id)

        # N+1 on events for on_time compute per trip
        events = list(
            (await session.execute(select(DeliveryEvent).where(DeliveryEvent.trip_id == t.trip_id)))
            .scalars()
            .all()
        )
        on_time: bool | None = all(e.on_time_flag for e in events) if events else None

        recent_payload.append(
            {
                "trip_id": t.trip_id,
                "dispatch_date": t.dispatch_date,
                "customer_name": customer.customer_name,
                "route_summary": (
                    f"{route.origin_city}, {route.origin_state} → "
                    f"{route.destination_city}, {route.destination_state}"
                ),
                "distance_miles": t.actual_distance_miles,
                "on_time": on_time,
            }
        )

    # Current month metrics — inline from raw, ignoring driver_monthly_metrics
    today = date.today()
    month_start = today.replace(day=1)
    month_trips_stmt = select(Trip).where(
        (Trip.driver_id == driver_id) & (Trip.dispatch_date >= month_start)
    )
    month_trips = list((await session.execute(month_trips_stmt)).scalars().all())

    total_miles = sum(t.actual_distance_miles for t in month_trips)
    if month_trips:
        avg_mpg = float(sum(t.average_mpg for t in month_trips) / len(month_trips))
    else:
        avg_mpg = 0.0

    on_time_rate = 0.0
    if month_trips:
        events_stmt = select(DeliveryEvent).where(
            DeliveryEvent.trip_id.in_([t.trip_id for t in month_trips])
        )
        all_events = list((await session.execute(events_stmt)).scalars().all())
        if all_events:
            on_time_count = sum(1 for e in all_events if e.on_time_flag)
            on_time_rate = on_time_count / len(all_events)

    incidents_count = (
        await session.execute(
            select(func.count(SafetyIncident.incident_id)).where(
                SafetyIncident.driver_id == driver_id
            )
        )
    ).scalar_one()

    return {
        "driver": driver,
        "recent_trips": recent_payload,
        "current_month_metrics": {
            "trips_completed": len(month_trips),
            "total_miles": total_miles,
            "on_time_delivery_rate": on_time_rate,
            "average_mpg": avg_mpg,
        },
        "open_incidents_count": incidents_count,
    }
