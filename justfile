default:
    @just --list

# Local dev
up:
    docker compose up -d --build

down:
    docker compose down

logs:
    docker compose logs -f app

shell:
    docker compose exec app bash

# Database
migrate name:
    docker compose exec app alembic revision --autogenerate -m "{{name}}"

migrate-up:
    docker compose exec app alembic upgrade head

migrate-down:
    docker compose exec app alembic downgrade -1

psql:
    docker compose exec db psql -U postgres

# Testing & quality
test:
    docker compose exec app pytest -v

lint:
    docker compose exec app ruff check . && docker compose exec app ruff format --check .

format:
    docker compose exec app ruff format .

# Seed
seed-csv:
    docker compose exec app python -m src.scripts.seed_csv

seed-csv-reset:
    docker compose exec app python -m src.scripts.seed_csv --reset

# Perf
perf-trip-search:
    uv run --project app python -m perf.stress_trip_search --env local

perf-trip-search-aws ip body="heavy" max-parallel="34":
    STRESS_TARGET_URL=http://{{ip}} uv run --project app python -m perf.stress_trip_search \
        --env aws --body {{body}} --max-parallel {{max-parallel}}

# Deploy
deploy:
    git push origin main

# Server access
ssh:
    ssh ubuntu@$(cd infra && tofu output -raw server_ip)

server-logs:
    ssh ubuntu@$(cd infra && tofu output -raw server_ip) 'cd /opt/workshop && docker compose logs -f app'

server-status:
    ssh ubuntu@$(cd infra && tofu output -raw server_ip) 'cd /opt/workshop && docker compose ps'
