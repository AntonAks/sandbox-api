from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .drivers import Driver
    from .loads import Load
    from .trailers import Trailer
    from .trucks import Truck


class Trip(Base):
    __tablename__ = "trips"

    trip_id: Mapped[int] = mapped_column(primary_key=True)
    load_id: Mapped[int] = mapped_column(ForeignKey("loads.load_id"), nullable=False, index=True)
    driver_id: Mapped[int | None] = mapped_column(
        ForeignKey("drivers.driver_id"), nullable=True, index=True
    )
    truck_id: Mapped[int | None] = mapped_column(
        ForeignKey("trucks.truck_id"), nullable=True, index=True
    )
    trailer_id: Mapped[int | None] = mapped_column(
        ForeignKey("trailers.trailer_id"), nullable=True, index=True
    )
    dispatch_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_distance_miles: Mapped[int] = mapped_column(nullable=False)
    actual_duration_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    fuel_gallons_used: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    average_mpg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    idle_time_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    trip_status: Mapped[str] = mapped_column(String(20), nullable=False)

    load: Mapped["Load"] = relationship()
    driver: Mapped["Driver"] = relationship()
    truck: Mapped["Truck"] = relationship()
    trailer: Mapped["Trailer"] = relationship()

    __table_args__ = (
        UniqueConstraint("load_id", name="uq_trips_load_id"),
        Index("ix_trips_trip_status", "trip_status"),
    )
