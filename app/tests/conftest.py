import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/sandbox_api")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault(
    "JWT_SECRET_KEY", "test-secret-key-not-for-production"
)  # required at import time by Settings()

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from src.auth.security import hash_password  # noqa: E402
from src.config import settings  # noqa: E402
from src.main import app  # noqa: E402
from src.models.users import User  # noqa: E402


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(loop_scope="session")
async def demo_users():
    # Create a fresh engine bound to the current test event loop to avoid
    # cross-loop connection pool issues with the shared module-level engine.
    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        result = await session.execute(select(User).where(User.email == "dispatcher@example.com"))
        if result.scalar_one_or_none() is None:
            dispatcher = User(
                email="dispatcher@example.com",
                password_hash=hash_password("dispatcher123"),
                display_name="Demo Dispatcher",
            )
            session.add(dispatcher)
            await session.commit()
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session():
    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def authed_client(client, demo_users):
    """HTTP client with Authorization header pre-set for the demo dispatcher."""
    login = await client.post(
        "/auth/login",
        json={"email": "dispatcher@example.com", "password": "dispatcher123"},
    )
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    return client


@pytest_asyncio.fixture(loop_scope="session")
async def sample_trip_id(db_session):
    """Return the smallest existing trip_id from seeded data."""
    from sqlalchemy import select

    from src.models import Trip

    return (
        await db_session.execute(select(Trip.trip_id).order_by(Trip.trip_id).limit(1))
    ).scalar_one_or_none()


@pytest_asyncio.fixture(loop_scope="session")
async def sample_truck_metric(db_session):
    """Ensure at least one row exists for truck_id=1, month=2024-06.

    Self-contained: inserts the parent Truck if absent so the fixture works in CI
    where CSV seed has not run.
    """
    from datetime import date
    from decimal import Decimal

    from sqlalchemy import select

    from src.models import Truck, TruckUtilizationMetrics

    truck = (
        await db_session.execute(select(Truck).where(Truck.truck_id == 1))
    ).scalar_one_or_none()
    if truck is None:
        db_session.add(
            Truck(
                truck_id=1,
                unit_number="T1-TEST",
                make="Freightliner",
                model_year=2021,
                vin="VINTEST00000001",
                acquisition_date=date(2021, 1, 1),
                acquisition_mileage=0,
                fuel_type="Diesel",
                tank_capacity_gallons=200,
                status="ACTIVE",
                home_terminal="Atlanta",
            )
        )
        await db_session.commit()

    existing = (
        await db_session.execute(
            select(TruckUtilizationMetrics).where(
                TruckUtilizationMetrics.truck_id == 1,
                TruckUtilizationMetrics.month == date(2024, 6, 1),
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    metric = TruckUtilizationMetrics(
        truck_id=1,
        month=date(2024, 6, 1),
        trips_completed=15,
        total_miles=12000,
        total_revenue=Decimal("30000"),
        average_mpg=Decimal("6.8"),
        maintenance_events=2,
        maintenance_cost=Decimal("500"),
        downtime_hours=Decimal("8"),
        utilization_rate=Decimal("0.65"),
    )
    db_session.add(metric)
    await db_session.commit()
    return metric
