"""seed demo users

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-17

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DISPATCHER_HASH = "$2b$12$oI9Wp5OazEuLEWIrdb2TuOITAaOxXT9ABhNG81gsLhmPvqB/Rce.u"
VIEWER_HASH = "$2b$12$g1qE2WjT4V.Wwsl9L0H7G.xzpqip3HFxyAPvW9o5l.GX/4d2nu7XW"


def upgrade() -> None:
    users = sa.table(
        "users",
        sa.column("email", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("display_name", sa.String),
    )
    op.bulk_insert(
        users,
        [
            {
                "email": "dispatcher@example.com",
                "password_hash": DISPATCHER_HASH,
                "display_name": "Demo Dispatcher",
            },
            {
                "email": "viewer@example.com",
                "password_hash": VIEWER_HASH,
                "display_name": "Demo Viewer",
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE email IN ('dispatcher@example.com', 'viewer@example.com')")
