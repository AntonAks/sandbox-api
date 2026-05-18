from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DeliveryEvent(Base):
    __tablename__ = "delivery_events"

    event_id: Mapped[int] = mapped_column(primary_key=True)
    load_id: Mapped[int] = mapped_column(ForeignKey("loads.load_id"), nullable=False, index=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.trip_id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    facility_id: Mapped[int] = mapped_column(
        ForeignKey("facilities.facility_id"), nullable=False, index=True
    )
    scheduled_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    actual_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    detention_minutes: Mapped[int] = mapped_column(nullable=False)
    on_time_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    location_city: Mapped[str] = mapped_column(String(80), nullable=False)
    location_state: Mapped[str] = mapped_column(String(2), nullable=False)

    __table_args__ = (Index("ix_delivery_events_event_type", "event_type"),)
