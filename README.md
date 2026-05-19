# sandbox-api

Logistics-dispatcher backend used as the demo project for an AI workshop on diagnosing
performance problems with Claude Code. See `docs/spec.md` for the baseline (phase 1)
spec and `docs/superpowers/specs/2026-05-17-phase2-workshop-content-design.md` for
the phase 2 (this) design.

## Quick start (local)

```bash
cp .env.example .env
# Required env vars to set in .env:
#   JWT_SECRET_KEY        — openssl rand -base64 48
#   DEMO_USER_EMAIL       — any valid email
#   DEMO_USER_PASSWORD    — openssl rand -base64 24
just up
docker compose exec app alembic upgrade head
just seed-csv
```

Login (replace placeholders with values you put in `.env`):
```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<DEMO_USER_EMAIL>","password":"<DEMO_USER_PASSWORD>"}'
```

The demo user is upserted on app startup from `DEMO_USER_EMAIL` and
`DEMO_USER_PASSWORD` env vars (see `app/src/auth/seed.py`). Rotating the
password is a redeploy, not a migration.

## Endpoints

Public:
- `GET /health/live`, `GET /health/ready`
- `POST /auth/login`

Protected (Bearer JWT):
- `GET /drivers` — list with status/terminal filters
- `GET /drivers/{id}/dashboard` — driver page with recent trips + month KPIs
- `POST /trips/search` — rich filter search (perf-target)
- `GET /trips/{id}` — trip detail
- `GET /loads/upcoming?days=N` — next N days
- `GET /reports/fleet-utilization?month=YYYY-MM` — pre-aggregated monthly report
- `GET /auth/me` — current user

## Common tasks

See `justfile` — `just up`, `just down`, `just logs`, `just test`, `just lint`,
`just seed-csv`, `just perf-trip-search`, etc.

## Deploy

Push to `main` triggers `.github/workflows/deploy.yml` (CI + build + SSH deploy
to AWS EC2 + smoke). Infra is provisioned via `Actions → Infra → Run workflow → apply`.
See `infra/README.md`.
