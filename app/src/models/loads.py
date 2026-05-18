from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Load(Base):
    __tablename__ = "loads"

    load_id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.customer_id"), nullable=False, index=True
    )
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.route_id"), nullable=False, index=True)
    load_date: Mapped[date] = mapped_column(Date, nullable=False)
    load_type: Mapped[str] = mapped_column(String(40), nullable=False)
    weight_lbs: Mapped[int] = mapped_column(nullable=False)
    pieces: Mapped[int] = mapped_column(nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fuel_surcharge: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    accessorial_charges: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    load_status: Mapped[str] = mapped_column(String(20), nullable=False)
    booking_type: Mapped[str] = mapped_column(String(20), nullable=False)

    customer: Mapped["Customer"] = relationship()
    route: Mapped["Route"] = relationship()

    __table_args__ = (
        Index("ix_loads_load_date", "load_date"),
        Index("ix_loads_load_status", "load_status"),
    )
