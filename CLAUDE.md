# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A logistics-dispatcher FastAPI backend that serves as the **baseline project for an AI workshop on diagnosing performance problems**. The code contains *intentional* performance flaws (e.g. `POST /trips/search` does N+1 `session.get()` lookups and filters in Python instead of SQL — see `app/src/trips/service.py`). Do not "fix" these as part of unrelated work: the vanilla baseline must stay as-is unless a task explicitly targets a perf fix. `perf/README.md` documents the expected before/after numbers for the headline regression ("Bug A").

## Running everything goes through Docker Compose + just

The app and its Postgres run in containers; almost every command is a `just` recipe that shells into the `app` container. `just` with no args lists recipes.

```bash
cp .env.example .env          # then set JWT_SECRET_KEY, DEMO_USER_EMAIL, DEMO_USER_PASSWORD
just up                       # docker compose up -d --build
just migrate-up               # alembic upgrade head
just seed-csv                 # load app/data/*.csv into Postgres via COPY (idempotent; --reset variant TRUNCATEs)
```

- **Tests:** `just test` (`docker compose exec app pytest -v`). Single test: `docker compose exec app pytest tests/trips/test_trip_detail.py -k test_name -v`. Tests run *inside* the container; `tests/conftest.py` sets env defaults and drives the app in-process via `httpx.ASGITransport` (no live server needed). Fixtures are session-scoped and self-seed the minimum rows they need, so most tests pass in CI without the full CSV seed.
- **Lint/format:** `just lint` (ruff check + format --check), `just format`. Ruff config lives in `app/pyproject.toml` (line-length 100, rules `E,F,I,UP,B,SIM,ASYNC`). A `PostToolUse` hook auto-runs `ruff format` + `ruff check --fix` on every `.py` file you edit, so manual formatting is usually unnecessary.
- **Migrations:** `just migrate name="..."` (autogenerate), `just migrate-up`, `just migrate-down`. Versions in `app/alembic/versions/`.
- **Perf harness:** `just perf-trip-search` (local) / `just perf-trip-search-aws` ramps concurrency against `POST /trips/search` and reports p95. Bodies in `perf/bodies/`.
- **JWT for ad-hoc calls:** `just jwt` prints a bearer token for the demo user.

The `perf/` package is run from the repo root via `uv run --project app` (not inside the container); everything else uses `docker compose exec app`.

## Architecture

**FastAPI app lives under `app/src/`, organized as one package per domain.** Each domain folder (`auth/`, `trips/`, `drivers/`, `loads/`, `reports/`, `dashboard/`, `health/`, `admin/`) follows the same shape: `router.py` (endpoints) → `service.py` (business logic + queries) → `schemas.py` (Pydantic request/response). Routers are wired together in `app/src/main.py`; imports are absolute from the `src` package (`from src.trips.service import ...`).

**Data layer is fully async SQLAlchemy 2.0 (`asyncpg`).** `app/src/db.py` owns the engine, `SessionLocal`, and the `get_session` dependency. ORM models are split one-file-per-table under `app/src/models/` and re-exported from `app/src/models/__init__.py`. `app/src/domain_tables.py` maps table-name → model and is the single source of truth used by both the CSV seeder and the seed-integrity check.

**Auth is stateless JWT.** `app/src/auth/dependencies.py` exposes the reusable `SessionDep` and `BearerDep` annotated types plus `get_current_user`. Protected routers depend on these. There is no user-signup flow: a single demo user is upserted on startup (`lifespan` in `main.py` → `auth/seed.py`) from `DEMO_USER_EMAIL`/`DEMO_USER_PASSWORD`. Rotating that password is a redeploy, not a migration.

**Seeding is CSV-via-COPY, not fixtures.** `app/src/scripts/seed_csv.py` bulk-loads `app/data/*.csv` in FK-dependency order (`LOAD_ORDER`) and writes an expected-row-count manifest. `app/src/dashboard/seed_check.py` later compares live counts against that manifest and reports ok/mismatch — surfaced through the dashboard.

**The dashboard is an in-process request-traffic monitor**, not a user feature. `RequestCounterMiddleware` (`dashboard/middleware.py`) tallies every request by `METHOD route-template` + status into `dashboard/store.py`, persisted under `STATS_DIR`. Useful for watching load during perf runs.

**Deploy / infra.** Push to `main` → `.github/workflows/deploy.yml` (CI → build image → SSH deploy to AWS EC2 → smoke test). Infrastructure is Terraform/OpenTofu in `infra/` and is **applied only by a human via GitHub `Actions → Infra → Run workflow → apply`** — do not run `tofu apply` locally. See `infra/README.md`.

## Working constraints

- A `PreToolUse` hook blocks git-mutating and other dangerous Bash commands. Don't attempt to push, reset, or force-clean; let the user drive those.
- `.env` and other secret-bearing files are read-denied by `.claude/settings.json` — work from `.env.example` for variable names.
