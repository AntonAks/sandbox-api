from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(160), nullable=False)
    customer_type: Mapped[str] = mapped_column(String(40), nullable=False)
    credit_terms_days: Mapped[int] = mapped_column(nullable=False)
    primary_freight_type: Mapped[str] = mapped_column(String(60), nullable=False)
    account_status: Mapped[str] = mapped_column(String(20), nullable=False)
    contract_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    annual_revenue_potential: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
