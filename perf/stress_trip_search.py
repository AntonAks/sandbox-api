"""Stress test for POST /trips/search.

Usage:
    uv run python -m perf.stress_trip_search --env local
    STRESS_TARGET_URL=http://1.2.3.4 uv run python -m perf.stress_trip_search --env aws
"""

import argparse
import asyncio
import json
import os
import statistics
import time

import aiohttp

from perf.bodies.trip_search_heavy import TRIP_SEARCH_HEAVY
from perf.bodies.trip_search_light import TRIP_SEARCH_LIGHT

BODIES = {"heavy": TRIP_SEARCH_HEAVY, "light": TRIP_SEARCH_LIGHT}

ENV_CONFIG = {
    "local": {"url": "http://localhost:8000", "latency_offset": 0.0},
    "aws": {"url": os.environ.get("STRESS_TARGET_URL", ""), "latency_offset": 0.05},
}

DEMO_EMAIL = os.environ.get("DEMO_USER_EMAIL")
DEMO_PASSWORD = os.environ.get("DEMO_USER_PASSWORD")
if not DEMO_EMAIL or not DEMO_PASSWORD:
    raise SystemExit(
        "DEMO_USER_EMAIL and DEMO_USER_PASSWORD env vars are required "
        "(same values used by the deployed app — check GitHub secrets)."
    )


async def login(session: aiohttp.ClientSession, base_url: str) -> str:
    async with session.post(
        f"{base_url}/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    ) as resp:
        resp.raise_for_status()
        return (await resp.json())["access_token"]


async def send_request(
    sem: asyncio.Semaphore,
    latencies: list,
    errors: list,
    session: aiohttp.ClientSession,
    url: str,
    headers: dict,
    body: str,
) -> None:
    async with sem:
        start = time.perf_counter()
        try:
            async with session.post(url, headers=headers, data=body) as resp:
                await resp.read()
                if resp.status != 200:
                    errors.append(f"http_{resp.status}")
                    return
            latencies.append(time.perf_counter() - start)
        except Exception as exc:
            errors.append(type(exc).__name__)


async def stress(
    url: str,
    headers: dict,
    body: str,
    latencies: list,
    errors: list,
    parallel: int,
    total: int,
    timeout_s: int = 120,
) -> None:
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    connector = aiohttp.TCPConnector(limit=parallel)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        sem = asyncio.Semaphore(parallel)
        tasks = [
            asyncio.create_task(
                send_request(sem, latencies, errors, session, url, headers, body)
            )
            for _ in range(total)
        ]
        await asyncio.gather(*tasks)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=list(ENV_CONFIG.keys()), default="local")
    parser.add_argument(
        "--body",
        choices=list(BODIES.keys()),
        default="heavy",
        help="heavy: broad filters (~10s+ per request, demo material). "
        "light: narrow filters (sanity check, fast).",
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=34,
        help="Cap concurrency ramp at this value (default 34 = full ramp).",
    )
    args = parser.parse_args()

    cfg = ENV_CONFIG[args.env]
    base_url = cfg["url"]
    if not base_url:
        raise SystemExit(
            f"env={args.env}: base URL empty (set STRESS_TARGET_URL for aws)"
        )

    network_offset = cfg["latency_offset"]
    url = f"{base_url}/trips/search"
    body = json.dumps(BODIES[args.body])

    async def _login_only() -> str:
        async with aiohttp.ClientSession() as s:
            return await login(s, base_url)

    token = asyncio.run(_login_only())
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    geos = [int(2 * 1.5**p) for p in range(8)]
    geos = [g for g in geos if g <= args.max_parallel]
    loops = [(p, p * 5) for p in geos]

    print("Will run stress test with (parallel, total) pairs:", loops)
    print(f"Subtracting {network_offset}s network offset from latencies")
    print("Warming up server...")
    asyncio.run(stress(url, headers, body, [], [], 5, 10))
    time.sleep(0.5)

    loops = [(1, 10), (1, 15), (1, 30), (1, 60), (1, 120)]
    # loops = [(2, 10), (2, 15), (2, 30), (2, 60), (2, 120)]

    header = "total/parallel   errors    " + "".join(
        f"{k:>7}" for k in ("time", "avg", "p95", "min", "max")
    )
    print(header)

    for parallel, total in loops:
        latencies: list[float] = []
        errors: list[str] = []
        start = time.perf_counter()
        asyncio.run(stress(url, headers, body, latencies, errors, parallel, total))
        elapsed = time.perf_counter() - start

        ok = len(latencies)
        err_summary = f"{len(errors)}/{total}"
        if not latencies:
            err_detail = ",".join(sorted(set(errors))[:3])
            row = (
                f"{total}/{parallel:<13} {err_summary:>7}    ALL FAILED ({err_detail})"
            )
            print(row)
            time.sleep(0.5)
            continue

        results = {
            "time": elapsed,
            "avg": statistics.mean(latencies),
            "p95": (
                statistics.quantiles(latencies, n=20)[18]
                if ok >= 20
                else max(latencies)
            ),
            "min": min(latencies),
            "max": max(latencies),
        }
        for k in ("avg", "p95", "min", "max"):
            results[k] = max(0.0, results[k] - network_offset)
        row = f"{total}/{parallel:<13} {err_summary:>7}    " + "".join(
            f"{v:>6.2f}s" for v in results.values()
        )
        print(row)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
