from calendar import monthrange
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Truck, TruckUtilizationMetrics


async def fleet_utilization(session: AsyncSession, *, month: str) -> dict:
    month_date = date.fromisoformat(f"{month}-01")

    stmt = (
        select(TruckUtilizationMetrics, Truck.unit_number)
        .join(Truck, Truck.truck_id == TruckUtilizationMetrics.truck_id)
        .where(TruckUtilizationMetrics.month == month_date)
        .order_by(TruckUtilizationMetrics.truck_id)
    )
    rows = (await session.execute(stmt)).all()

    trucks = [
        {
            "truck_id": m.truck_id,
            "unit_number": unit_number,
            "trips_completed": m.trips_completed,
            "total_miles": m.total_miles,
            "average_mpg": m.average_mpg,
            "utilization_rate": m.utilization_rate,
            "maintenance_cost": m.maintenance_cost,
        }
        for m, unit_number in rows
    ]

    last_day = monthrange(month_date.year, month_date.month)[1]
    computed_at = datetime(month_date.year, month_date.month, last_day, 23, 55, tzinfo=UTC)

    return {"month": month, "trucks": trucks, "data_computed_at": computed_at}
