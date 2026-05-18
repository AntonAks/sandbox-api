from datetime import date

from pydantic import BaseModel


class UpcomingLoadItem(BaseModel):
    load_id: int
    customer_name: str
    route_summary: str
    weight_lbs: int
    load_status: str
    load_date: date
