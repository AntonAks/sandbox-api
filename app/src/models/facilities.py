from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Facility(Base):
    __tablename__ = "facilities"

    facility_id: Mapped[int] = mapped_column(primary_key=True)
    facility_name: Mapped[str] = mapped_column(String(160), nullable=False)
    facility_type: Mapped[str] = mapped_column(String(40), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    dock_doors: Mapped[int] = mapped_column(nullable=False)
    operating_hours: Mapped[str] = mapped_column(String(80), nullable=False)
