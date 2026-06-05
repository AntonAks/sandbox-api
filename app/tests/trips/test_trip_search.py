"""Behavior + performance tests for POST /trips/search (search_trips).

Strategy: all data is seeded under synthetic high IDs (99xxx) and every query
filters by our synthetic driver_ids, so these tests are isolated from whatever
else lives in the DB (CSV seed uses ids 1..150 for drivers).

- Correctness tests hit the real endpoint and lock in filter/pagination/total
  behavior (regression safety net for the refactor).
- test_search_query_count_is_bounded is the driver: it fails on the N+1
  implementation (queries scale with matched rows) and passes once filtering,
  pagination and eager-loading move into SQL.
"""

from datetime import date
from decimal import Decimal

import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config import settings
from src.models import Customer, Driver, Load, Route, Trip, Truck
from src.trips.service import search_trips

# --- synthetic ids ----------------------------------------------------------
DRV_A = 99001
DRV_B = 99002
TRUCK_A = 99001
CUST = 99001
ROUTE_TX = 99001
ROUTE_CA = 99002


def _trip(trip_id, load_id, driver_id, truck_id, day, distance):
    return Trip(
        trip_id=trip_id,
        load_id=load_id,
        driver_id=driver_id,
        truck_id=truck_id,
        trailer_id=None,
        dispatch_date=date(2024, 3, day),
        actual_distance_miles=distance,
        actual_duration_hours=Decimal("10.0"),
        fuel_gallons_used=Decimal("80.0"),
        average_mpg=Decimal("6.5"),
        idle_time_hours=Decimal("1.0"),
        trip_status="COMPLETED",
    )


def _load(load_id, route_id, status):
    return Load(
        load_id=load_id,
        customer_id=CUST,
        route_id=route_id,
        load_date=date(2024, 3, 1),
        load_type="DRY_VAN",
        weight_lbs=20000,
        pieces=10,
        revenue=Decimal("1000.00"),
        fuel_surcharge=Decimal("100.00"),
        accessorial_charges=Decimal("0.00"),
        load_status=status,
        booking_type="CONTRACT",
    )


@pytest_asyncio.fixture(loop_scope="session")
async def seed_search_data(db_session):
    """Idempotently seed the synthetic search dataset."""
    exists = (
        await db_session.execute(select(Driver.driver_id).where(Driver.driver_id == DRV_A))
    ).scalar_one_or_none()
    if exists is not None:
        return

    db_session.add_all(
        [
            Route(
                route_id=ROUTE_TX,
                origin_city="Houston",
                origin_state="TX",
                destination_city="Dallas",
                destination_state="TX",
                typical_distance_miles=240,
                base_rate_per_mile=Decimal("2.0000"),
                fuel_surcharge_rate=Decimal("0.2000"),
                typical_transit_days=1,
            ),
            Route(
                route_id=ROUTE_CA,
                origin_city="Oakland",
                origin_state="CA",
                destination_city="Los Angeles",
                destination_state="CA",
                typical_distance_miles=370,
                base_rate_per_mile=Decimal("2.5000"),
                fuel_surcharge_rate=Decimal("0.2500"),
                typical_transit_days=1,
            ),
            Customer(
                customer_id=CUST,
                customer_name="Acme Test Co",
                customer_type="SHIPPER",
                credit_terms_days=30,
                primary_freight_type="DRY_VAN",
                account_status="ACTIVE",
                contract_start_date=date(2023, 1, 1),
                annual_revenue_potential=Decimal("500000.00"),
            ),
            Driver(
                driver_id=DRV_A,
                first_name="Test",
                last_name="Driverone",
                hire_date=date(2020, 1, 1),
                termination_date=None,
                license_number="LIC99001",
                license_state="TX",
                date_of_birth=date(1980, 1, 1),
                home_terminal="Houston",
                employment_status="ACTIVE",
                cdl_class="A",
                years_experience=10,
            ),
            Driver(
                driver_id=DRV_B,
                first_name="Test",
                last_name="Drivertwo",
                hire_date=date(2020, 1, 1),
                termination_date=None,
                license_number="LIC99002",
                license_state="TX",
                date_of_birth=date(1981, 1, 1),
                home_terminal="Houston",
                employment_status="ACTIVE",
                cdl_class="A",
                years_experience=9,
            ),
            Truck(
                truck_id=TRUCK_A,
                unit_number="T99001",
                make="Freightliner",
                model_year=2021,
                vin="VIN9900100000001",
                acquisition_date=date(2021, 1, 1),
                acquisition_mileage=0,
                fuel_type="Diesel",
                tank_capacity_gallons=200,
                status="ACTIVE",
                home_terminal="Houston",
            ),
        ]
    )

    # Dataset A — 6 precise trips for driver A. (load_id, route, status) then trip.
    a_specs = [
        (99001, 99001, ROUTE_TX, "DELIVERED", 1, 500, TRUCK_A),
        (99002, 99002, ROUTE_CA, "DELIVERED", 2, 800, TRUCK_A),
        (99003, 99003, ROUTE_TX, "IN_TRANSIT", 3, 200, TRUCK_A),
        (99004, 99004, ROUTE_TX, "DELIVERED", 4, 1000, None),
        (99005, 99005, ROUTE_CA, "IN_TRANSIT", 5, 600, TRUCK_A),
        (99006, 99006, ROUTE_TX, "DELIVERED", 6, 300, TRUCK_A),
    ]
    for trip_id, load_id, route, status, day, dist, truck in a_specs:
        db_session.add(_load(load_id, route, status))
        db_session.add(_trip(trip_id, load_id, DRV_A, truck, day, dist))

    # Dataset B — 15 TX/DELIVERED trips for driver B (query-count workload).
    for i in range(15):
        load_id = 99100 + i
        db_session.add(_load(load_id, ROUTE_TX, "DELIVERED"))
        db_session.add(_trip(99100 + i, load_id, DRV_B, TRUCK_A, (i % 28) + 1, 400 + i))

    await db_session.commit()


