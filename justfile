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

# Deploy
deploy:
    git push origin main

# Server access
ssh:
    ssh root@$(cd infra && tofu output -raw server_ip)

server-logs:
    ssh root@$(cd infra && tofu output -raw server_ip) 'cd /opt/workshop && docker compose logs -f app'

server-status:
    ssh root@$(cd infra && tofu output -raw server_ip) 'cd /opt/workshop && docker compose ps'
