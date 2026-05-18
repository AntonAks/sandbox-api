from datetime import date

from sqlalchemy import Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Driver(Base):
    __tablename__ = "drivers"

    driver_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    license_number: Mapped[str] = mapped_column(String(40), nullable=False)
    license_state: Mapped[str] = mapped_column(String(2), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    home_terminal: Mapped[str] = mapped_column(String(80), nullable=False)
    employment_status: Mapped[str] = mapped_column(String(20), nullable=False)
    cdl_class: Mapped[str] = mapped_column(String(2), nullable=False)
    years_experience: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (Index("ix_drivers_employment_status", "employment_status"),)
