# ТЗ: Baseline setup для AI workshop

## Контекст

Я готую workshop для розробників, де демонструватиму діагностику і рішення performance проблем за допомогою Claude Code. Це baseline setup — фундамент, на який пізніше додаватиметься бізнес-логіка з закладеними проблемами (N+1, повільні queries, можливо race conditions).

Стек фіксований: Python 3.12, FastAPI, PostgreSQL 16, Docker, GitHub Actions, Hetzner Cloud (deploy через SSH + ghcr.io). Без SSL — workshop ефемерний, instance видалю після.

## Структура repo

Monorepo:

```
.
├── app/                          # FastAPI application
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py             # pydantic-settings
│   │   ├── db.py                 # SQLAlchemy async engine, session
│   │   ├── logging.py            # structured JSON logging
│   │   ├── middleware.py         # request_id middleware
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── health.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── test_health.py
│   ├── alembic/                  # готовий до використання
│   │   ├── versions/             # порожня
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── alembic.ini
│   ├── pyproject.toml            # uv, не poetry
│   ├── uv.lock
│   ├── Dockerfile
│   └── .dockerignore
├── infra/
│   ├── main.tf                   # Hetzner provider, 1 server, firewall
│   ├── variables.tf
│   ├── outputs.tf
│   ├── cloud-init.yaml
│   └── README.md
├── deploy/
│   ├── docker-compose.prod.yml
│   └── nginx.conf
├── docker-compose.yml            # для local dev
├── .github/
│   └── workflows/
│       ├── ci.yml                # lint + test + build на кожен PR
│       └── deploy.yml            # build + push to ghcr.io + ssh deploy на main
├── .env.example
├── .gitignore
├── justfile                      # команди-shortcuts
└── README.md
```

## Вимоги до app

### Endpoints

- `GET /health/live` — повертає `{"status": "ok"}` 200. Не торкається БД. Для liveness probe.
- `GET /health/ready` — робить `SELECT 1` до Postgres. Якщо ок — `{"status": "ok", "db": "ok"}` 200. Якщо БД недоступна — 503 з `{"status": "error", "db": "unreachable"}`. Для readiness.

### Налаштування

- `pydantic-settings` для конфігу. Параметри: `DATABASE_URL`, `LOG_LEVEL`, `ENV` (dev/prod), `UVICORN_WORKERS` (default 2).
- `.env.example` з усіма змінними і коментарями про призначення кожної.

### Database layer

- SQLAlchemy 2.0 async, `asyncpg` driver.
- Connection pool з дефолтами `pool_size=5, max_overflow=5` (потім тюнитимемо під workshop).
- Залежність `get_session()` для FastAPI dependency injection.
- БД ініціалізація на startup: спроба підключитись з retry (5 спроб з backoff), щоб контейнер не падав якщо Postgres ще не готовий.

### Logging

- JSON structured logs через `structlog`.
- Кожен HTTP request логується з: `request_id` (UUID, генерується middleware і пробрасується в response header `X-Request-ID`), `method`, `path`, `status`, `duration_ms`.
- Рівень з env, default INFO.
- `uvicorn` access log вимкнений — все йде через наш middleware щоб не дублювати.

### Alembic

- Налаштований, готовий до `alembic revision --autogenerate`.
- `env.py` читає `DATABASE_URL` з env, не з alembic.ini.
- Поки без міграцій — порожня папка `versions/`.
- При старті контейнера в prod автоматично виконується `alembic upgrade head` перед запуском uvicorn (через entrypoint script).

### Tests

- pytest + pytest-asyncio + httpx async client.
- `conftest.py` з фікстурами для test client і test DB.
- Тест на `/health/live` — без БД, перевіряє 200.
- Тест на `/health/ready` — з реальною Postgres через docker-compose service в CI (а не testcontainers — простіше і швидше для CI).
- Параметризований тест `/health/ready` — коли БД доступна (200) і коли ні (симуляція через monkeypatch, очікуємо 503).

### Dependencies

Через `uv`. Файл `pyproject.toml` з секцією `[project]` (PEP 621), не legacy poetry формат. Lock через `uv.lock`.

Production dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `pydantic-settings`, `structlog`, `alembic`.

