from datetime import date

from sqlalchemy import Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Truck(Base):
    __tablename__ = "trucks"

    truck_id: Mapped[int] = mapped_column(primary_key=True)
    unit_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    make: Mapped[str] = mapped_column(String(60), nullable=False)
    model_year: Mapped[int] = mapped_column(nullable=False)
    vin: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    acquisition_mileage: Mapped[int] = mapped_column(nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(20), nullable=False)
    tank_capacity_gallons: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    home_terminal: Mapped[str] = mapped_column(String(80), nullable=False)

    __table_args__ = (Index("ix_trucks_status", "status"),)
