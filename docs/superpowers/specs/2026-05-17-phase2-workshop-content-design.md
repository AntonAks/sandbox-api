# Phase 2 — Dispatcher Console для workshop-демо

**Дата:** 2026-05-17
**Статус:** Design approved через brainstorming session, готово до writing-plans
**Базується на:** `docs/spec.md` (baseline phase), [[project_workshop_context]], [[project_aws_infra]]

## 1. Контекст і ціль

`sandbox-api` baseline (phase 1) — це vanilla FastAPI skeleton без домену. Цей документ описує **phase 2** — побудову правдоподібного logistics-dispatcher backend поверх вже завантаженого датасету [European Logistics Operations Database](https://www.kaggle.com/datasets/yogape/logistics-operations-database).

**Ціль phase 2 — НЕ "додати домен з perf-багами для уроку про perf"**. Ціль — **побудувати ready-to-onboard production-like проект, який Антон використовує як vehicle для демонстрації власного Claude Code workflow** перед mixed аудиторією (~2 години, переважно Node.js-розробники).

Деталі workshop-формату: live demo, Антон один за клавіатурою, клин main, реальні branches/PRs/deploys, аудиторія дивиться. API — це **backdrop**, не **subject**.

## 2. Scope

### In scope (phase 2 робить)

- 14 SQLAlchemy моделей (всі CSV-таблиці + User)
- 9 endpoints: `health/live`, `health/ready`, `POST /auth/login`, 6 business endpoints
- JWT auth (medium-weight): User table, `POST /auth/login`, `Depends(get_current_user)`, demo users pre-seeded
- 3 baseline Alembic migrations
- CSV seed CLI command (`just seed-csv`)
- 2 органічні perf-баги в коді (Bug A у `POST /trips/search`, Bug B у `GET /drivers/{id}/dashboard`)
- 1 bonus design issue (Bug C — stale data у `GET /reports/fleet-utilization`)
- Perf load-test script (`perf/stress_trip_search.py`) — адаптована версія Антонового aiohttp-tool
- Нерівне test coverage (свідомо — щоб "add tests" було природним демо)
- Updated README + .env.example + justfile commands

### Out of scope (явно НЕ робимо)

- Multi-persona endpoints (`/customer-portal/*`, `/driver-portal/*`) — це підхід B, відхилений
- Roles / permissions / refresh tokens / user CRUD / password reset
- PostGIS / гео-запити (хоч `facilities` має lat/lng)
- Refresh job для pre-aggregated metrics (це частина bonus demo, а не baseline)
- Workshop notes 03-05 (Антон пише після workshop)
- Caching layer (Redis тощо)
- Background workers / queues
- Observability beyond JSON logs (no Prometheus, no tracing)
- Frontend / Swagger customization
- Application-level rate limiting (nginx має `limit_req` яка вимикається на perf-test)

## 3. Schema, migrations, seed

### SQLAlchemy моделі

Всі 14 domain-таблиць з CSV + User. Layout:

```
app/src/models/
  base.py            # DeclarativeBase
  users.py           # User (auth)
  drivers.py         # Driver
  trucks.py          # Truck
  trailers.py        # Trailer
  customers.py       # Customer
  facilities.py      # Facility (з lat/lng — не використовуємо у phase 2)
  routes.py          # Route (lane, origin→destination)
  loads.py           # Load
  trips.py           # Trip (1-to-1 з Load — свідома design smell для refactor-демо)
  fuel.py            # FuelPurchase
  maintenance.py     # MaintenanceRecord
  events.py          # DeliveryEvent
  incidents.py       # SafetyIncident
  metrics.py         # DriverMonthlyMetrics, TruckUtilizationMetrics
```

Стиль за `docs/rules/code_rules.md`: `Mapped[]` + `mapped_column()`, FK через типізований `relationship()`. Composite PK на metrics-таблицях через `__table_args__`.

### Alembic migrations (5 baseline — оновлено пост-impl)

1. **`0001_create_domain_schema.py`** — всі 14 domain-таблиць з FK. Без даних.
2. **`0002_seed_demo_users.py`** — User table + INSERT 2 demo users (`dispatcher@example.com` / `dispatcher123`, `viewer@example.com` / `viewer123`) з bcrypt-хешами. Це legal per code_rules ("controlled seed").
3. **`0003_indexes_baseline.py`** — **свідомо неповні**. Лише FK-індекси через `index=True` у моделях + 2 explicit extras (`maintenance_records.maintenance_date`, `safety_incidents.incident_date`). **Свідомо НЕ кладемо** composite `Trip(driver_id, dispatch_date)` — це fix який Claude додасть на live-демо.
4. **`0004_nullable_optional_fks.py`** *(data-driven, додано в Task 10)* — робить nullable: `trips.{driver_id, truck_id, trailer_id}`, `fuel_purchases.{driver_id, truck_id}`, `safety_incidents.{driver_id, truck_id}`. CSV-датасет містить тисячі рядків з порожніми FK — це реальний production-shape data quality issue.
5. **`0005_drop_trailer_number_unique.py`** *(data-driven, додано в Task 10)* — знімає UNIQUE з `trailers.trailer_number` (4 дублікати в CSV).

Workshop demo D3 створить **`0006_perf_indexes.py`** (composite index + інші) як live-демо action.

### CSV seed (НЕ через міграцію)

`app/src/scripts/seed_csv.py` — proper CLI module (per code_rules "no one-off scripts"):

```bash
just seed-csv         # завантажує всі CSV через COPY за ~1-2 хв
just seed-csv-reset   # TRUNCATE 14 domain-tables (зберігає users) + reseed
```

Imp: для кожної таблиці `COPY <table> FROM STDIN WITH CSV HEADER` через asyncpg. Idempotent: на старті перевіряє `SELECT 1 FROM trips LIMIT 1` — якщо щось є, друкує "data already seeded" і виходить нулем.

### Production deployment

- Entrypoint app: `alembic upgrade head && uvicorn` — auth і domain tables створюються автоматично з demo users
- CSV seed — **руками** один раз через SSH після першого `Infra apply`:
  ```bash
  ssh ubuntu@<ip> 'docker compose exec app python -m app.src.scripts.seed_csv'
  ```
- EBS привʼязаний з `delete_on_termination = true`, тому після `Infra destroy → apply` потрібен новий seed

## 4. Endpoints

Загалом 9 endpoints у 5 модулях + health.

### Public (без auth)

| Method | Path | Module |
|--------|------|--------|
| GET | `/health/live` | `health/` |
| GET | `/health/ready` | `health/` |
| POST | `/auth/login` | `auth/` |

### Protected (через `Depends(get_current_user)`)

| Method | Path | Module | Bug status |
|--------|------|--------|-----------|
| GET | `/drivers` | `drivers/` | clean |
| GET | `/drivers/{driver_id}/dashboard` | `drivers/` | **Bug B (N+1 + inline compute)** |
| POST | `/trips/search` ⚡ | `trips/` | **Bug A (missing index + Python-filter + N+1 enrichment)** — perf-target |
| GET | `/trips/{trip_id}` | `trips/` | clean |
| GET | `/loads/upcoming` | `loads/` | clean |
| GET | `/reports/fleet-utilization` | `reports/` | clean, але pre-agg може бути stale (bonus) |

### Сигнатури (essential subset — повні shape у impl plan)

**`POST /auth/login`** — body `{email, password}` → 200 `{access_token, token_type, expires_in}` / 401

**`GET /drivers?status=...&terminal=...`** — список з фільтрами → `[{driver_id, name, employment_status, home_terminal, years_experience, ...}]`

**`GET /drivers/{id}/dashboard?since=...`** — `{driver, recent_trips: [...], current_month_metrics: {...}, open_incidents_count}` (recent_trips мають N+1, metrics обчислюються inline замість використання pre-agg)

**`POST /trips/search`** — body з 10+ optional filters (`driver_ids`, `truck_ids`, `load_status`, `date_from/to`, `destination_state`, `min/max_distance`, `limit`, `offset`) → `{total, items: [...]}`. Це perf-target. Body для load-test зберігається у `perf/bodies/trip_search_heavy.py`.

**`GET /trips/{id}`** — `{trip, load, driver, truck, trailer, route, fuel_summary, delivery_events_count}` — clean, використовує `selectinload`

**`GET /loads/upcoming?days=3`** — список завантажень на найближчі N днів

**`GET /reports/fleet-utilization?month=YYYY-MM`** — звіт з `truck_utilization_metrics`, повертає `data_computed_at` чесно

### Структура коду

```
app/src/
  main.py
  config.py              # +JWT_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES
  db.py logging.py middleware.py
  models/                # див. Section 3
  health/                # promoted з routes/health.py
    router.py
  auth/
    router.py service.py dependencies.py security.py schemas.py
  drivers/
    router.py service.py schemas.py
  trips/
    router.py service.py schemas.py
  loads/
    router.py service.py schemas.py
  reports/
    router.py service.py schemas.py
  scripts/
    seed_csv.py
```

Малий refactor baseline: `routes/health.py` → `health/router.py` для консистентності з модульним підходом.

### Auth implementation

- **Hashing**: bcrypt через `passlib[bcrypt]`
- **JWT**: `python-jose[cryptography]`, HS256, expire 24h
- **Config** з env: `JWT_SECRET_KEY` (required), `ACCESS_TOKEN_EXPIRE_MINUTES` (default 1440)
- **Demo users** з простими паролями для зручності live-demo (коментар в `.env.example`: "demo only — change for real")

## 5. Intentional perf bugs

**Принцип:** жодних `# TODO: bug for demo` коментарів. Це live-investigation; коміти у git history виглядають як справжній код, який пройшов code review.

### Bug A — `POST /trips/search` (perf-target скрипта)

4 проблеми в одному endpoint:

1. **Missing composite index** на `Trip(driver_id, dispatch_date)` → seq scan на 85K
2. **Python-side filters** для `min/max_distance` → fetches all matches → filter після
3. **N+1 на join-filters** `destination_state` / `load_status` — для кожного candidate trip окремий `db.get(Load)` + `db.get(Route)`
4. **Result enrichment N+1** — 4 окремі `db.get` для кожного item на сторінці результатів

**Очікувані числа** (на AWS t3.small, baseline):
```
total//parallel    avg    p95
110/22             1.85s  3.50s
```

**Fix path (live на демо):**
- Migration `0006_perf_indexes.py` — composite `(driver_id, dispatch_date)`
- Push filters до SQL (rewrite з join до Load/Route, всі conditions у WHERE)
- Replace N+1 на `selectinload(Trip.driver, Trip.truck, Trip.load.selectinload(Load.route))`

**Очікуваний after:** `p95 ~30-50ms на 22 паралельних`.

### Bug B — `GET /drivers/{id}/dashboard`

Тихий баг (не показується у load-test, бо load-test б'є по інший endpoint). Видно через ручний curl (~600-1500ms на одного водія).

3 проблеми всередині:

1. **N+1 на recent_trips** — 20 trips × 3 fetches (load, customer, route) = ~60 додаткових queries
2. **N+1 на per-trip events** для on_time компуту — ще 20 queries
3. **Inline compute current_month_metrics** замість lookup у `driver_monthly_metrics` (pre-agg таблиця **існує і має готові поля**, але код ігнорує)

**Fix path:**
- `selectinload` на recent_trips
- Single events query замість per-trip
- Switch metrics на `DriverMonthlyMetrics` lookup
- **Architectural discussion live**: hybrid (current month inline для свіжості, попередні з pre-agg)

### Bug C — `GET /reports/fleet-utilization` stale (bonus, не блокує)

Запит для `month=current` повертає неповні дані бо немає refresh-job-у. `data_computed_at` повертається чесно.

**Fix path (якщо демо доходить):**
- Варіант 1: cron-style refresh task
- Варіант 2: on-demand fallback (якщо `data_computed_at` < початок поточного місяця, compute інлайн)
- Hybrid рекомендація

### Перевірка готовності bugs перед workshop

```bash
just up
just seed-csv
just perf-trip-search-aws    # очікую p95 > 1s на 22 паралельних
curl http://<ip>/drivers/1/dashboard -H "Auth..."   # очікую ~1s
curl http://<ip>/reports/fleet-utilization?month=2026-05 -H "Auth..."  # очікую stale
```

Якщо bugs регресували — фіксимо "регрес багу" перед workshop.

## 6. Workshop demo chain (2 години)

| Блок | Час | Що |
|------|-----|-----|
| 0. Intro | 0:00–0:05 | Slides — про мене, чому Claude Code |
| 1. Setup Claude Code | 0:05–0:40 | CLAUDE.md, skills (10), hooks (10), .claude structure (5) |
| **2. Live coding** | **0:40–1:45** | 5 демо нижче |
| 3. Summary | 1:45–1:50 | Recap + посилання на матеріали |
| 4. Q&A | 1:50–2:00 | |

### Block 2 — 5 demos (~65 хв)

**D1 — Onboarding (~10 хв)** — Branch: `workshop/onboarding-doc`. Claude використовує Explore agent, читає repo, генерує `docs/ONBOARDING.md`. PR + merge.

**D2 — Perf test execution (~5 хв)** — `just perf-trip-search-aws` → видно погані числа (p95 3.5s на 22 паралельних). Без code changes.

**D3 — Investigate + fix Bug A (~23 хв)** — Branch: `workshop/fix-trip-search-perf`. Plan mode → 4 проблеми → 3 окремі коміти + migration `0006_perf_indexes.py`. Між комітами Антон re-run perf → видно покращення. PR → CI green live → merge → AWS deploy live → smoke test green. Фінально: p95 ~30-50ms.

**D4 — Refactor + new endpoint (~17 хв)** — Branch: `workshop/add-loads-search`. Claude рефакторить trips/search (extract service layer, cursor pagination), додає `POST /loads/search` на тому ж pattern + тести. PR/merge/deploy.

**D5 — Documentation (~10 хв)** — Branch: `workshop/post-workshop-docs`. ADR-001 (perf fix), ADR-002 (search service pattern), updated README. Verify all migrations apply cleanly to fresh DB.

**Bonus якщо час** — Bug B dashboard OR Bug C stale data (Антон обирає на льоту, обидва підготовлені у baseline).

### Risk callouts для live

| Ризик | Mitigation |
|-------|-----------|
| Claude пішов у бік у D3 | Антон сам показує EXPLAIN ANALYZE, "підказує" через follow-up prompt. **Не** використовувати `git reset` live. |
| Perf script не показує покращення | Перевірити baseline числа за день до workshop |
| JWT token expires mid-demo | Перед демо: `just demo-login → export TOKEN=...` |
| CI впав на live merge | Dry-run merge на staging branch + перевірка workflow_run заздалегідь |
| Python-неофіти губляться | Антон вербалізує analogies: "FastAPI route ≈ Express handler", "Pydantic ≈ Zod", "Alembic ≈ TypeORM migrations" |

## 7. Testing strategy

**Нерівне coverage — це дизайн**, не випадковість. Дає Claude'у природні приводи "let's add tests" під час bonus demo.

| Module | Coverage у phase 2 ready |
|--------|---------------------------|
| `health/` | full (вже є) |
| `auth/` | full — login happy/sad, missing/expired token |
| `trips/` | тільки `GET /trips/{id}` — search без тестів |
| `drivers/` | відсутні взагалі |
| `loads/` | відсутні (додаються разом з endpoint у D4) |
| `reports/` | 1 happy path для fleet-utilization |

### Test layout
```
app/tests/
  conftest.py
  test_health.py
  auth/test_login.py
  trips/test_trip_detail.py
  reports/test_fleet_utilization.py
  fixtures/
    users.py
    sample_data.py     # маленький subset (~10 drivers, 50 trips, 100 events)
```

### Test data
- Unit/integration: deterministic subset з `fixtures/sample_data.py`, session-scoped fixture
- **НЕ завантажуємо повний CSV у CI** — повільно і не потрібно для логіки
- Per-test isolation через transaction-rollback (SAVEPOINT)

### CI
`ci.yml` лишається як зараз: postgres service, `uv sync`, `pytest -v`. Phase 2 додає `JWT_SECRET_KEY=test-secret-do-not-use` у `env:`.

## 8. Perf script integration

### Layout
```
perf/
  stress_trip_search.py    # Антонів скрипт, адаптований
  bodies/
    trip_search_heavy.py   # body, що матчить ~5K trips
    trip_search_light.py   # ~50 trips, sanity check
  README.md                # запуск, інтерпретація чисел
```

### Адаптації від Антонового зразка

1. **Login першим** для отримання JWT
2. **Headers** з `Authorization: Bearer ...`
3. **URL** — `/trips/search`, body з `perf/bodies/`
4. **Environment config**: `local` (localhost:8000) і `aws` (`STRESS_TARGET_URL` env var або `tofu output -raw server_ip`)
5. Решта (geometric ramp, p95 table) — як у твоєму

### justfile commands
```
perf-trip-search:
    uv run python -m perf.stress_trip_search --env local

perf-trip-search-aws:
    @echo "Target: $(cd infra && tofu output -raw server_ip)"
    STRESS_TARGET_URL=http://$(cd infra && tofu output -raw server_ip) \
        uv run python -m perf.stress_trip_search --env aws
```

## 9. Deliverables / acceptance criteria

### Code & schema
- [ ] 14 SQLAlchemy моделей у `app/src/models/`
- [ ] User model + JWT auth + login endpoint
- [ ] 9 endpoints — всі повертають правильні shapes
- [ ] 3 baseline migrations
- [ ] **Перевірено** що відсутні composite index для Bug A
- [ ] Bug A та B заведені у коді як планується
- [ ] Demo users (`dispatcher@example.com` / `dispatcher123`) працюють через login

### CSV seed
- [ ] `app/src/scripts/seed_csv.py` як CLI команда
- [ ] `just seed-csv` працює локально, ~570K rows за ~2 хв
- [ ] Idempotent + reset варіант

### Local dev
- [ ] `git clone && cp .env.example .env && just up && just seed-csv` → end-to-end
- [ ] `curl localhost:8000/health/ready` → `{"status":"ok","db":"ok"}`
- [ ] `POST /auth/login` повертає JWT
- [ ] `just test` — всі тести зелені (з навмисною нерівністю)

### CI
- [ ] PR на feature branch — `ci` job зелений
- [ ] Merge to main — `deploy.yml` усі 4 джоби green
- [ ] Smoke-test на AWS — `db:ok`

### AWS prod
- [ ] Після першого merge → SSH + seed → entries загружені
- [ ] `POST /auth/login` повертає JWT
- [ ] `GET /drivers/1/dashboard` → ~600-1500ms (Bug B працює)
- [ ] `just perf-trip-search-aws` → `p95 ≥ 1s на 22 паралельних` (Bug A працює)

### Documentation
- [ ] `README.md` оновлений з one-liner про логістик-домен
- [ ] `.env.example` містить `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- [ ] `perf/README.md` — як запускати, що означають числа

### Workshop bonus state
- [ ] Bug C (stale fleet-utilization) працює — current month повертає stale data
- [ ] Тести для `drivers/`, `loads/`, `trips/search` **навмисно відсутні**

## 10. Effort estimate

~3-5 робочих сесій по 3-4 години:
- Сесія 1: models + 3 baseline migrations + seed_csv + local validation
- Сесія 2: auth (full) + health
- Сесія 3: drivers + trips endpoints з Bug A та B
- Сесія 4: loads + reports + perf script + tests
- Сесія 5: AWS deploy + verify bugs у prod + polish docs

Може бути швидше, якщо сам багато з цього робиш з Claude — що логічно, бо це фактично перша частина workshop content.

## 11. Open questions / parking lot

Не блокують phase 2, але варто памʼятати:
- **Workshop notes 03-05** — окремий post-workshop deliverable
- **Refresh job для metrics** — bonus демо, але якщо колись хочемо у baseline, треба окремий design
- **Multi-persona expansion** (driver-portal, customer-portal) — phase 3 опція якщо буде серія workshop-ів
- **PostGIS** для facilities lat/lng — phase 3 опція
- **Auth roles/permissions** — phase 3 коли scope зросте

## Посилання

- Baseline spec: `docs/spec.md`
- Code rules: `docs/rules/code_rules.md`
- Existing workshop notes: `docs/workshop/01-claude-code-setup.md`, `docs/workshop/02-hooks-in-practice.md`
- AWS infra context: memory `project_aws_infra.md`
- Dataset: https://www.kaggle.com/datasets/yogape/logistics-operations-database