Dev dependencies (через `[dependency-groups]`): `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`.

## Docker

### `app/Dockerfile`

Multi-stage:
- Builder: `python:3.12-slim` + uv, копіює `pyproject.toml` + `uv.lock`, робить `uv sync --frozen --no-dev`
- Runtime: `python:3.12-slim`, копіює `.venv` з builder-а, копіює `src/` і `alembic/`, non-root user `app`, healthcheck через `curl -f http://localhost:8000/health/live`
- Entrypoint script: `alembic upgrade head && exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-2}`

### `docker-compose.yml` (local dev)

- `app`: build з `./app`, ports `8000:8000`, env з `.env`, depends_on `db` з `condition: service_healthy`, volumes для hot reload (`./app/src:/app/src`), command override на `uvicorn --reload --workers 1`
- `db`: `postgres:16-alpine`, named volume `pg_data`, healthcheck `pg_isready -U $POSTGRES_USER`, ports `5432:5432` (для local debugging — підключитися psql/DBeaver), env `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

### `deploy/docker-compose.prod.yml`

- `app`: image `ghcr.io/${GITHUB_REPOSITORY}:latest`, без build, restart `unless-stopped`, env з `.env` на сервері, depends_on db
- `db`: той самий postgres:16-alpine, volume `pg_data`, БЕЗ expose назовні
- `nginx`: `nginx:alpine`, mount `./nginx.conf:/etc/nginx/nginx.conf:ro`, ports `80:80`, restart unless-stopped, depends_on app

### `deploy/nginx.conf`

Простий reverse proxy:
- `proxy_pass http://app:8000`
- `proxy_set_header X-Real-IP`, `X-Forwarded-For`, `Host`
- `limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s` з `burst=20 nodelay` — щоб випадкові скани не псували метрики під час workshop. Цей liміт ми будемо ВИМИКАТИ перед load test (закомментуємо), тому тримай його виокремленою секцією з коментарем "DISABLE BEFORE LOAD TEST".
- access_log в JSON форматі з `$request_time` і `$upstream_response_time` — це критично для діагностики.

## GitHub Actions

### `.github/workflows/ci.yml`

Triggers: `pull_request`, `push` крім main.

Jobs:
1. **lint**: setup uv, `uv sync`, `uv run ruff check .`, `uv run ruff format --check .`
2. **test**: services postgres:16, env `DATABASE_URL` на test postgres, `uv sync`, `uv run pytest -v`
3. **build**: `docker build -t test ./app` без push (валідація що збирається)

Кеш: `actions/setup-python` з `cache: 'pip'` НЕ підходить для uv. Використати `astral-sh/setup-uv@v3` з вбудованим кешем.

### `.github/workflows/deploy.yml`

Triggers: `push` в `main`.

Jobs:
1. **ci**: викликає reusable частину з ci.yml (або дублює — на твій вибір, обґрунтуй коротко)
2. **build-and-push**: 
   - login до ghcr.io через `GITHUB_TOKEN`
   - `docker/build-push-action` з тегами `latest` і `${{ github.sha }}`
   - cache через GHA cache backend
3. **deploy**:
   - needs build-and-push
   - SSH через `appleboy/ssh-action`
   - команди: `cd /opt/workshop && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d`
4. **smoke-test**:
   - needs deploy
   - curl `http://${{ secrets.SSH_HOST }}/health/ready` з retry (max 12 спроб по 5 секунд = 60s)
   - fail якщо не зелений

Required secrets: `SSH_PRIVATE_KEY`, `SSH_HOST`, `SSH_USER`. `GITHUB_TOKEN` для ghcr вже є by default.

## Terraform

### `infra/main.tf`

- Provider `hetznercloud/hcloud`
- 1 server `cpx21` в `fsn1`, image `ubuntu-24.04`
- Firewall: 
  - 80/tcp з `0.0.0.0/0`
  - 22/tcp з `var.admin_ip` (мій IP)
- SSH key з local file (path через variable)
- cloud-init який:
  1. ставить docker + docker compose plugin
  2. створює `/opt/workshop`
  3. кладе туди `docker-compose.prod.yml` і `nginx.conf` (через `write_files`)
  4. логінується в ghcr.io через deploy token (передається як user_data variable)
  5. створює `.env` з production значеннями (Postgres credentials, etc)
  6. робить перший `docker compose pull && docker compose up -d`

