import json

import pytest

from src.config import settings
from src.dashboard.seed_check import seed_check
from src.domain_tables import DOMAIN_TABLES


@pytest.mark.asyncio
async def test_no_manifest_reports_unknown(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SEED_MANIFEST_PATH", str(tmp_path / "missing.json"))

    report = await seed_check(db_session)

    assert report["overall_status"] == "unknown"
    assert report["total_expected"] is None
    assert len(report["tables"]) == len(DOMAIN_TABLES)
    for t in report["tables"]:
        assert t["expected"] is None
        assert t["status"] == "unknown"


@pytest.mark.asyncio
async def test_matching_manifest_reports_ok(db_session, tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.json"
    monkeypatch.setattr(settings, "SEED_MANIFEST_PATH", str(manifest_path))

    baseline = await seed_check(db_session)
    actual = {t["table"]: t["rows"] for t in baseline["tables"]}
    manifest_path.write_text(json.dumps(actual))

    report = await seed_check(db_session)

    assert report["overall_status"] == "ok"
    assert report["total_expected"] == sum(actual.values())
    for t in report["tables"]:
        assert t["status"] == "ok"
        assert t["expected"] == t["rows"]


@pytest.mark.asyncio
async def test_mismatched_manifest_flags_offending_table(db_session, tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.json"
    monkeypatch.setattr(settings, "SEED_MANIFEST_PATH", str(manifest_path))

    baseline = await seed_check(db_session)
    actual = {t["table"]: t["rows"] for t in baseline["tables"]}
    actual["drivers"] = actual["drivers"] + 1
    manifest_path.write_text(json.dumps(actual))

    report = await seed_check(db_session)

    assert report["overall_status"] == "mismatch"
    by_table = {t["table"]: t for t in report["tables"]}
    assert by_table["drivers"]["status"] == "mismatch"
    assert all(by_table[name]["status"] == "ok" for name in DOMAIN_TABLES if name != "drivers")


@pytest.mark.asyncio
async def test_endpoint_returns_payload(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SEED_MANIFEST_PATH", str(tmp_path / "missing.json"))

    resp = await client.get("/dashboard/seed-check")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"tables", "overall_status", "total_rows", "total_expected"}
    assert len(body["tables"]) == len(DOMAIN_TABLES)
