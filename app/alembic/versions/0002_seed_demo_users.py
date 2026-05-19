"""seed demo users — now a no-op

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-17

Originally this migration inserted hard-coded demo users (dispatcher@example.com,
viewer@example.com) with bcrypt-hashed passwords baked into source. That made
password rotation impossible without a new migration and leaked the password
into git history.

Demo-user seeding now lives at runtime in ``src.auth.seed.ensure_demo_user``
which reads ``DEMO_USER_EMAIL`` and ``DEMO_USER_PASSWORD`` from environment
on every startup (idempotent upsert).

The legacy hard-coded users are removed here so old environments converge to
the new env-driven seed without leftover rows. The upgrade is safe to apply on
fresh DBs (DELETE matches nothing) and on existing prod DBs (legacy rows go
away, lifespan recreates the env-driven one on next boot).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM users WHERE email IN ('dispatcher@example.com', 'viewer@example.com')")


def downgrade() -> None:
    # No-op — we don't re-insert hardcoded creds on downgrade.
    pass
