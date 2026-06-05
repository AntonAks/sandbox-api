"""Print a JWT for the demo user by logging in via the API.

Reuses the ``/auth/login`` flow with ``DEMO_USER_EMAIL`` / ``DEMO_USER_PASSWORD``
from .env (perf.settings). Default user only.

Usage:
    uv run --project app python -m perf.issue_token
    uv run --project app python -m perf.issue_token --base-url http://1.2.3.4
"""

from __future__ import annotations

import argparse
import asyncio

import aiohttp

from perf.settings import settings


async def login(base_url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/auth/login",
            json={
                "email": settings.DEMO_USER_EMAIL,
                "password": settings.DEMO_USER_PASSWORD,
            },
        ) as resp:
            resp.raise_for_status()
            return (await resp.json())["access_token"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a JWT for the demo user.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    print(asyncio.run(login(args.base_url)))


if __name__ == "__main__":
    main()
