from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Driver, SafetyIncident, Truck


async def search_incidents(
    session: AsyncSession,
    *,
    driver_ids: list[int] | None = None,
    truck_ids: list[int] | None = None,
    location_state: str | None = None,
    date_from=None,
    date_to=None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    # One statement: all filters in SQL, the nullable driver/truck FKs resolved via
    # outerjoin (only the display columns are pulled), and pagination + count done by the
    # DB. The FK and incident_date filters are backed by the ix_safety_incidents_* indexes.
    stmt = (
        select(
            SafetyIncident,
            Driver.first_name,
            Driver.last_name,
            Truck.unit_number,
        )
        .outerjoin(Driver, SafetyIncident.driver_id == Driver.driver_id)
        .outerjoin(Truck, SafetyIncident.truck_id == Truck.truck_id)
    )
    if driver_ids is not None:
        stmt = stmt.where(SafetyIncident.driver_id.in_(driver_ids))
    if truck_ids is not None:
        stmt = stmt.where(SafetyIncident.truck_id.in_(truck_ids))
    if location_state:
        stmt = stmt.where(SafetyIncident.location_state == location_state)
    if date_from is not None:
        stmt = stmt.where(SafetyIncident.incident_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(SafetyIncident.incident_date <= date_to)

    total = await session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = (
        await session.execute(
            stmt.order_by(SafetyIncident.incident_date.desc(), SafetyIncident.incident_id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    items = []
    for incident, first_name, last_name, unit_number in rows:
        items.append(
            {
                "incident_id": incident.incident_id,
                "trip_id": incident.trip_id,
                "incident_date": incident.incident_date,
                "incident_type": incident.incident_type,
                "location": f"{incident.location_city}, {incident.location_state}",
                "driver_name": (f"{first_name} {last_name}" if first_name is not None else "—"),
                "truck_unit": unit_number if unit_number is not None else "—",
                "at_fault_flag": incident.at_fault_flag,
                "injury_flag": incident.injury_flag,
                "claim_amount": incident.claim_amount,
            }
        )

    return {"total": total or 0, "items": items}
