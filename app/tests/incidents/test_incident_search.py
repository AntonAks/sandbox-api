"""Behavior tests for POST /incidents/search (search_incidents).

All data is seeded under synthetic high IDs (98xxx, distinct from the trips
test's 99xxx) and every assertion isolates our rows via truck_ids=[TRUCK]
(every seeded incident shares that truck), so these tests are independent of the
CSV seed (which uses ids 1..) and of the other test modules.
"""

from datetime import date
from decimal import Decimal

import pytest_asyncio
from sqlalchemy import select

from src.models import Customer, Driver, Load, Route, SafetyIncident, Trip, Truck

# --- synthetic ids ----------------------------------------------------------
DRV_A = 98001  # driver on the first three incidents
DRV_B = 98002  # driver on incidents 4 and 5
TRUCK = 98001  # shared by every seeded incident -> the isolation handle
CUST = 98001
ROUTE = 98001
TRIP_A = 98001
TRIP_B = 98002

# incident_id, trip_id, driver_id, (year, month, day), location_state, claim
INCIDENT_SPECS = [
    (98001, TRIP_A, DRV_A, (2024, 1, 10), "TX", "100.00"),
    (98002, TRIP_A, DRV_A, (2024, 2, 10), "TX", "200.00"),
    (98003, TRIP_A, DRV_A, (2024, 3, 10), "CA", "300.00"),
    (98004, TRIP_B, DRV_B, (2024, 4, 10), "CA", "400.00"),
    (98005, TRIP_B, DRV_B, (2024, 5, 10), "TX", "500.00"),
    (98006, TRIP_B, None, (2024, 6, 10), "TX", "600.00"),  # null driver
]


def _trip(trip_id, load_id, driver_id):
    return Trip(
        trip_id=trip_id,
        load_id=load_id,
        driver_id=driver_id,
        truck_id=TRUCK,
        trailer_id=None,
        dispatch_date=date(2024, 1, 1),
        actual_distance_miles=500,
        actual_duration_hours=Decimal("10.0"),
        fuel_gallons_used=Decimal("80.0"),
        average_mpg=Decimal("6.5"),
        idle_time_hours=Decimal("1.0"),
        trip_status="COMPLETED",
    )


def _incident(incident_id, trip_id, driver_id, ymd, state, claim):
    return SafetyIncident(
        incident_id=incident_id,
        trip_id=trip_id,
        truck_id=TRUCK,
        driver_id=driver_id,
        incident_date=date(*ymd),
        incident_type="Moving Violation",
        location_city="Columbus",
        location_state=state,
        at_fault_flag=True,
        injury_flag=False,
        vehicle_damage_cost=Decimal(claim),
        cargo_damage_cost=Decimal("0.00"),
        claim_amount=Decimal(claim),
        preventable_flag=True,
        description="synthetic test incident",
    )


@pytest_asyncio.fixture(loop_scope="session")
async def seed_incident_data(db_session):
    """Idempotently seed the synthetic incident dataset."""
    exists = (
        await db_session.execute(
            select(SafetyIncident.incident_id).where(SafetyIncident.incident_id == 98001)
        )
    ).scalar_one_or_none()
    if exists is not None:
        return

    db_session.add_all(
        [
            Route(
                route_id=ROUTE,
                origin_city="Houston",
                origin_state="TX",
                destination_city="Dallas",
                destination_state="TX",
                typical_distance_miles=240,
                base_rate_per_mile=Decimal("2.0000"),
                fuel_surcharge_rate=Decimal("0.2000"),
                typical_transit_days=1,
            ),
            Customer(
                customer_id=CUST,
                customer_name="Acme Incident Co",
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
                license_number="LIC98001",
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
                license_number="LIC98002",
                license_state="TX",
                date_of_birth=date(1981, 1, 1),
                home_terminal="Houston",
                employment_status="ACTIVE",
                cdl_class="A",
                years_experience=9,
            ),
            Truck(
                truck_id=TRUCK,
                unit_number="T98001",
                make="Freightliner",
                model_year=2021,
                vin="VIN9800100000001",
                acquisition_date=date(2021, 1, 1),
                acquisition_mileage=0,
                fuel_type="Diesel",
                tank_capacity_gallons=200,
                status="ACTIVE",
                home_terminal="Houston",
            ),
        ]
    )

    # trips.load_id is unique, so each trip needs its own load.
    db_session.add(_load_row(98001))
    db_session.add(_load_row(98002))
    db_session.add(_trip(TRIP_A, 98001, DRV_A))
    db_session.add(_trip(TRIP_B, 98002, DRV_B))
    await db_session.flush()
    for spec in INCIDENT_SPECS:
        db_session.add(_incident(*spec))
    await db_session.commit()


