from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class FuelPurchase(Base):
    __tablename__ = "fuel_purchases"

    fuel_purchase_id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.trip_id"), nullable=False, index=True)
    truck_id: Mapped[int | None] = mapped_column(
        ForeignKey("trucks.truck_id"), nullable=True, index=True
    )
    driver_id: Mapped[int | None] = mapped_column(
        ForeignKey("drivers.driver_id"), nullable=True, index=True
    )
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    location_city: Mapped[str] = mapped_column(String(80), nullable=False)
    location_state: Mapped[str] = mapped_column(String(2), nullable=False)
    gallons: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    price_per_gallon: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fuel_card_number: Mapped[str] = mapped_column(String(40), nullable=False)

    __table_args__ = (Index("ix_fuel_purchases_purchase_date", "purchase_date"),)
