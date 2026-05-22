"""trips perf indexes

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-22

Adds dispatch_date index for date-range trip searches and composite
(driver_id, dispatch_date) for driver-scoped queries.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_trips_dispatch_date", "trips", ["dispatch_date"])
    op.create_index(
        "ix_trips_driver_id_dispatch_date",
        "trips",
        ["driver_id", "dispatch_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_trips_driver_id_dispatch_date", table_name="trips")
    op.drop_index("ix_trips_dispatch_date", table_name="trips")
