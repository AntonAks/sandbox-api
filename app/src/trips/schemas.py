from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CustomerNested(BaseModel):
    customer_id: int
    customer_name: str


class LoadNested(BaseModel):
    load_id: int
    load_type: str
    weight_lbs: int
    pieces: int
    revenue: Decimal
    load_status: str
    customer: CustomerNested


class DriverNested(BaseModel):
    driver_id: int
    name: str


class TruckNested(BaseModel):
    truck_id: int
    unit_number: str


class TrailerNested(BaseModel):
    trailer_id: int
    trailer_number: str


class RouteNested(BaseModel):
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str


class FuelSummary(BaseModel):
    purchases_count: int
    total_gallons: Decimal
    total_cost: Decimal


class TripDetailResponse(BaseModel):
    trip_id: int
    dispatch_date: date
    actual_distance_miles: int
    trip_status: str
    load: LoadNested
    driver: DriverNested | None
    truck: TruckNested | None
    trailer: TrailerNested | None
    route: RouteNested
    fuel_summary: FuelSummary
    delivery_events_count: int


class TripSearchRequest(BaseModel):
    driver_ids: list[int] | None = None
    truck_ids: list[int] | None = None
    load_status: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    destination_state: str | None = None
    min_distance: int | None = None
    max_distance: int | None = None
    limit: int = 20
    offset: int = 0


class TripSearchItem(BaseModel):
    trip_id: int
    dispatch_date: date
    driver_name: str
    truck_unit: str
    route_summary: str
    distance_miles: int
    trip_status: str


class TripSearchResponse(BaseModel):
    total: int
    items: list[TripSearchItem]
