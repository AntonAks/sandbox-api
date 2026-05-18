from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    maintenance_id: Mapped[int] = mapped_column(primary_key=True)
    truck_id: Mapped[int] = mapped_column(ForeignKey("trucks.truck_id"), nullable=False, index=True)
    maintenance_date: Mapped[date] = mapped_column(Date, nullable=False)
    maintenance_type: Mapped[str] = mapped_column(String(60), nullable=False)
    odometer_reading: Mapped[int] = mapped_column(nullable=False)
    labor_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    labor_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    parts_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    facility_location: Mapped[str] = mapped_column(String(120), nullable=False)
    downtime_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    service_description: Mapped[str] = mapped_column(String(255), nullable=False)