def _load_row(load_id):
    return Load(
        load_id=load_id,
        customer_id=CUST,
        route_id=ROUTE,
        load_date=date(2024, 1, 1),
        load_type="DRY_VAN",
        weight_lbs=20000,
        pieces=10,
        revenue=Decimal("1000.00"),
        fuel_surcharge=Decimal("100.00"),
        accessorial_charges=Decimal("0.00"),
        load_status="DELIVERED",
        booking_type="CONTRACT",
    )


async def _search(authed_client, **body):
    resp = await authed_client.post("/incidents/search", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_isolation_handle_returns_all_seeded(authed_client, seed_incident_data):
    data = await _search(authed_client, truck_ids=[TRUCK], limit=50)
    assert data["total"] == 6
    assert {i["incident_id"] for i in data["items"]} == {98001, 98002, 98003, 98004, 98005, 98006}


async def test_filter_driver_ids(authed_client, seed_incident_data):
    data = await _search(authed_client, driver_ids=[DRV_A], limit=50)
    assert data["total"] == 3
    assert {i["incident_id"] for i in data["items"]} == {98001, 98002, 98003}


async def test_empty_driver_ids_matches_nothing(authed_client, seed_incident_data):
    # An explicit [] means "no driver matches", not "ignore the filter".
    data = await _search(authed_client, driver_ids=[], limit=50)
    assert data["total"] == 0
    assert data["items"] == []


async def test_filter_location_state(authed_client, seed_incident_data):
    data = await _search(authed_client, truck_ids=[TRUCK], location_state="CA", limit=50)
    assert data["total"] == 2
    assert {i["incident_id"] for i in data["items"]} == {98003, 98004}


async def test_filter_date_window(authed_client, seed_incident_data):
    data = await _search(
        authed_client,
        truck_ids=[TRUCK],
        date_from="2024-02-01",
        date_to="2024-04-30",
        limit=50,
    )
    assert data["total"] == 3
    assert {i["incident_id"] for i in data["items"]} == {98002, 98003, 98004}


async def test_total_is_full_match_not_page_size(authed_client, seed_incident_data):
    page = await _search(authed_client, truck_ids=[TRUCK], limit=2, offset=0)
    assert page["total"] == 6
    assert len(page["items"]) == 2


async def test_ordering_newest_first_and_pagination_stable(authed_client, seed_incident_data):
    p0 = await _search(authed_client, truck_ids=[TRUCK], limit=2, offset=0)
    p1 = await _search(authed_client, truck_ids=[TRUCK], limit=2, offset=2)
    assert [i["incident_id"] for i in p0["items"]] == [98006, 98005]
    assert [i["incident_id"] for i in p1["items"]] == [98004, 98003]


async def test_null_driver_falls_back_to_dash(authed_client, seed_incident_data):
    data = await _search(authed_client, truck_ids=[TRUCK], limit=50)
    null_row = next(i for i in data["items"] if i["incident_id"] == 98006)
    assert null_row["driver_name"] == "—"
    assert null_row["location"] == "Columbus, TX"
