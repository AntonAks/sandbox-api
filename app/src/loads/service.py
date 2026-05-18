from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Load


async def list_upcoming(session: AsyncSession, *, days: int = 3) -> list[Load]:
    today = date.today()
    end = today + timedelta(days=days)
    stmt = (
        select(Load)
        .where((Load.load_date >= today) & (Load.load_date <= end))
        .order_by(Load.load_date.asc())
        .options(
            selectinload(Load.customer),
            selectinload(Load.route),
        )
    )
    return list((await session.execute(stmt)).scalars().all())
