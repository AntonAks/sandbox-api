"""drop unique constraint on trailers.trailer_number — CSV data has duplicates

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-17

The source dataset contains 4 pairs of trailers that share the same trailer_number,
making the UNIQUE constraint unloadable via COPY. The constraint is removed so the
CSV data can be seeded as-is.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("trailers_trailer_number_key", "trailers", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("trailers_trailer_number_key", "trailers", ["trailer_number"])
