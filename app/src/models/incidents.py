from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SafetyIncident(Base):
    __tablename__ = "safety_incidents"

    incident_id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.trip_id"), nullable=False, index=True)
    truck_id: Mapped[int | None] = mapped_column(
        ForeignKey("trucks.truck_id"), nullable=True, index=True
    )
    driver_id: Mapped[int | None] = mapped_column(
        ForeignKey("drivers.driver_id"), nullable=True, index=True
    )
    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    incident_type: Mapped[str] = mapped_column(String(60), nullable=False)
    location_city: Mapped[str] = mapped_column(String(80), nullable=False)
    location_state: Mapped[str] = mapped_column(String(2), nullable=False)
    at_fault_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    injury_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    vehicle_damage_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cargo_damage_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    claim_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    preventable_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
