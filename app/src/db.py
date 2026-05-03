import asyncio
from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql import text

from src.config import settings

logger = structlog.get_logger()

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=5,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def wait_for_db(retries: int = 5, base_delay: float = 1.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("db_ready", attempt=attempt)
            return
        except Exception as exc:
            if attempt == retries:
                logger.error("db_unreachable", attempts=attempt, error=str(exc))
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "db_not_ready",
                attempt=attempt,
                retries=retries,
                retry_in_s=delay,
                error=str(exc),
            )
            await asyncio.sleep(delay)
