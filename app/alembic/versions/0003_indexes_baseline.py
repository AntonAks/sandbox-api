"""indexes baseline

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-17

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extras beyond the FK/status indexes already created in 0001.
    # Intentionally excludes composite (driver_id, dispatch_date) on trips —
    # that index is Bug A's fix and lives in a future workshop migration.
    op.create_index(
        "ix_maintenance_records_maintenance_date", "maintenance_records", ["maintenance_date"]
    )
    op.create_index("ix_safety_incidents_incident_date", "safety_incidents", ["incident_date"])


def downgrade() -> None:
    op.drop_index("ix_safety_incidents_incident_date", table_name="safety_incidents")
    op.drop_index("ix_maintenance_records_maintenance_date", table_name="maintenance_records")
