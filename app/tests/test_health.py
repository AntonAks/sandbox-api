import pytest

from src.db import get_session
from src.main import app


async def test_health_live(client):
    r = await client.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert "x-request-id" in {k.lower() for k in r.headers}


async def test_health_ready_ok(client):
    r = await client.get("/health/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": "ok"}


@pytest.fixture
def fail_session():
    class _FailSession:
        async def execute(self, *args, **kwargs):
            raise RuntimeError("simulated db unreachable")

    async def _override():
        yield _FailSession()

    app.dependency_overrides[get_session] = _override
    yield
    app.dependency_overrides.pop(get_session, None)


async def test_health_ready_db_unreachable(client, fail_session):
    r = await client.get("/health/ready")
    assert r.status_code == 503
    assert r.json() == {"status": "error", "db": "unreachable"}
