from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Route(Base):
    __tablename__ = "routes"

    route_id: Mapped[int] = mapped_column(primary_key=True)
    origin_city: Mapped[str] = mapped_column(String(80), nullable=False)
    origin_state: Mapped[str] = mapped_column(String(2), nullable=False)
    destination_city: Mapped[str] = mapped_column(String(80), nullable=False)
    destination_state: Mapped[str] = mapped_column(String(2), nullable=False)
    typical_distance_miles: Mapped[int] = mapped_column(nullable=False)
    base_rate_per_mile: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    fuel_surcharge_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    typical_transit_days: Mapped[int] = mapped_column(nullable=False)
