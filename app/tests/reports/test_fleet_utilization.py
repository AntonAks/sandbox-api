async def test_fleet_utilization_returns_month_payload(authed_client, sample_truck_metric):
    resp = await authed_client.get("/reports/fleet-utilization?month=2024-06")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["month"] == "2024-06"
    assert "trucks" in body
    assert "data_computed_at" in body
