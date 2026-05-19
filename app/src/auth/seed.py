"""Idempotent demo-user seeding from environment settings.

Replaces the static bcrypt hash in migration 0002. Runs on every startup so
rotating ``DEMO_USER_PASSWORD`` (e.g. via a GitHub secret update + redeploy)
takes effect without a new migration.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.security import hash_password
from src.config import settings
from src.models import User


async def ensure_demo_user(session: AsyncSession) -> None:
    user = (
        await session.execute(select(User).where(User.email == settings.DEMO_USER_EMAIL))
    ).scalar_one_or_none()

    hashed = hash_password(settings.DEMO_USER_PASSWORD)
    if user is None:
        session.add(
            User(
                email=settings.DEMO_USER_EMAIL,
                password_hash=hashed,
                display_name="Demo User",
            )
        )
    else:
        # Always sync the hash so password rotation in env takes effect.
        user.password_hash = hashed
    await session.commit()
