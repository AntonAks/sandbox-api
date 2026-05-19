import pytest

from src.config import settings


@pytest.mark.asyncio
async def test_login_returns_token(client, demo_users):
    r = await client.post(
        "/auth/login",
        json={"email": settings.DEMO_USER_EMAIL, "password": settings.DEMO_USER_PASSWORD},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client, demo_users):
    r = await client.post(
        "/auth/login",
        json={"email": settings.DEMO_USER_EMAIL, "password": "wrongpassword"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client, demo_users):
    r = await client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token_returns_401(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_token_returns_user(client, demo_users):
    login_r = await client.post(
        "/auth/login",
        json={"email": settings.DEMO_USER_EMAIL, "password": settings.DEMO_USER_PASSWORD},
    )
    assert login_r.status_code == 200
    token = login_r.json()["access_token"]

    me_r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_r.status_code == 200
    body = me_r.json()
    assert body["email"] == settings.DEMO_USER_EMAIL
    assert "user_id" in body
