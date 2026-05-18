"""make optional FK columns nullable to match CSV data

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-17

trips.driver_id, trips.truck_id, trips.trailer_id — occasionally absent in source data
fuel_purchases.driver_id, fuel_purchases.truck_id — frequently absent in source data
safety_incidents.driver_id, safety_incidents.truck_id — occasionally absent in source data
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("trips", "driver_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("trips", "truck_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("trips", "trailer_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("fuel_purchases", "driver_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("fuel_purchases", "truck_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("safety_incidents", "driver_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("safety_incidents", "truck_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("safety_incidents", "truck_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("safety_incidents", "driver_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("fuel_purchases", "truck_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("fuel_purchases", "driver_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("trips", "trailer_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("trips", "truck_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("trips", "driver_id", existing_type=sa.Integer(), nullable=False)