### `infra/variables.tf`

- `hcloud_token` (sensitive)
- `admin_ip` (для SSH firewall rule)
- `ssh_public_key_path` (default `~/.ssh/id_ed25519.pub`)
- `github_repository` (для image path)
- `ghcr_token` (sensitive, для pull з private registry якщо буде private)
- `postgres_password` (sensitive)
- `app_env` (для `.env`)

### `infra/outputs.tf`

- `server_ip` — IPv4 сервера
- `ssh_command` — готова команда `ssh root@<ip>`

### `infra/README.md`

Інструкції:
1. Створити Hetzner API token
2. `cp terraform.tfvars.example terraform.tfvars`, заповнити
3. `tofu init && tofu apply`
4. Дочекатися доки cloud-init завершиться (`ssh root@<ip> 'cloud-init status --wait'`)
5. Перевірити `curl http://<ip>/health/ready`
6. Як `tofu destroy`

## Justfile

```
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
```

## README.md (верхнього рівня)

Секції:
1. **What is this** — 2-3 речення
2. **Quick start (local)** — 3 команди
3. **Architecture** — короткий опис компонентів
4. **Project structure** — дерево з коментарями
5. **Common tasks** — посилання на justfile команди
6. **Deploy** — як працює CI/CD
7. **Adding a migration** — приклад
8. **Troubleshooting** — типові проблеми (DB connection refused, port 8000 зайнятий, etc)

## Що НЕ робити на цьому етапі

- Не додавай Redis, кеш, application-level rate limiting, Prometheus, Grafana, tracing.
- Не додавай авторизацію, JWT, API keys.
- Не пиши доменні моделі і бізнес-endpoints — тільки skeleton.
- Не оптимізуй під performance — навмисно лишаємо дефолти.
- Не додавай pre-commit hooks (додам сам пізніше якщо треба).
- Не додавай docker-compose override для testing — використовуємо service container в CI.

## Критерії готовності (definition of done)

1. `git clone && cp .env.example .env && just up` — підіймається локально, `curl localhost:8000/health/ready` повертає 200 з `{"status": "ok", "db": "ok"}`.
2. `just test` — всі тести проходять.
3. PR в main — CI зелений (lint + test + build).
4. Merge в main — deploy.yml проходить успішно, smoke-test зелений.
5. `curl http://<server-ip>/health/ready` повертає 200 з production server-а.
6. `just lint` — без помилок і без diff від format.
7. `tofu destroy` — все знесено, нічого не лишилось висіти на Hetzner.
8. JSON logs видно через `just logs` з усіма потрібними полями (`request_id`, `method`, `path`, `status`, `duration_ms`).
9. `X-Request-ID` header присутній в response.

## Workflow на цьому етапі

1. Прочитай це ТЗ повністю.
2. Якщо щось неоднозначно або суперечить — задай уточнюючі питання ОДНИМ повідомленням, не починай імплементацію.
3. Запропонуй план: список файлів які створиш, в якому порядку. Я підтверджу.
4. Імплементуй поетапно: спочатку local dev (compose + app + tests), потім CI, потім Terraform + deploy.
5. Після кожного етапу — короткий статус, що зроблено, що далі.
6. Не запускай `tofu apply` сам — це я роблю руками.
7. CI workflow тестуй створенням draft PR, не push-ом одразу в main.

## Технічні преференції

- Python style: ruff config з sensible defaults (line-length 100, target-version py312).
- Імпорти: явні, без `*`. Relative imports всередині `src/`.
- Type hints скрізь де можливо.
- Async всюди де є I/O. Sync функції тільки для pure logic.
- Error handling в endpoints через FastAPI exception handlers, не try/except в кожному handler-і.
- Назви БД таблиць: snake_case, множина (`users`, `orders`).
- Назви endpoints: `/resource` для колекцій, `/resource/{id}` для одиничних.

Запитай уточнення якщо щось неоднозначно. Не починай писати код поки не підтвердиш план файлів і не отримаєш від мене "ок, починай".
