from datetime import date

from pydantic import BaseModel, ConfigDict


class DriverListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    driver_id: int
    first_name: str
    last_name: str
    employment_status: str
    home_terminal: str
    years_experience: int
    cdl_class: str
    hire_date: date


class DashboardTrip(BaseModel):
    trip_id: int
    dispatch_date: date
    customer_name: str
    route_summary: str
    distance_miles: int
    on_time: bool | None


class DashboardMetrics(BaseModel):
    trips_completed: int
    total_miles: int
    on_time_delivery_rate: float
    average_mpg: float


class DriverDashboardResponse(BaseModel):
    driver: DriverListItem
    recent_trips: list[DashboardTrip]
    current_month_metrics: DashboardMetrics
    open_incidents_count: int
