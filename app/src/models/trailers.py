from datetime import date

from sqlalchemy import Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Trailer(Base):
    __tablename__ = "trailers"

    trailer_id: Mapped[int] = mapped_column(primary_key=True)
    trailer_number: Mapped[str] = mapped_column(String(20), nullable=False)
    trailer_type: Mapped[str] = mapped_column(String(40), nullable=False)
    length_feet: Mapped[int] = mapped_column(nullable=False)
    model_year: Mapped[int] = mapped_column(nullable=False)
    vin: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    current_location: Mapped[str] = mapped_column(String(120), nullable=False)

    __table_args__ = (Index("ix_trailers_status", "status"),)