# --- correctness (regression safety net) ------------------------------------


async def _search(authed_client, **body):
    resp = await authed_client.post("/trips/search", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_no_filter_returns_all_for_driver(authed_client, seed_search_data):
    data = await _search(authed_client, driver_ids=[DRV_A], limit=50)
    assert data["total"] == 6
    assert len(data["items"]) == 6


async def test_filter_destination_state(authed_client, seed_search_data):
    data = await _search(authed_client, driver_ids=[DRV_A], destination_state="TX", limit=50)
    assert data["total"] == 4
    assert {i["trip_id"] for i in data["items"]} == {99001, 99003, 99004, 99006}


async def test_filter_load_status(authed_client, seed_search_data):
    data = await _search(authed_client, driver_ids=[DRV_A], load_status="DELIVERED", limit=50)
    assert data["total"] == 4
    assert {i["trip_id"] for i in data["items"]} == {99001, 99002, 99004, 99006}


async def test_filter_destination_and_status_combined(authed_client, seed_search_data):
    data = await _search(
        authed_client, driver_ids=[DRV_A], destination_state="TX", load_status="DELIVERED", limit=50
    )
    assert data["total"] == 3
    assert {i["trip_id"] for i in data["items"]} == {99001, 99004, 99006}


async def test_distance_bounds_inclusive(authed_client, seed_search_data):
    lo = await _search(authed_client, driver_ids=[DRV_A], min_distance=500, limit=50)
    assert lo["total"] == 4
    hi = await _search(authed_client, driver_ids=[DRV_A], max_distance=500, limit=50)
    assert hi["total"] == 3
    both = await _search(
        authed_client, driver_ids=[DRV_A], min_distance=500, max_distance=800, limit=50
    )
    assert both["total"] == 3


async def test_date_bounds_inclusive(authed_client, seed_search_data):
    frm = await _search(authed_client, driver_ids=[DRV_A], date_from="2024-03-04", limit=50)
    assert frm["total"] == 3
    to = await _search(authed_client, driver_ids=[DRV_A], date_to="2024-03-02", limit=50)
    assert to["total"] == 2


async def test_truck_filter_excludes_null_truck(authed_client, seed_search_data):
    data = await _search(authed_client, driver_ids=[DRV_A], truck_ids=[TRUCK_A], limit=50)
    assert data["total"] == 5


async def test_total_is_full_match_not_page_size(authed_client, seed_search_data):
    page = await _search(authed_client, driver_ids=[DRV_A], limit=2, offset=0)
    assert page["total"] == 6
    assert len(page["items"]) == 2


async def test_pagination_is_stable_and_ordered(authed_client, seed_search_data):
    p0 = await _search(authed_client, driver_ids=[DRV_A], limit=2, offset=0)
    p1 = await _search(authed_client, driver_ids=[DRV_A], limit=2, offset=2)
    assert [i["trip_id"] for i in p0["items"]] == [99001, 99002]
    assert [i["trip_id"] for i in p1["items"]] == [99003, 99004]


async def test_item_shape_and_null_fallbacks(authed_client, seed_search_data):
    data = await _search(authed_client, driver_ids=[DRV_A], destination_state="TX", limit=50)
    by_id = {i["trip_id"]: i for i in data["items"]}
    t1 = by_id[99001]
    assert t1["driver_name"] == "Test Driverone"
    assert t1["truck_unit"] == "T99001"
    assert t1["route_summary"] == "Houston, TX → Dallas, TX"
    assert t1["distance_miles"] == 500
    assert by_id[99004]["truck_unit"] == "—"


# --- performance (the RED driver) -------------------------------------------


async def test_search_query_count_is_bounded(seed_search_data):
    """A search over many matching rows must issue a bounded number of queries,
    independent of result-set size. The N+1 implementation fails this."""
    engine = create_async_engine(settings.DATABASE_URL)
    count = 0

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _on_exec(*_args):
        nonlocal count
        count += 1

    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            data = await search_trips(
                session, driver_ids=[DRV_B], destination_state="TX", limit=20, offset=0
            )
    finally:
        await engine.dispose()

    assert data["total"] == 15
    assert count <= 8, f"search issued {count} queries for 15 rows — N+1 not eliminated"
