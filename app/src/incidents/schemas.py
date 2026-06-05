from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class IncidentSearchRequest(BaseModel):
    driver_ids: list[int] | None = None
    truck_ids: list[int] | None = None
    location_state: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    limit: int = 20
    offset: int = 0


class IncidentSearchItem(BaseModel):
    incident_id: int
    trip_id: int
    incident_date: date
    incident_type: str
    location: str
    driver_name: str
    truck_unit: str
    at_fault_flag: bool
    injury_flag: bool
    claim_amount: Decimal


class IncidentSearchResponse(BaseModel):
    total: int
    items: list[IncidentSearchItem]
