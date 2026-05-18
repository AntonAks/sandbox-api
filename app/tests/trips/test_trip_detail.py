import pytest


async def test_trip_detail_returns_full_shape(authed_client, sample_trip_id):
    if sample_trip_id is None:
        pytest.skip("no trips seeded in test DB")
    resp = await authed_client.get(f"/trips/{sample_trip_id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) >= {
        "trip_id",
        "dispatch_date",
        "load",
        "driver",
        "truck",
        "trailer",
        "route",
        "fuel_summary",
        "delivery_events_count",
    }
    # load.customer should be nested
    assert body["load"]["customer"]["customer_id"] > 0


async def test_trip_detail_404_for_unknown(authed_client):
    resp = await authed_client.get("/trips/99999999")
    assert resp.status_code == 404
