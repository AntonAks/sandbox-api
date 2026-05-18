from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DriverMonthlyMetrics(Base):
    __tablename__ = "driver_monthly_metrics"

    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.driver_id"), nullable=False)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    trips_completed: Mapped[int] = mapped_column(nullable=False)
    total_miles: Mapped[int] = mapped_column(nullable=False)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    average_mpg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    total_fuel_gallons: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    on_time_delivery_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    average_idle_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)

    __table_args__ = (PrimaryKeyConstraint("driver_id", "month", name="pk_driver_monthly_metrics"),)


class TruckUtilizationMetrics(Base):
    __tablename__ = "truck_utilization_metrics"

    truck_id: Mapped[int] = mapped_column(ForeignKey("trucks.truck_id"), nullable=False)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    trips_completed: Mapped[int] = mapped_column(nullable=False)
    total_miles: Mapped[int] = mapped_column(nullable=False)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    average_mpg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    maintenance_events: Mapped[int] = mapped_column(nullable=False)
    maintenance_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    downtime_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    utilization_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("truck_id", "month", name="pk_truck_utilization_metrics"),
    )
