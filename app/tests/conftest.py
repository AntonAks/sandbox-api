import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/sandbox_api")
os.environ.setdefault("LOG_LEVEL", "WARNING")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from src.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
