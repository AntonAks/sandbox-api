from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TruckUtilizationItem(BaseModel):
    truck_id: int
    unit_number: str
    trips_completed: int
    total_miles: int
    average_mpg: Decimal
    utilization_rate: Decimal
    maintenance_cost: Decimal


class FleetUtilizationResponse(BaseModel):
    month: str
    trucks: list[TruckUtilizationItem]
    data_computed_at: datetime
