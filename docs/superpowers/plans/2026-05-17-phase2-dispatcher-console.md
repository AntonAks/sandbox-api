# Phase 2 — Dispatcher Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a believable logistics-dispatcher FastAPI backend on top of the loaded Logistics Operations dataset, ready as the workshop demo vehicle — 9 endpoints, JWT auth, 14 SQLAlchemy models, 3 baseline migrations, CSV seed CLI, 2 intentional perf bugs, perf load-test script.

**Architecture:** Modular FastAPI app (one module per business domain) on SQLAlchemy 2.0 async + asyncpg + PostgreSQL 16. JWT bearer auth via `Depends(get_current_user)`. Alembic for schema, separate CLI for CSV bulk load via `COPY`. Intentional perf gaps in `POST /trips/search` (missing composite index, Python-side filters, N+1) and `GET /drivers/{id}/dashboard` (N+1, inline metrics) — gaps are real code, not flagged TODOs.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, asyncpg, PostgreSQL 16, Alembic, pydantic-settings, structlog, passlib[bcrypt], python-jose[cryptography], pytest + pytest-asyncio, aiohttp (perf script), Docker + docker-compose, uv (deps).

**Spec:** `docs/superpowers/specs/2026-05-17-phase2-workshop-content-design.md`

---

## Preamble — conventions and prerequisites

**Prerequisites (verify before starting):**

- [ ] Working baseline (phase 1) — `just up` brings the app up, `curl localhost:8000/health/ready` returns `{"status":"ok","db":"ok"}`
- [ ] CSV data present in `app/data/` (14 files, `DATABASE_SCHEMA.txt` reference)
- [ ] You are on a fresh feature branch (`phase2-impl` or similar), NOT on `main`. Branch from latest `main`.
- [ ] You can run `uv` commands inside `app/` (it manages deps and the venv)

**Code conventions** (from `docs/rules/code_rules.md` — non-negotiable):

- SQLAlchemy 2.0 style: `select()`, `.where()`, `.scalars()` — no `.query()`
- Use `Mapped[]` annotations with `mapped_column()`
- Use `&` / `|` for boolean composition in queries, not `and_()` / `or_()`
- `nullable=False` explicit on Boolean columns
- Routers handle HTTP validation, services own DB logic — no DB queries in routers
- Never reach into another module's models directly — go through that module's service
- No "step" comments in code; comments only for non-obvious *why*

**Commit convention:** Conventional commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`, `perf:`, `refactor:`). One logical change per commit. The git hook in this repo blocks `git push/commit/reset` from Claude — the engineer running this plan executes commits manually.

**Testing approach:** TDD where the unit is amenable (services, route handlers, security utils). Models and migrations don't TDD — verify by running and inspecting. The two **intentional perf bugs** are tested for **functional correctness only** — perf is verified separately via the load-test script.

---

## Session 1 — Foundation (models, migrations, CSV seed)

### Task 1: Add new dependencies + JWT config

**Files:**
- Modify: `app/pyproject.toml`
- Modify: `app/src/config.py`
- Modify: `.env.example`

- [ ] **Step 1: Add runtime deps to `app/pyproject.toml`**

Inside `[project]` `dependencies = [...]` block, add:
```toml
    "passlib[bcrypt]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "typer>=0.12",
```

- [ ] **Step 2: Add aiohttp to dev deps for perf script**

Inside `[dependency-groups]` `dev = [...]` block, add:
```toml
    "aiohttp>=3.10",
```

- [ ] **Step 3: Lock deps**

```bash
cd app && uv sync
```

Expected: `Resolved N packages` with no errors.

- [ ] **Step 4: Extend `app/src/config.py` with JWT settings**

Add to the `Settings(BaseSettings)` class:
```python
    JWT_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h
```

- [ ] **Step 5: Update `.env.example`**

Append:
```
# JWT — demo only, generate fresh secret for any real deployment
JWT_SECRET_KEY=change-me-to-a-long-random-string
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

- [ ] **Step 6: Update local `.env`**

Set a real value:
```bash
echo "JWT_SECRET_KEY=$(openssl rand -base64 48)" >> .env
echo "ACCESS_TOKEN_EXPIRE_MINUTES=1440" >> .env
```

- [ ] **Step 7: Commit**

```bash
git add app/pyproject.toml app/uv.lock app/src/config.py .env.example
git commit -m "chore: add auth deps and JWT config"
```

---

### Task 2: SQLAlchemy base + User model

**Files:**
- Create: `app/src/models/__init__.py`
- Create: `app/src/models/base.py`
- Create: `app/src/models/users.py`
- Create: `app/tests/models/__init__.py`
- Create: `app/tests/models/test_user_model.py`

- [ ] **Step 1: Create `app/src/models/base.py`**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Project-wide declarative base."""
    pass
```

- [ ] **Step 2: Create `app/src/models/users.py`**

```python
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 3: Create `app/src/models/__init__.py`**

```python
from .base import Base
from .users import User

__all__ = ["Base", "User"]
```

- [ ] **Step 4: Write failing test**

Create `app/tests/models/__init__.py` (empty) and `app/tests/models/test_user_model.py`:
```python
from src.models import User


def test_user_model_columns_exist():
    cols = {c.name for c in User.__table__.columns}
    assert cols == {"user_id", "email", "password_hash", "display_name", "created_at"}


def test_user_email_is_unique():
    assert any(idx.unique for idx in User.__table__.indexes if "email" in [c.name for c in idx.columns])
```

- [ ] **Step 5: Run tests**

```bash
cd app && uv run pytest tests/models/test_user_model.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add app/src/models/ app/tests/models/
git commit -m "feat(models): add SQLAlchemy base and User model"
```

---

### Task 3: Domain models — reference entities (drivers, trucks, trailers, customers, facilities, routes)

**Files:**
- Create: `app/src/models/drivers.py`, `trucks.py`, `trailers.py`, `customers.py`, `facilities.py`, `routes.py`
- Modify: `app/src/models/__init__.py`

Reference for columns: `app/data/DATABASE_SCHEMA.txt` and CSV headers (use `head -1 app/data/<file>.csv` if unsure).

- [ ] **Step 1: Create `app/src/models/drivers.py`**

```python
from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Driver(Base):
    __tablename__ = "drivers"

    driver_id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    termination_date: Mapped[date | None] = mapped_column(Date)
    license_number: Mapped[str] = mapped_column(String(40), nullable=False)
    license_state: Mapped[str] = mapped_column(String(2), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    home_terminal: Mapped[str] = mapped_column(String(80), nullable=False)
    employment_status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    cdl_class: Mapped[str] = mapped_column(String(2), nullable=False)
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False)
```

- [ ] **Step 2: Create `app/src/models/trucks.py`**

```python
from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Truck(Base):
    __tablename__ = "trucks"

    truck_id: Mapped[int] = mapped_column(primary_key=True)
    unit_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    make: Mapped[str] = mapped_column(String(60), nullable=False)
    model_year: Mapped[int] = mapped_column(Integer, nullable=False)
    vin: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    acquisition_mileage: Mapped[int] = mapped_column(Integer, nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(20), nullable=False)
    tank_capacity_gallons: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    home_terminal: Mapped[str] = mapped_column(String(80), nullable=False)
```

- [ ] **Step 3: Create `app/src/models/trailers.py`**

```python
from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Trailer(Base):
    __tablename__ = "trailers"

    trailer_id: Mapped[int] = mapped_column(primary_key=True)
    trailer_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    trailer_type: Mapped[str] = mapped_column(String(40), nullable=False)
    length_feet: Mapped[int] = mapped_column(Integer, nullable=False)
    model_year: Mapped[int] = mapped_column(Integer, nullable=False)
    vin: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    current_location: Mapped[str] = mapped_column(String(120), nullable=False)
```

- [ ] **Step 4: Create `app/src/models/customers.py`**

```python
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(160), nullable=False)
    customer_type: Mapped[str] = mapped_column(String(40), nullable=False)
    credit_terms_days: Mapped[int] = mapped_column(Integer, nullable=False)
    primary_freight_type: Mapped[str] = mapped_column(String(60), nullable=False)
    account_status: Mapped[str] = mapped_column(String(20), nullable=False)
    contract_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    annual_revenue_potential: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
```

- [ ] **Step 5: Create `app/src/models/facilities.py`**

```python
from decimal import Decimal

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Facility(Base):
    __tablename__ = "facilities"

    facility_id: Mapped[int] = mapped_column(primary_key=True)
    facility_name: Mapped[str] = mapped_column(String(160), nullable=False)
    facility_type: Mapped[str] = mapped_column(String(40), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    dock_doors: Mapped[int] = mapped_column(Integer, nullable=False)
    operating_hours: Mapped[str] = mapped_column(String(80), nullable=False)
```

- [ ] **Step 6: Create `app/src/models/routes.py`**

```python
from decimal import Decimal

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Route(Base):
    __tablename__ = "routes"

    route_id: Mapped[int] = mapped_column(primary_key=True)
    origin_city: Mapped[str] = mapped_column(String(80), nullable=False)
    origin_state: Mapped[str] = mapped_column(String(2), nullable=False)
    destination_city: Mapped[str] = mapped_column(String(80), nullable=False)
    destination_state: Mapped[str] = mapped_column(String(2), nullable=False)
    typical_distance_miles: Mapped[int] = mapped_column(Integer, nullable=False)
    base_rate_per_mile: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    fuel_surcharge_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    typical_transit_days: Mapped[int] = mapped_column(Integer, nullable=False)
```

- [ ] **Step 7: Update `app/src/models/__init__.py`**

```python
from .base import Base
from .customers import Customer
from .drivers import Driver
from .facilities import Facility
from .routes import Route
from .trailers import Trailer
from .trucks import Truck
from .users import User

__all__ = [
    "Base",
    "Customer",
    "Driver",
    "Facility",
    "Route",
    "Trailer",
    "Truck",
    "User",
]
```

- [ ] **Step 8: Verify models import cleanly**

```bash
cd app && uv run python -c "from src.models import Base; print(sorted(Base.metadata.tables.keys()))"
```

Expected: `['customers', 'drivers', 'facilities', 'routes', 'trailers', 'trucks', 'users']`

- [ ] **Step 9: Commit**

```bash
git add app/src/models/
git commit -m "feat(models): add reference-entity domain models"
```

---

### Task 4: Domain models — loads + trips (with FK to references)

**Files:**
- Create: `app/src/models/loads.py`, `trips.py`
- Modify: `app/src/models/__init__.py`

- [ ] **Step 1: Create `app/src/models/loads.py`**

```python
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .customers import Customer
from .routes import Route


class Load(Base):
    __tablename__ = "loads"

    load_id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.customer_id"), index=True, nullable=False
    )
    route_id: Mapped[int] = mapped_column(
        ForeignKey("routes.route_id"), index=True, nullable=False
    )
    load_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    load_type: Mapped[str] = mapped_column(String(40), nullable=False)
    weight_lbs: Mapped[int] = mapped_column(Integer, nullable=False)
    pieces: Mapped[int] = mapped_column(Integer, nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fuel_surcharge: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    accessorial_charges: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    load_status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    booking_type: Mapped[str] = mapped_column(String(20), nullable=False)

    customer: Mapped[Customer] = relationship()
    route: Mapped[Route] = relationship()
```

- [ ] **Step 2: Create `app/src/models/trips.py`**

```python
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .drivers import Driver
from .loads import Load
from .trailers import Trailer
from .trucks import Truck


class Trip(Base):
    __tablename__ = "trips"

    trip_id: Mapped[int] = mapped_column(primary_key=True)
    load_id: Mapped[int] = mapped_column(
        ForeignKey("loads.load_id"), unique=True, index=True, nullable=False
    )
    driver_id: Mapped[int] = mapped_column(
        ForeignKey("drivers.driver_id"), index=True, nullable=False
    )
    truck_id: Mapped[int] = mapped_column(
        ForeignKey("trucks.truck_id"), index=True, nullable=False
    )
    trailer_id: Mapped[int] = mapped_column(
        ForeignKey("trailers.trailer_id"), index=True, nullable=False
    )
    dispatch_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_distance_miles: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_duration_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    fuel_gallons_used: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    average_mpg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    idle_time_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    trip_status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)

    load: Mapped[Load] = relationship()
    driver: Mapped[Driver] = relationship()
    truck: Mapped[Truck] = relationship()
    trailer: Mapped[Trailer] = relationship()
```

> Note the **deliberate design smell**: `Trip` is 1-to-1 with `Load` (enforced via `unique=True` on `load_id`). Spec calls this out as a future refactor talking point. **Do not** merge them into one table — that would defeat the demo.

> Note also: composite index `(driver_id, dispatch_date)` is **NOT** added here. That index is part of Bug A and will be added live during the workshop in `0006_perf_indexes.py` (migrations 0004 and 0005 are reserved for data-driven schema fixes added in Task 10 — nullable optional FKs, dropped trailer_number unique). Resist the urge to "be helpful" and add the composite now.

- [ ] **Step 3: Update `app/src/models/__init__.py`**

```python
from .base import Base
from .customers import Customer
from .drivers import Driver
from .facilities import Facility
from .loads import Load
from .routes import Route
from .trailers import Trailer
from .trips import Trip
from .trucks import Truck
from .users import User

__all__ = [
    "Base", "Customer", "Driver", "Facility", "Load", "Route",
    "Trailer", "Trip", "Truck", "User",
]
```

- [ ] **Step 4: Verify all 9 tables register**

```bash
cd app && uv run python -c "from src.models import Base; print(sorted(Base.metadata.tables.keys()))"
```

Expected: `['customers', 'drivers', 'facilities', 'loads', 'routes', 'trailers', 'trips', 'trucks', 'users']`

- [ ] **Step 5: Commit**

```bash
git add app/src/models/
git commit -m "feat(models): add loads and trips with FKs (1-to-1 trips↔loads by design)"
```

---

### Task 5: Domain models — events, fuel, maintenance, incidents

**Files:**
- Create: `app/src/models/fuel.py`, `maintenance.py`, `events.py`, `incidents.py`
- Modify: `app/src/models/__init__.py`

- [ ] **Step 1: Create `app/src/models/fuel.py`**

```python
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class FuelPurchase(Base):
    __tablename__ = "fuel_purchases"

    fuel_purchase_id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(
        ForeignKey("trips.trip_id"), index=True, nullable=False
    )
    truck_id: Mapped[int] = mapped_column(
        ForeignKey("trucks.truck_id"), index=True, nullable=False
    )
    driver_id: Mapped[int] = mapped_column(
        ForeignKey("drivers.driver_id"), index=True, nullable=False
    )
    purchase_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    location_city: Mapped[str] = mapped_column(String(80), nullable=False)
    location_state: Mapped[str] = mapped_column(String(2), nullable=False)
    gallons: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    price_per_gallon: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fuel_card_number: Mapped[str] = mapped_column(String(40), nullable=False)
```

- [ ] **Step 2: Create `app/src/models/maintenance.py`**

```python
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    maintenance_id: Mapped[int] = mapped_column(primary_key=True)
    truck_id: Mapped[int] = mapped_column(
        ForeignKey("trucks.truck_id"), index=True, nullable=False
    )
    maintenance_date: Mapped[date] = mapped_column(Date, nullable=False)
    maintenance_type: Mapped[str] = mapped_column(String(60), nullable=False)
    odometer_reading: Mapped[int] = mapped_column(Integer, nullable=False)
    labor_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    labor_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    parts_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    facility_location: Mapped[str] = mapped_column(String(120), nullable=False)
    downtime_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    service_description: Mapped[str] = mapped_column(String(255), nullable=False)
```

- [ ] **Step 3: Create `app/src/models/events.py`**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DeliveryEvent(Base):
    __tablename__ = "delivery_events"

    event_id: Mapped[int] = mapped_column(primary_key=True)
    load_id: Mapped[int] = mapped_column(
        ForeignKey("loads.load_id"), index=True, nullable=False
    )
    trip_id: Mapped[int] = mapped_column(
        ForeignKey("trips.trip_id"), index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    facility_id: Mapped[int] = mapped_column(
        ForeignKey("facilities.facility_id"), index=True, nullable=False
    )
    scheduled_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    actual_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    detention_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    on_time_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    location_city: Mapped[str] = mapped_column(String(80), nullable=False)
    location_state: Mapped[str] = mapped_column(String(2), nullable=False)
```

- [ ] **Step 4: Create `app/src/models/incidents.py`**

```python
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SafetyIncident(Base):
    __tablename__ = "safety_incidents"

    incident_id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(
        ForeignKey("trips.trip_id"), index=True, nullable=False
    )
    truck_id: Mapped[int] = mapped_column(
        ForeignKey("trucks.truck_id"), index=True, nullable=False
    )
    driver_id: Mapped[int] = mapped_column(
        ForeignKey("drivers.driver_id"), index=True, nullable=False
    )
    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    incident_type: Mapped[str] = mapped_column(String(60), nullable=False)
    location_city: Mapped[str] = mapped_column(String(80), nullable=False)
    location_state: Mapped[str] = mapped_column(String(2), nullable=False)
    at_fault_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    injury_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    vehicle_damage_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cargo_damage_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    claim_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    preventable_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
```

- [ ] **Step 5: Update `app/src/models/__init__.py`**

```python
from .base import Base
from .customers import Customer
from .drivers import Driver
from .events import DeliveryEvent
from .facilities import Facility
from .fuel import FuelPurchase
from .incidents import SafetyIncident
from .loads import Load
from .maintenance import MaintenanceRecord
from .routes import Route
from .trailers import Trailer
from .trips import Trip
from .trucks import Truck
from .users import User

__all__ = [
    "Base", "Customer", "DeliveryEvent", "Driver", "Facility",
    "FuelPurchase", "Load", "MaintenanceRecord", "Route",
    "SafetyIncident", "Trailer", "Trip", "Truck", "User",
]
```

- [ ] **Step 6: Verify all 13 tables register**

```bash
cd app && uv run python -c "from src.models import Base; print(sorted(Base.metadata.tables.keys()))"
```

Expected (13 entries):
```
['customers', 'delivery_events', 'drivers', 'facilities', 'fuel_purchases',
 'loads', 'maintenance_records', 'routes', 'safety_incidents', 'trailers',
 'trips', 'trucks', 'users']
```

- [ ] **Step 7: Commit**

```bash
git add app/src/models/
git commit -m "feat(models): add fuel, maintenance, delivery events, safety incidents"
```

---

### Task 6: Domain models — metrics (composite PK)

**Files:**
- Create: `app/src/models/metrics.py`
- Modify: `app/src/models/__init__.py`

- [ ] **Step 1: Create `app/src/models/metrics.py`**

```python
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DriverMonthlyMetrics(Base):
    __tablename__ = "driver_monthly_metrics"

    driver_id: Mapped[int] = mapped_column(
        ForeignKey("drivers.driver_id"), nullable=False
    )
    month: Mapped[date] = mapped_column(Date, nullable=False)
    trips_completed: Mapped[int] = mapped_column(Integer, nullable=False)
    total_miles: Mapped[int] = mapped_column(Integer, nullable=False)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    average_mpg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    total_fuel_gallons: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    on_time_delivery_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    average_idle_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("driver_id", "month", name="pk_driver_monthly_metrics"),
    )


class TruckUtilizationMetrics(Base):
    __tablename__ = "truck_utilization_metrics"

    truck_id: Mapped[int] = mapped_column(
        ForeignKey("trucks.truck_id"), nullable=False
    )
    month: Mapped[date] = mapped_column(Date, nullable=False)
    trips_completed: Mapped[int] = mapped_column(Integer, nullable=False)
    total_miles: Mapped[int] = mapped_column(Integer, nullable=False)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    average_mpg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    maintenance_events: Mapped[int] = mapped_column(Integer, nullable=False)
    maintenance_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    downtime_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    utilization_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("truck_id", "month", name="pk_truck_utilization_metrics"),
    )
```

- [ ] **Step 2: Update `app/src/models/__init__.py`**

Add to imports and `__all__`:
```python
from .metrics import DriverMonthlyMetrics, TruckUtilizationMetrics
```
And add `"DriverMonthlyMetrics", "TruckUtilizationMetrics"` to `__all__` (keep alphabetical).

- [ ] **Step 3: Verify all 15 tables register**

```bash
cd app && uv run python -c "from src.models import Base; print(sorted(Base.metadata.tables.keys()))"
```

Expected: 15 tables (14 domain + users).

- [ ] **Step 4: Commit**

```bash
git add app/src/models/
git commit -m "feat(models): add metrics tables with composite PKs"
```

---

### Task 7: Alembic migration 0001 — domain schema

**Files:**
- Modify: `app/alembic/env.py` (if needed, to load models)
- Create: `app/alembic/versions/0001_create_domain_schema.py`

- [ ] **Step 1: Verify `app/alembic/env.py` imports `Base.metadata`**

Open `app/alembic/env.py`. It should have something like `from src.models import Base; target_metadata = Base.metadata`. If it has `target_metadata = None`, fix it:

```python
# At top of file, after sys.path setup:
from src.models import Base

target_metadata = Base.metadata
```

- [ ] **Step 2: Generate the initial migration**

```bash
cd app && docker compose exec app alembic revision --autogenerate -m "create domain schema"
```

This produces a file like `app/alembic/versions/<hash>_create_domain_schema.py`. **Rename it** to `0001_create_domain_schema.py` and edit the file's `revision = "..."` to `revision = "0001"`, `down_revision = None`.

- [ ] **Step 3: Inspect the generated migration**

Open the renamed file. Verify it creates all 15 tables (14 domain + users) with correct columns and FKs. The auto-generation may have ordering issues — confirm tables that reference others (`loads` → `customers`, `routes`) are created after their dependencies.

- [ ] **Step 4: Apply migration locally**

```bash
just up
docker compose exec app alembic upgrade head
```

Expected: `Running upgrade  -> 0001, create domain schema`.

- [ ] **Step 5: Verify all tables exist in Postgres**

```bash
just psql -c "\dt"
```

Expected: list of 15 tables.

- [ ] **Step 6: Test downgrade**

```bash
docker compose exec app alembic downgrade base
just psql -c "\dt"
```

Expected: only `alembic_version` table remains.

Then re-upgrade:
```bash
docker compose exec app alembic upgrade head
```

- [ ] **Step 7: Commit**

```bash
git add app/alembic/
git commit -m "feat(db): migration 0001 — domain schema (15 tables)"
```

---

### Task 8: Alembic migration 0002 — users table + seed demo users

**Files:**
- Create: `app/alembic/versions/0002_create_users_and_seed_demo_users.py`

> Note: User table was actually created in 0001 as part of `Base.metadata` autogeneration. **Migration 0002 is users-only data seed** (bcrypt hashes). If 0001 did not include `users`, adjust accordingly — but in practice autogenerate picks up all `Base` subclasses.

- [ ] **Step 1: Generate hashed passwords**

Open a shell:
```bash
cd app && uv run python -c "
from passlib.context import CryptContext
ctx = CryptContext(schemes=['bcrypt'])
print('dispatcher:', ctx.hash('dispatcher123'))
print('viewer:', ctx.hash('viewer123'))
"
```

Copy the two hash strings — you'll paste them into the migration.

- [ ] **Step 2: Create `app/alembic/versions/0002_create_users_and_seed_demo_users.py`**

Replace `<DISPATCHER_HASH>` and `<VIEWER_HASH>` with the values from Step 1:

```python
"""seed demo users

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-17

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


DISPATCHER_HASH = "<DISPATCHER_HASH>"
VIEWER_HASH = "<VIEWER_HASH>"


def upgrade() -> None:
    users = sa.table(
        "users",
        sa.column("email", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("display_name", sa.String),
    )
    op.bulk_insert(
        users,
        [
            {"email": "dispatcher@example.com", "password_hash": DISPATCHER_HASH,
             "display_name": "Demo Dispatcher"},
            {"email": "viewer@example.com", "password_hash": VIEWER_HASH,
             "display_name": "Demo Viewer"},
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE email IN ('dispatcher@example.com', 'viewer@example.com')")
```

- [ ] **Step 3: Apply migration**

```bash
docker compose exec app alembic upgrade head
```

Expected: `Running upgrade 0001 -> 0002, seed demo users`.

- [ ] **Step 4: Verify users exist**

```bash
just psql -c "SELECT user_id, email, display_name FROM users;"
```

Expected: 2 rows.

- [ ] **Step 5: Commit**

```bash
git add app/alembic/versions/0002_create_users_and_seed_demo_users.py
git commit -m "feat(db): migration 0002 — seed demo users"
```

---

### Task 9: Alembic migration 0003 — baseline indexes (deliberately incomplete)

**Files:**
- Create: `app/alembic/versions/0003_indexes_baseline.py`

> This migration adds **only** the indexes already declared in models via `index=True` (which autogenerate produces) plus 1-2 "obvious" extras. It deliberately **omits** the composite `Trip(driver_id, dispatch_date)` index — that's Bug A.

- [ ] **Step 1: Generate autogenerate migration to see what's already covered**

```bash
docker compose exec app alembic revision --autogenerate -m "indexes baseline"
```

If autogenerate produces an **empty** migration (because `index=True` was already in the model's column declarations and `0001` picked them up), that's fine — the indexes are already in 0001. In that case, **skip Step 2-3** and instead create a minimal 0003 with the 2 explicit extras below.

If autogenerate produces a migration with index additions, proceed.

- [ ] **Step 2: Rename to `0003_indexes_baseline.py` and edit revisions**

Rename file and set `revision = "0003"`, `down_revision = "0002"`.

- [ ] **Step 3: Add the 2 deliberate extras**

In the `upgrade()` body, append:
```python
    # Obvious indexes on commonly-filtered columns
    op.create_index("ix_loads_load_date", "loads", ["load_date"])
    op.create_index("ix_deliv_events_event_type", "delivery_events", ["event_type"])
```

In `downgrade()`, prepend:
```python
    op.drop_index("ix_deliv_events_event_type", table_name="delivery_events")
    op.drop_index("ix_loads_load_date", table_name="loads")
```

- [ ] **Step 4: VERIFY that composite `(driver_id, dispatch_date)` is NOT present**

```bash
grep -i "driver_id.*dispatch_date\|dispatch_date.*driver_id" app/alembic/versions/0003_indexes_baseline.py
```

Expected: **no output**. If anything matches, **remove it** — that index is Bug A's fix and must not be in baseline.

- [ ] **Step 5: Apply migration**

```bash
docker compose exec app alembic upgrade head
```

Expected: `Running upgrade 0002 -> 0003, indexes baseline`.

- [ ] **Step 6: Verify indexes**

```bash
just psql -c "SELECT indexname FROM pg_indexes WHERE tablename = 'trips' ORDER BY indexname;"
```

Expected indexes on trips: `trips_pkey`, `ix_trips_load_id`, `ix_trips_driver_id`, `ix_trips_truck_id`, `ix_trips_trailer_id`, `ix_trips_trip_status`. **No** composite `(driver_id, dispatch_date)` — that's the design intent.

- [ ] **Step 7: Commit**

```bash
git add app/alembic/versions/0003_indexes_baseline.py
git commit -m "feat(db): migration 0003 — baseline indexes (intentionally missing composite for Bug A)"
```

---

### Task 10: CSV seed CLI

**Files:**
- Create: `app/src/scripts/__init__.py`
- Create: `app/src/scripts/seed_csv.py`
- Modify: `justfile`

- [ ] **Step 1: Create `app/src/scripts/__init__.py`** (empty)

- [ ] **Step 2: Create `app/src/scripts/seed_csv.py`**

```python
"""CSV seed CLI — loads app/data/*.csv into Postgres via COPY.

Usage:
    python -m src.scripts.seed_csv         # idempotent: no-op if data already loaded
    python -m src.scripts.seed_csv --reset # TRUNCATE 14 domain tables, then seed
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg
import typer

from src.config import settings

app = typer.Typer(add_completion=False)

# Load order matters — FK parents before children
LOAD_ORDER = [
    "drivers",
    "trucks",
    "trailers",
    "customers",
    "facilities",
    "routes",
    "loads",
    "trips",
    "fuel_purchases",
    "maintenance_records",
    "delivery_events",
    "safety_incidents",
    "driver_monthly_metrics",
    "truck_utilization_metrics",
]

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _build_dsn() -> str:
    # asyncpg accepts plain postgresql:// (no +asyncpg suffix)
    url = settings.database_url
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _table_has_data(conn: asyncpg.Connection, table: str) -> bool:
    row = await conn.fetchrow(f"SELECT 1 FROM {table} LIMIT 1")
    return row is not None


async def _truncate_all(conn: asyncpg.Connection) -> None:
    # Reverse order to respect FKs; CASCADE for safety
    for table in reversed(LOAD_ORDER):
        await conn.execute(f"TRUNCATE {table} RESTART IDENTITY CASCADE")


async def _copy_csv(conn: asyncpg.Connection, table: str) -> int:
    csv_path = DATA_DIR / f"{table}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"missing CSV: {csv_path}")

    with csv_path.open("rb") as f:
        result = await conn.copy_to_table(
            table_name=table,
            source=f,
            format="csv",
            header=True,
        )
    # asyncpg.copy_to_table returns a status string like "COPY 85410"
    count = int(result.split()[-1])
    return count


async def _seed(reset: bool) -> None:
    conn = await asyncpg.connect(_build_dsn())
    try:
        if not reset and await _table_has_data(conn, "trips"):
            typer.echo("data already seeded (trips not empty) — exiting (use --reset to force)")
            return

        if reset:
            typer.echo("--reset: TRUNCATE all 14 domain tables")
            await _truncate_all(conn)

        for table in LOAD_ORDER:
            count = await _copy_csv(conn, table)
            typer.echo(f"  {table:30} {count:>10,} rows")
        typer.echo("seed complete")
    finally:
        await conn.close()


@app.command()
def main(
    reset: bool = typer.Option(
        False, "--reset", help="TRUNCATE domain tables before seeding"
    ),
) -> None:
    """Load app/data/*.csv into Postgres via COPY."""
    asyncio.run(_seed(reset))


if __name__ == "__main__":
    app()
```

- [ ] **Step 3: Add justfile commands**

In `justfile`, after the existing `migrate-down:` block, add:
```
# Seed
seed-csv:
    docker compose exec app python -m src.scripts.seed_csv

seed-csv-reset:
    docker compose exec app python -m src.scripts.seed_csv --reset
```

- [ ] **Step 4: Run the seed**

```bash
just up
docker compose exec app alembic upgrade head
just seed-csv
```

Expected output (rows close to these — exact counts from CSV files):
```
  drivers                              150 rows
  trucks                               120 rows
  trailers                             180 rows
  customers                            200 rows
  facilities                            50 rows
  routes                                58 rows
  loads                             85,410 rows
  trips                             85,410 rows
  fuel_purchases                   196,442 rows
  maintenance_records                2,920 rows
  delivery_events                  170,820 rows
  safety_incidents                     170 rows
  driver_monthly_metrics             4,464 rows
  truck_utilization_metrics          3,312 rows
seed complete
```

Total ~1-2 minutes.

- [ ] **Step 5: Verify idempotency**

```bash
just seed-csv
```

Expected: `data already seeded (trips not empty) — exiting (use --reset to force)`.

- [ ] **Step 6: Verify reset**

```bash
just seed-csv-reset
```

Expected: TRUNCATE message + same row counts as Step 4.

- [ ] **Step 7: Commit**

```bash
git add app/src/scripts/ justfile
git commit -m "feat(scripts): CSV seed CLI for 14 domain tables (idempotent + reset)"
```

---

## Session 2 — Auth module + health refactor

### Task 11: Move health to its own module

**Files:**
- Create: `app/src/health/__init__.py`
- Create: `app/src/health/router.py`
- Delete: `app/src/routes/health.py`
- Delete: `app/src/routes/__init__.py`
- Modify: `app/src/main.py`

- [ ] **Step 1: Read current `app/src/routes/health.py` to preserve behaviour**

```bash
cat app/src/routes/health.py
```

Note the exact endpoints and their bodies — you must preserve them.

- [ ] **Step 2: Create `app/src/health/__init__.py`** (empty)

- [ ] **Step 3: Create `app/src/health/router.py`** with the same logic

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def readiness(session: AsyncSession = Depends(get_session)) -> dict:
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail={"status": "error", "db": "unreachable"})
```

If the existing `routes/health.py` does anything different (e.g., different status code shape), match it exactly.

- [ ] **Step 4: Update `app/src/main.py`**

Replace any `from src.routes.health import router as health_router` with `from src.health.router import router as health_router` (or whatever import alias was used). Keep `app.include_router(health_router)` line.

- [ ] **Step 5: Delete the old routes folder**

```bash
rm -r app/src/routes
```

- [ ] **Step 6: Verify the test still passes**

```bash
cd app && uv run pytest tests/test_health.py -v
```

Expected: 2 passed (live + ready).

- [ ] **Step 7: Commit**

```bash
git add app/src/health/ app/src/main.py
git rm app/src/routes/health.py app/src/routes/__init__.py
git commit -m "refactor: promote health to its own module for consistency"
```

---

### Task 12: Auth security utilities (password + JWT)

**Files:**
- Create: `app/src/auth/__init__.py`
- Create: `app/src/auth/security.py`
- Create: `app/tests/auth/__init__.py`
- Create: `app/tests/auth/test_security.py`

- [ ] **Step 1: Create `app/src/auth/__init__.py`** (empty)

- [ ] **Step 2: Create `app/src/auth/security.py`**

```python
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def issue_jwt(*, subject: str) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    expires_in_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, expires_in_minutes * 60


def decode_jwt(token: str) -> dict:
    """Raises jose.JWTError on invalid/expired token."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
```

- [ ] **Step 3: Create `app/tests/auth/__init__.py`** (empty)

- [ ] **Step 4: Write failing tests `app/tests/auth/test_security.py`**

```python
import time

import pytest
from jose import JWTError

from src.auth.security import (
    decode_jwt,
    hash_password,
    issue_jwt,
    verify_password,
)


def test_hash_then_verify_roundtrip():
    hashed = hash_password("hunter2")
    assert verify_password("hunter2", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_jwt_roundtrip():
    token, expires_in = issue_jwt(subject="alice@example.com")
    payload = decode_jwt(token)
    assert payload["sub"] == "alice@example.com"
    assert expires_in > 0


def test_jwt_tampered_signature_rejected():
    token, _ = issue_jwt(subject="alice@example.com")
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
    with pytest.raises(JWTError):
        decode_jwt(tampered)
```

- [ ] **Step 5: Run tests**

```bash
cd app && uv run pytest tests/auth/test_security.py -v
```

Expected: 3 passed. (Set `JWT_SECRET_KEY` in env if not already.)

- [ ] **Step 6: Commit**

```bash
git add app/src/auth/__init__.py app/src/auth/security.py app/tests/auth/
git commit -m "feat(auth): password hashing and JWT issuance utilities"
```

---

### Task 13: Auth service + dependencies + schemas

**Files:**
- Create: `app/src/auth/schemas.py`
- Create: `app/src/auth/service.py`
- Create: `app/src/auth/dependencies.py`

- [ ] **Step 1: Create `app/src/auth/schemas.py`**

```python
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUserResponse(BaseModel):
    user_id: int
    email: str
    display_name: str
```

- [ ] **Step 2: Create `app/src/auth/service.py`**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.security import issue_jwt, verify_password
from src.models import User


async def authenticate(session: AsyncSession, *, email: str, password: str) -> User | None:
    stmt = select(User).where(User.email == email)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def make_token_for(user: User) -> tuple[str, int]:
    return issue_jwt(subject=user.email)
```

- [ ] **Step 3: Create `app/src/auth/dependencies.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.security import decode_jwt
from src.db import get_session
from src.models import User

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        payload = decode_jwt(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
```

- [ ] **Step 4: Commit**

```bash
git add app/src/auth/schemas.py app/src/auth/service.py app/src/auth/dependencies.py
git commit -m "feat(auth): service, dependencies, and schemas"
```

---

### Task 14: Auth router (POST /auth/login) + wire into main

**Files:**
- Create: `app/src/auth/router.py`
- Modify: `app/src/main.py`

- [ ] **Step 1: Create `app/src/auth/router.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUserResponse, LoginRequest, TokenResponse
from src.auth.service import authenticate, make_token_for
from src.db import get_session
from src.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    user = await authenticate(session, email=body.email, password=body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token, expires_in = make_token_for(user)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=CurrentUserResponse)
async def me(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
    )
```

- [ ] **Step 2: Wire into `app/src/main.py`**

After `app.include_router(health_router)`, add:
```python
from src.auth.router import router as auth_router
app.include_router(auth_router)
```

- [ ] **Step 3: Smoke test manually**

```bash
just up
docker compose exec app alembic upgrade head
# Login
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dispatcher@example.com","password":"dispatcher123"}'
```

Expected: JSON with `access_token`, `token_type`, `expires_in`.

```bash
# /auth/me with bearer
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dispatcher@example.com","password":"dispatcher123"}' | jq -r .access_token)
curl -s http://localhost:8000/auth/me -H "Authorization: Bearer $TOKEN"
```

Expected: `{"user_id":1,"email":"dispatcher@example.com","display_name":"Demo Dispatcher"}`.

- [ ] **Step 4: Commit**

```bash
git add app/src/auth/router.py app/src/main.py
git commit -m "feat(auth): POST /auth/login and GET /auth/me, wired into main"
```

---

### Task 15: Auth integration tests

**Files:**
- Create: `app/tests/auth/test_login.py`
- Modify: `app/tests/conftest.py` (add JWT_SECRET_KEY for tests, fixtures)

- [ ] **Step 1: Inspect existing conftest**

```bash
cat app/tests/conftest.py
```

Note existing fixtures (likely a `client` and a DB session fixture).

- [ ] **Step 2: Ensure `JWT_SECRET_KEY` is set for tests**

In `app/tests/conftest.py`, near the top:
```python
import os
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-do-not-use")
```

If `conftest.py` already does env setup, add the `JWT_SECRET_KEY` line there.

- [ ] **Step 3: Add a `demo_users` fixture in conftest**

Add to `app/tests/conftest.py`:
```python
import pytest_asyncio
from sqlalchemy import select
from src.auth.security import hash_password
from src.models import User


@pytest_asyncio.fixture
async def demo_users(db_session):
    """Inserts dispatcher@example.com / dispatcher123 if missing."""
    existing = (await db_session.execute(
        select(User).where(User.email == "dispatcher@example.com")
    )).scalar_one_or_none()
    if existing is None:
        db_session.add(User(
            email="dispatcher@example.com",
            password_hash=hash_password("dispatcher123"),
            display_name="Test Dispatcher",
        ))
        await db_session.commit()
    yield
```

(Adapt to the existing session-fixture name — likely `db_session` or `session`.)

- [ ] **Step 4: Write failing tests `app/tests/auth/test_login.py`**

```python
import pytest


@pytest.mark.asyncio
async def test_login_returns_token(client, demo_users):
    resp = await client.post("/auth/login", json={
        "email": "dispatcher@example.com",
        "password": "dispatcher123",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client, demo_users):
    resp = await client.post("/auth/login", json={
        "email": "dispatcher@example.com",
        "password": "WRONG",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client, demo_users):
    resp = await client.post("/auth/login", json={
        "email": "nobody@example.com",
        "password": "any",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token_returns_401(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_token_returns_user(client, demo_users):
    login = await client.post("/auth/login", json={
        "email": "dispatcher@example.com",
        "password": "dispatcher123",
    })
    token = login.json()["access_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "dispatcher@example.com"
```

- [ ] **Step 5: Run tests**

```bash
cd app && uv run pytest tests/auth/ -v
```

Expected: 5 passed (plus the 3 from `test_security.py`).

- [ ] **Step 6: Commit**

```bash
git add app/tests/auth/ app/tests/conftest.py
git commit -m "test(auth): login + /auth/me integration tests"
```

---

## Session 3 — Drivers + Trips modules (planted bugs)

### Task 16: Drivers — list endpoint

**Files:**
- Create: `app/src/drivers/__init__.py`
- Create: `app/src/drivers/schemas.py`
- Create: `app/src/drivers/service.py`
- Create: `app/src/drivers/router.py`
- Modify: `app/src/main.py`

- [ ] **Step 1: Create `app/src/drivers/__init__.py`** (empty)

- [ ] **Step 2: Create `app/src/drivers/schemas.py`**

```python
from datetime import date

from pydantic import BaseModel, ConfigDict


class DriverListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    driver_id: int
    first_name: str
    last_name: str
    employment_status: str
    home_terminal: str
    years_experience: int
    cdl_class: str
    hire_date: date
```

- [ ] **Step 3: Create `app/src/drivers/service.py` (list portion)**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Driver


async def list_drivers(
    session: AsyncSession,
    *,
    status: str | None = None,
    terminal: str | None = None,
) -> list[Driver]:
    stmt = select(Driver).order_by(Driver.driver_id)
    if status:
        stmt = stmt.where(Driver.employment_status == status)
    if terminal:
        stmt = stmt.where(Driver.home_terminal == terminal)
    return list((await session.execute(stmt)).scalars().all())
```

- [ ] **Step 4: Create `app/src/drivers/router.py` (list portion)**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.db import get_session
from src.drivers.schemas import DriverListItem
from src.drivers.service import list_drivers
from src.models import User

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.get("", response_model=list[DriverListItem])
async def get_drivers(
    status: str | None = None,
    terminal: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[DriverListItem]:
    drivers = await list_drivers(session, status=status, terminal=terminal)
    return [DriverListItem.model_validate(d) for d in drivers]
```

- [ ] **Step 5: Wire into `main.py`**

```python
from src.drivers.router import router as drivers_router
app.include_router(drivers_router)
```

- [ ] **Step 6: Smoke test**

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dispatcher@example.com","password":"dispatcher123"}' | jq -r .access_token)
curl -s http://localhost:8000/drivers?status=ACTIVE \
  -H "Authorization: Bearer $TOKEN" | jq '.[0:3]'
```

Expected: array of 3 drivers with `employment_status: "ACTIVE"`.

- [ ] **Step 7: Commit**

```bash
git add app/src/drivers/ app/src/main.py
git commit -m "feat(drivers): GET /drivers list with status/terminal filters"
```

---

### Task 17: Drivers — `/drivers/{id}/dashboard` (Bug B planted)

**Files:**
- Modify: `app/src/drivers/schemas.py`
- Modify: `app/src/drivers/service.py`
- Modify: `app/src/drivers/router.py`

> **Bug B intent:** 3 issues planted in the service function — N+1 across recent_trips for load/customer/route, N+1 per-trip events fetch for on_time, and inline metrics compute that ignores `driver_monthly_metrics` table. Do NOT use `selectinload` here. Do NOT use the metrics table. The bugs must look like "the natural first attempt by a junior engineer".

- [ ] **Step 1: Extend `app/src/drivers/schemas.py`**

Append:
```python
from datetime import date as _date_alias
from decimal import Decimal


class DashboardTrip(BaseModel):
    trip_id: int
    dispatch_date: _date_alias
    customer_name: str
    route_summary: str
    distance_miles: int
    on_time: bool | None


class DashboardMetrics(BaseModel):
    trips_completed: int
    total_miles: int
    on_time_delivery_rate: float
    average_mpg: float


class DriverDashboardResponse(BaseModel):
    driver: DriverListItem
    recent_trips: list[DashboardTrip]
    current_month_metrics: DashboardMetrics
    open_incidents_count: int
```

- [ ] **Step 2: Add dashboard logic to `app/src/drivers/service.py`**

```python
from datetime import date, timedelta
from sqlalchemy import func

from src.models import (
    Customer,
    DeliveryEvent,
    Driver,
    Load,
    Route,
    SafetyIncident,
    Trip,
)


async def get_driver_or_404(session: AsyncSession, driver_id: int) -> Driver:
    driver = await session.get(Driver, driver_id)
    if driver is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="driver not found")
    return driver


async def build_driver_dashboard(
    session: AsyncSession,
    driver_id: int,
    *,
    since: date | None = None,
) -> dict:
    """Builds dashboard payload.

    NOTE: This is the 'naive first implementation'. Performance issues live here.
    """
    driver = await get_driver_or_404(session, driver_id)

    if since is None:
        since = date.today() - timedelta(days=30)

    # Recent trips
    trips_stmt = (
        select(Trip)
        .where((Trip.driver_id == driver_id) & (Trip.dispatch_date >= since))
        .order_by(Trip.dispatch_date.desc())
        .limit(20)
    )
    recent_trips = list((await session.execute(trips_stmt)).scalars().all())

    recent_payload = []
    for t in recent_trips:
        # N+1 on load / customer / route per trip
        load = await session.get(Load, t.load_id)
        customer = await session.get(Customer, load.customer_id)
        route = await session.get(Route, load.route_id)

        # N+1 on events for on_time compute per trip
        events = list((await session.execute(
            select(DeliveryEvent).where(DeliveryEvent.trip_id == t.trip_id)
        )).scalars().all())
        on_time: bool | None = all(e.on_time_flag for e in events) if events else None

        recent_payload.append({
            "trip_id": t.trip_id,
            "dispatch_date": t.dispatch_date,
            "customer_name": customer.customer_name,
            "route_summary": (
                f"{route.origin_city}, {route.origin_state} → "
                f"{route.destination_city}, {route.destination_state}"
            ),
            "distance_miles": t.actual_distance_miles,
            "on_time": on_time,
        })

    # Current month metrics — inline from raw, ignoring driver_monthly_metrics
    today = date.today()
    month_start = today.replace(day=1)
    month_trips_stmt = select(Trip).where(
        (Trip.driver_id == driver_id) & (Trip.dispatch_date >= month_start)
    )
    month_trips = list((await session.execute(month_trips_stmt)).scalars().all())

    total_miles = sum(t.actual_distance_miles for t in month_trips)
    if month_trips:
        avg_mpg = float(sum(t.average_mpg for t in month_trips) / len(month_trips))
    else:
        avg_mpg = 0.0

    on_time_rate = 0.0
    if month_trips:
        events_stmt = select(DeliveryEvent).where(
            DeliveryEvent.trip_id.in_([t.trip_id for t in month_trips])
        )
        all_events = list((await session.execute(events_stmt)).scalars().all())
        if all_events:
            on_time_count = sum(1 for e in all_events if e.on_time_flag)
            on_time_rate = on_time_count / len(all_events)

    incidents_count = (await session.execute(
        select(func.count(SafetyIncident.incident_id)).where(
            SafetyIncident.driver_id == driver_id
        )
    )).scalar_one()

    return {
        "driver": driver,
        "recent_trips": recent_payload,
        "current_month_metrics": {
            "trips_completed": len(month_trips),
            "total_miles": total_miles,
            "on_time_delivery_rate": on_time_rate,
            "average_mpg": avg_mpg,
        },
        "open_incidents_count": incidents_count,
    }
```

- [ ] **Step 3: Add route to `app/src/drivers/router.py`**

```python
from datetime import date as _date

from src.drivers.schemas import (
    DashboardMetrics,
    DashboardTrip,
    DriverDashboardResponse,
    DriverListItem,
)
from src.drivers.service import build_driver_dashboard


@router.get("/{driver_id}/dashboard", response_model=DriverDashboardResponse)
async def driver_dashboard(
    driver_id: int,
    since: _date | None = None,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> DriverDashboardResponse:
    data = await build_driver_dashboard(session, driver_id, since=since)
    return DriverDashboardResponse(
        driver=DriverListItem.model_validate(data["driver"]),
        recent_trips=[DashboardTrip(**t) for t in data["recent_trips"]],
        current_month_metrics=DashboardMetrics(**data["current_month_metrics"]),
        open_incidents_count=data["open_incidents_count"],
    )
```

- [ ] **Step 4: Manual smoke test (functional, not perf)**

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dispatcher@example.com","password":"dispatcher123"}' | jq -r .access_token)
time curl -s http://localhost:8000/drivers/1/dashboard \
  -H "Authorization: Bearer $TOKEN" | jq 'keys, (.recent_trips | length)'
```

Expected: 200 OK with `["current_month_metrics","driver","open_incidents_count","recent_trips"]` and recent_trips length 0-20. Timing 500-1500ms — **slow on purpose**.

- [ ] **Step 5: Commit**

```bash
git add app/src/drivers/
git commit -m "feat(drivers): GET /drivers/{id}/dashboard with naive implementation"
```

---

### Task 18: Trips — `/trips/{id}` detail (clean)

**Files:**
- Create: `app/src/trips/__init__.py`, `schemas.py`, `service.py`, `router.py`
- Create: `app/tests/trips/__init__.py`, `test_trip_detail.py`
- Modify: `app/src/main.py`

- [ ] **Step 1: Create empty `app/src/trips/__init__.py`** and `app/tests/trips/__init__.py`

- [ ] **Step 2: Create `app/src/trips/schemas.py`**

```python
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CustomerNested(BaseModel):
    customer_id: int
    customer_name: str


class LoadNested(BaseModel):
    load_id: int
    load_type: str
    weight_lbs: int
    pieces: int
    revenue: Decimal
    load_status: str
    customer: CustomerNested


class DriverNested(BaseModel):
    driver_id: int
    name: str


class TruckNested(BaseModel):
    truck_id: int
    unit_number: str


class TrailerNested(BaseModel):
    trailer_id: int
    trailer_number: str


class RouteNested(BaseModel):
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str


class FuelSummary(BaseModel):
    purchases_count: int
    total_gallons: Decimal
    total_cost: Decimal


class TripDetailResponse(BaseModel):
    trip_id: int
    dispatch_date: date
    actual_distance_miles: int
    trip_status: str
    load: LoadNested
    driver: DriverNested
    truck: TruckNested
    trailer: TrailerNested
    route: RouteNested
    fuel_summary: FuelSummary
    delivery_events_count: int
```

- [ ] **Step 3: Create `app/src/trips/service.py` (detail portion — CLEAN)**

```python
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import (
    Customer,
    DeliveryEvent,
    FuelPurchase,
    Load,
    Route,
    Trip,
)


async def get_trip_detail(session: AsyncSession, trip_id: int) -> dict:
    trip_stmt = (
        select(Trip)
        .where(Trip.trip_id == trip_id)
        .options(
            selectinload(Trip.load).selectinload(Load.customer),
            selectinload(Trip.load).selectinload(Load.route),
            selectinload(Trip.driver),
            selectinload(Trip.truck),
            selectinload(Trip.trailer),
        )
    )
    trip = (await session.execute(trip_stmt)).scalar_one_or_none()
    if trip is None:
        raise HTTPException(status_code=404, detail="trip not found")

    fuel_stmt = select(
        func.count(FuelPurchase.fuel_purchase_id),
        func.coalesce(func.sum(FuelPurchase.gallons), 0),
        func.coalesce(func.sum(FuelPurchase.total_cost), 0),
    ).where(FuelPurchase.trip_id == trip_id)
    purchases_count, total_gallons, total_cost = (
        await session.execute(fuel_stmt)
    ).one()

    events_count = (await session.execute(
        select(func.count(DeliveryEvent.event_id)).where(DeliveryEvent.trip_id == trip_id)
    )).scalar_one()

    return {
        "trip": trip,
        "load": trip.load,
        "customer": trip.load.customer,
        "route": trip.load.route,
        "driver": trip.driver,
        "truck": trip.truck,
        "trailer": trip.trailer,
        "fuel": {
            "purchases_count": int(purchases_count),
            "total_gallons": Decimal(total_gallons),
            "total_cost": Decimal(total_cost),
        },
        "events_count": int(events_count),
    }
```

- [ ] **Step 4: Create `app/src/trips/router.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.db import get_session
from src.models import User
from src.trips.schemas import (
    CustomerNested,
    DriverNested,
    FuelSummary,
    LoadNested,
    RouteNested,
    TrailerNested,
    TripDetailResponse,
    TruckNested,
)
from src.trips.service import get_trip_detail

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("/{trip_id}", response_model=TripDetailResponse)
async def trip_detail(
    trip_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> TripDetailResponse:
    data = await get_trip_detail(session, trip_id)
    trip = data["trip"]
    return TripDetailResponse(
        trip_id=trip.trip_id,
        dispatch_date=trip.dispatch_date,
        actual_distance_miles=trip.actual_distance_miles,
        trip_status=trip.trip_status,
        load=LoadNested(
            load_id=data["load"].load_id,
            load_type=data["load"].load_type,
            weight_lbs=data["load"].weight_lbs,
            pieces=data["load"].pieces,
            revenue=data["load"].revenue,
            load_status=data["load"].load_status,
            customer=CustomerNested(
                customer_id=data["customer"].customer_id,
                customer_name=data["customer"].customer_name,
            ),
        ),
        driver=DriverNested(
            driver_id=data["driver"].driver_id,
            name=f"{data['driver'].first_name} {data['driver'].last_name}",
        ),
        truck=TruckNested(
            truck_id=data["truck"].truck_id,
            unit_number=data["truck"].unit_number,
        ),
        trailer=TrailerNested(
            trailer_id=data["trailer"].trailer_id,
            trailer_number=data["trailer"].trailer_number,
        ),
        route=RouteNested(
            origin_city=data["route"].origin_city,
            origin_state=data["route"].origin_state,
            destination_city=data["route"].destination_city,
            destination_state=data["route"].destination_state,
        ),
        fuel_summary=FuelSummary(**data["fuel"]),
        delivery_events_count=data["events_count"],
    )
```

- [ ] **Step 5: Wire into main.py**

```python
from src.trips.router import router as trips_router
app.include_router(trips_router)
```

- [ ] **Step 6: Write test `app/tests/trips/test_trip_detail.py`**

```python
import pytest


@pytest.mark.asyncio
async def test_trip_detail_returns_full_shape(authed_client, sample_trip_id):
    resp = await authed_client.get(f"/trips/{sample_trip_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) >= {
        "trip_id", "dispatch_date", "load", "driver", "truck",
        "trailer", "route", "fuel_summary", "delivery_events_count",
    }
    assert body["load"]["customer"]["customer_id"] > 0


@pytest.mark.asyncio
async def test_trip_detail_404_for_unknown(authed_client):
    resp = await authed_client.get("/trips/99999999")
    assert resp.status_code == 404
```

> The `authed_client` and `sample_trip_id` fixtures don't yet exist. Add them in Step 7.

- [ ] **Step 7: Extend conftest with `authed_client` and `sample_trip_id`**

In `app/tests/conftest.py`, append:
```python
import pytest_asyncio


@pytest_asyncio.fixture
async def authed_client(client, demo_users):
    """HTTP client with Authorization header pre-set."""
    login = await client.post("/auth/login", json={
        "email": "dispatcher@example.com",
        "password": "dispatcher123",
    })
    token = login.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest_asyncio.fixture
async def sample_trip_id(db_session):
    """Returns the smallest existing trip_id, inserting a minimal fixture if DB is empty."""
    from sqlalchemy import select
    from src.models import (
        Customer, Driver, Load, Route, Trailer, Trip, Truck
    )
    existing = (await db_session.execute(
        select(Trip.trip_id).order_by(Trip.trip_id).limit(1)
    )).scalar_one_or_none()
    if existing:
        return existing

    # Minimal fixture setup
    customer = Customer(
        customer_id=1, customer_name="Test Co", customer_type="3PL",
        credit_terms_days=30, primary_freight_type="Dry Van",
        account_status="ACTIVE", contract_start_date="2025-01-01",
        annual_revenue_potential=100000,
    )
    route = Route(
        route_id=1, origin_city="Atlanta", origin_state="GA",
        destination_city="Dallas", destination_state="TX",
        typical_distance_miles=800, base_rate_per_mile=2.5,
        fuel_surcharge_rate=0.4, typical_transit_days=2,
    )
    driver = Driver(
        driver_id=1, first_name="A", last_name="B", hire_date="2020-01-01",
        license_number="L1", license_state="GA", date_of_birth="1980-01-01",
        home_terminal="Atlanta", employment_status="ACTIVE", cdl_class="A",
        years_experience=5,
    )
    truck = Truck(
        truck_id=1, unit_number="T1", make="Freightliner", model_year=2021,
        vin="V1", acquisition_date="2021-01-01", acquisition_mileage=0,
        fuel_type="Diesel", tank_capacity_gallons=200, status="ACTIVE",
        home_terminal="Atlanta",
    )
    trailer = Trailer(
        trailer_id=1, trailer_number="TR1", trailer_type="Dry Van",
        length_feet=53, model_year=2021, vin="VT1",
        acquisition_date="2021-01-01", status="ACTIVE", current_location="Atlanta",
    )
    load = Load(
        load_id=1, customer_id=1, route_id=1, load_date="2026-01-15",
        load_type="FTL", weight_lbs=40000, pieces=10, revenue=2000,
        fuel_surcharge=100, accessorial_charges=0, load_status="DELIVERED",
        booking_type="CONTRACT",
    )
    trip = Trip(
        trip_id=1, load_id=1, driver_id=1, truck_id=1, trailer_id=1,
        dispatch_date="2026-01-15", actual_distance_miles=800,
        actual_duration_hours=14, fuel_gallons_used=120, average_mpg=6.7,
        idle_time_hours=2, trip_status="COMPLETED",
    )
    db_session.add_all([customer, route, driver, truck, trailer, load, trip])
    await db_session.commit()
    return 1
```

- [ ] **Step 8: Run tests**

```bash
cd app && uv run pytest tests/trips/ -v
```

Expected: 2 passed.

- [ ] **Step 9: Commit**

```bash
git add app/src/trips/__init__.py app/src/trips/schemas.py app/src/trips/service.py app/src/trips/router.py app/src/main.py app/tests/trips/ app/tests/conftest.py
git commit -m "feat(trips): GET /trips/{id} detail endpoint with full test"
```

---

### Task 19: Trips — `POST /trips/search` (Bug A planted)

**Files:**
- Modify: `app/src/trips/schemas.py`
- Modify: `app/src/trips/service.py`
- Modify: `app/src/trips/router.py`

> **Bug A intent:** 4 issues planted — missing composite index reliance (the index does not exist; query naturally scans), Python-side filters for min/max_distance, N+1 across destination_state / load_status filter (per-trip db.get of Load+Route), and N+1 result enrichment. Do NOT use selectinload. Do NOT push min/max filters to SQL. Keep code "natural-looking".

- [ ] **Step 1: Extend `app/src/trips/schemas.py`**

Append:
```python
class TripSearchRequest(BaseModel):
    driver_ids: list[int] | None = None
    truck_ids: list[int] | None = None
    load_status: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    destination_state: str | None = None
    min_distance: int | None = None
    max_distance: int | None = None
    limit: int = 20
    offset: int = 0


class TripSearchItem(BaseModel):
    trip_id: int
    dispatch_date: date
    driver_name: str
    truck_unit: str
    route_summary: str
    distance_miles: int
    trip_status: str


class TripSearchResponse(BaseModel):
    total: int
    items: list[TripSearchItem]
```

- [ ] **Step 2: Add search logic to `app/src/trips/service.py`**

```python
from src.models import Driver, Truck


async def search_trips(
    session: AsyncSession,
    *,
    driver_ids: list[int] | None = None,
    truck_ids: list[int] | None = None,
    load_status: str | None = None,
    date_from=None,
    date_to=None,
    destination_state: str | None = None,
    min_distance: int | None = None,
    max_distance: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Search trips with filters. Naive implementation — Bug A lives here."""
    stmt = select(Trip)
    if driver_ids:
        stmt = stmt.where(Trip.driver_id.in_(driver_ids))
    if truck_ids:
        stmt = stmt.where(Trip.truck_id.in_(truck_ids))
    if date_from is not None:
        stmt = stmt.where(Trip.dispatch_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Trip.dispatch_date <= date_to)

    trips = list((await session.execute(stmt)).scalars().all())

    # Python-side filter for distance
    if min_distance is not None:
        trips = [t for t in trips if t.actual_distance_miles >= min_distance]
    if max_distance is not None:
        trips = [t for t in trips if t.actual_distance_miles <= max_distance]

    # destination_state / load_status via per-trip db.get
    if destination_state or load_status:
        filtered = []
        for t in trips:
            load = await session.get(Load, t.load_id)
            route = await session.get(Route, load.route_id)
            if destination_state and route.destination_state != destination_state:
                continue
            if load_status and load.load_status != load_status:
                continue
            filtered.append(t)
        trips = filtered

    total = len(trips)
    page = trips[offset : offset + limit]

    # Result enrichment — N+1 (driver, truck, load, route per item)
    items = []
    for t in page:
        load = await session.get(Load, t.load_id)
        route = await session.get(Route, load.route_id)
        driver = await session.get(Driver, t.driver_id)
        truck = await session.get(Truck, t.truck_id)
        items.append({
            "trip_id": t.trip_id,
            "dispatch_date": t.dispatch_date,
            "driver_name": f"{driver.first_name} {driver.last_name}",
            "truck_unit": truck.unit_number,
            "route_summary": (
                f"{route.origin_city}, {route.origin_state} → "
                f"{route.destination_city}, {route.destination_state}"
            ),
            "distance_miles": t.actual_distance_miles,
            "trip_status": t.trip_status,
        })

    return {"total": total, "items": items}
```

- [ ] **Step 3: Add route to `app/src/trips/router.py`**

```python
from src.trips.schemas import TripSearchItem, TripSearchRequest, TripSearchResponse
from src.trips.service import search_trips


@router.post("/search", response_model=TripSearchResponse)
async def trips_search(
    body: TripSearchRequest,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> TripSearchResponse:
    data = await search_trips(
        session,
        driver_ids=body.driver_ids,
        truck_ids=body.truck_ids,
        load_status=body.load_status,
        date_from=body.date_from,
        date_to=body.date_to,
        destination_state=body.destination_state,
        min_distance=body.min_distance,
        max_distance=body.max_distance,
        limit=body.limit,
        offset=body.offset,
    )
    return TripSearchResponse(
        total=data["total"],
        items=[TripSearchItem(**i) for i in data["items"]],
    )
```

- [ ] **Step 4: Manual functional smoke test**

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" \
  -d '{"email":"dispatcher@example.com","password":"dispatcher123"}' | jq -r .access_token)

time curl -s -X POST http://localhost:8000/trips/search \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"date_from":"2024-01-01","date_to":"2024-12-31","limit":20}' \
  | jq '.total, (.items | length)'
```

Expected: 200 OK, total > 0, items length ≤ 20. Single-request timing 200-800ms. **Performance issues will only surface under concurrent load** (perf script). Functional behavior is correct.

- [ ] **Step 5: Commit**

```bash
git add app/src/trips/
git commit -m "feat(trips): POST /trips/search with rich filter set (naive implementation)"
```

---

## Session 4 — Loads + Reports + Perf script

### Task 20: Loads module — GET /loads/upcoming

**Files:**
- Create: `app/src/loads/__init__.py`, `schemas.py`, `service.py`, `router.py`
- Modify: `app/src/main.py`

- [ ] **Step 1: Create empty `app/src/loads/__init__.py`**

- [ ] **Step 2: Create `app/src/loads/schemas.py`**

```python
from datetime import date

from pydantic import BaseModel


class UpcomingLoadItem(BaseModel):
    load_id: int
    customer_name: str
    route_summary: str
    weight_lbs: int
    load_status: str
    load_date: date
```

- [ ] **Step 3: Create `app/src/loads/service.py`**

```python
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Load


async def list_upcoming(
    session: AsyncSession, *, days: int = 3
) -> list[Load]:
    today = date.today()
    end = today + timedelta(days=days)
    stmt = (
        select(Load)
        .where((Load.load_date >= today) & (Load.load_date <= end))
        .order_by(Load.load_date.asc())
        .options(
            selectinload(Load.customer),
            selectinload(Load.route),
        )
    )
    return list((await session.execute(stmt)).scalars().all())
```

- [ ] **Step 4: Create `app/src/loads/router.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.db import get_session
from src.loads.schemas import UpcomingLoadItem
from src.loads.service import list_upcoming
from src.models import User

router = APIRouter(prefix="/loads", tags=["loads"])


@router.get("/upcoming", response_model=list[UpcomingLoadItem])
async def upcoming(
    days: int = 3,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[UpcomingLoadItem]:
    loads = await list_upcoming(session, days=days)
    return [
        UpcomingLoadItem(
            load_id=l.load_id,
            customer_name=l.customer.customer_name,
            route_summary=(
                f"{l.route.origin_city}, {l.route.origin_state} → "
                f"{l.route.destination_city}, {l.route.destination_state}"
            ),
            weight_lbs=l.weight_lbs,
            load_status=l.load_status,
            load_date=l.load_date,
        )
        for l in loads
    ]
```

- [ ] **Step 5: Wire into main.py**

```python
from src.loads.router import router as loads_router
app.include_router(loads_router)
```

- [ ] **Step 6: Smoke test**

```bash
curl -s http://localhost:8000/loads/upcoming -H "Authorization: Bearer $TOKEN" | jq 'length'
```

Expected: integer (could be 0 if no loads in next 3 days within seeded data — that's fine for our 2024 dataset; query at least doesn't error).

- [ ] **Step 7: Commit**

```bash
git add app/src/loads/ app/src/main.py
git commit -m "feat(loads): GET /loads/upcoming with N-day window"
```

---

### Task 21: Reports module — GET /reports/fleet-utilization

**Files:**
- Create: `app/src/reports/__init__.py`, `schemas.py`, `service.py`, `router.py`
- Create: `app/tests/reports/__init__.py`, `test_fleet_utilization.py`
- Modify: `app/src/main.py`

- [ ] **Step 1: Create empty `app/src/reports/__init__.py`** and `app/tests/reports/__init__.py`

- [ ] **Step 2: Create `app/src/reports/schemas.py`**

```python
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TruckUtilizationItem(BaseModel):
    truck_id: int
    unit_number: str
    trips_completed: int
    total_miles: int
    average_mpg: Decimal
    utilization_rate: Decimal
    maintenance_cost: Decimal


class FleetUtilizationResponse(BaseModel):
    month: str
    trucks: list[TruckUtilizationItem]
    data_computed_at: datetime
```

- [ ] **Step 3: Create `app/src/reports/service.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Truck, TruckUtilizationMetrics


async def fleet_utilization(session: AsyncSession, *, month: str) -> dict:
    """Look up monthly truck utilization from pre-aggregated table.

    Note: this table is populated by an out-of-band refresh job (not implemented).
    If current month is requested, data may be stale or empty — return what's there
    honestly via data_computed_at.
    """
    from datetime import date
    month_date = date.fromisoformat(f"{month}-01")

    stmt = (
        select(TruckUtilizationMetrics, Truck.unit_number)
        .join(Truck, Truck.truck_id == TruckUtilizationMetrics.truck_id)
        .where(TruckUtilizationMetrics.month == month_date)
        .order_by(TruckUtilizationMetrics.truck_id)
    )
    rows = (await session.execute(stmt)).all()

    trucks = [
        {
            "truck_id": m.truck_id,
            "unit_number": unit_number,
            "trips_completed": m.trips_completed,
            "total_miles": m.total_miles,
            "average_mpg": m.average_mpg,
            "utilization_rate": m.utilization_rate,
            "maintenance_cost": m.maintenance_cost,
        }
        for m, unit_number in rows
    ]

    # data_computed_at: last day of the month at 23:55 — honest representation
    # that this is a snapshot, not live data
    from calendar import monthrange
    last_day = monthrange(month_date.year, month_date.month)[1]
    computed_at = datetime(
        month_date.year, month_date.month, last_day, 23, 55, tzinfo=timezone.utc
    )

    return {"month": month, "trucks": trucks, "data_computed_at": computed_at}
```

- [ ] **Step 4: Create `app/src/reports/router.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.db import get_session
from src.models import User
from src.reports.schemas import FleetUtilizationResponse, TruckUtilizationItem
from src.reports.service import fleet_utilization

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/fleet-utilization", response_model=FleetUtilizationResponse)
async def fleet_utilization_report(
    month: str,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> FleetUtilizationResponse:
    data = await fleet_utilization(session, month=month)
    return FleetUtilizationResponse(
        month=data["month"],
        trucks=[TruckUtilizationItem(**t) for t in data["trucks"]],
        data_computed_at=data["data_computed_at"],
    )
```

- [ ] **Step 5: Wire into main.py**

```python
from src.reports.router import router as reports_router
app.include_router(reports_router)
```

- [ ] **Step 6: Write test `app/tests/reports/test_fleet_utilization.py`**

```python
import pytest


@pytest.mark.asyncio
async def test_fleet_utilization_returns_month_payload(authed_client, sample_truck_metric):
    resp = await authed_client.get("/reports/fleet-utilization?month=2024-06")
    assert resp.status_code == 200
    body = resp.json()
    assert body["month"] == "2024-06"
    assert "trucks" in body
    assert "data_computed_at" in body
```

- [ ] **Step 7: Add `sample_truck_metric` fixture to conftest**

In `app/tests/conftest.py`, append:
```python
@pytest_asyncio.fixture
async def sample_truck_metric(db_session, sample_trip_id):
    """Inserts a metric row for truck_id=1 / month=2024-06 if missing."""
    from datetime import date
    from sqlalchemy import select
    from src.models import TruckUtilizationMetrics

    existing = (await db_session.execute(
        select(TruckUtilizationMetrics).where(
            TruckUtilizationMetrics.truck_id == 1,
            TruckUtilizationMetrics.month == date(2024, 6, 1),
        )
    )).scalar_one_or_none()
    if existing:
        return existing

    metric = TruckUtilizationMetrics(
        truck_id=1, month=date(2024, 6, 1),
        trips_completed=15, total_miles=12000, total_revenue=30000,
        average_mpg=6.8, maintenance_events=2, maintenance_cost=500,
        downtime_hours=8, utilization_rate=0.65,
    )
    db_session.add(metric)
    await db_session.commit()
    return metric
```

- [ ] **Step 8: Run tests**

```bash
cd app && uv run pytest tests/reports/ -v
```

Expected: 1 passed.

- [ ] **Step 9: Commit**

```bash
git add app/src/reports/ app/src/main.py app/tests/reports/ app/tests/conftest.py
git commit -m "feat(reports): GET /reports/fleet-utilization with stale-data handling"
```

---

### Task 22: Perf load-test script + bodies

**Files:**
- Create: `perf/__init__.py`, `stress_trip_search.py`, `README.md`
- Create: `perf/bodies/__init__.py`, `trip_search_heavy.py`, `trip_search_light.py`
- Modify: `justfile`

- [ ] **Step 1: Create empty `perf/__init__.py`** and `perf/bodies/__init__.py`

- [ ] **Step 2: Create `perf/bodies/trip_search_heavy.py`**

```python
"""Heavy body: matches ~5K trips, exercises filter + N+1 paths."""
TRIP_SEARCH_HEAVY = {
    "date_from": "2024-01-01",
    "date_to": "2024-06-30",
    "destination_state": "TX",
    "load_status": "DELIVERED",
    "min_distance": 200,
    "max_distance": 1500,
    "limit": 20,
    "offset": 0,
}
```

- [ ] **Step 3: Create `perf/bodies/trip_search_light.py`**

```python
"""Light body: narrow filters, ~50 trips, sanity check."""
TRIP_SEARCH_LIGHT = {
    "driver_ids": [1, 2, 3],
    "date_from": "2024-01-01",
    "date_to": "2024-01-31",
    "limit": 20,
    "offset": 0,
}
```

- [ ] **Step 4: Create `perf/stress_trip_search.py`**

```python
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

ENV_CONFIG = {
    "local": {"url": "http://localhost:8000", "latency_offset": 0.0},
    "aws":   {"url": os.environ.get("STRESS_TARGET_URL", ""), "latency_offset": 0.05},
}

DEMO_EMAIL = "dispatcher@example.com"
DEMO_PASSWORD = "dispatcher123"


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
    session: aiohttp.ClientSession,
    url: str,
    headers: dict,
    body: str,
) -> None:
    async with sem:
        start = time.perf_counter()
        async with session.post(url, headers=headers, data=body) as resp:
            await resp.read()
            if resp.status != 200:
                raise RuntimeError(f"non-200: {resp.status}")
        latencies.append(time.perf_counter() - start)


async def stress(
    url: str,
    headers: dict,
    body: str,
    latencies: list,
    parallel: int,
    total: int,
    timeout_s: int = 120,
) -> None:
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    connector = aiohttp.TCPConnector(limit=parallel)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        sem = asyncio.Semaphore(parallel)
        tasks = [
            asyncio.create_task(send_request(sem, latencies, session, url, headers, body))
            for _ in range(total)
        ]
        await asyncio.gather(*tasks)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=list(ENV_CONFIG.keys()), default="local")
    args = parser.parse_args()

    cfg = ENV_CONFIG[args.env]
    base_url = cfg["url"]
    if not base_url:
        raise SystemExit(
            f"env={args.env}: base URL empty (set STRESS_TARGET_URL for aws)"
        )

    network_offset = cfg["latency_offset"]
    url = f"{base_url}/trips/search"
    body = json.dumps(TRIP_SEARCH_HEAVY)

    # Login once
    async def _login_only() -> str:
        async with aiohttp.ClientSession() as s:
            return await login(s, base_url)
    token = asyncio.run(_login_only())
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    geos = [int(2 * 1.5 ** p) for p in range(8)]
    loops = [(p, p * 5) for p in geos]

    print("Will run stress test with (parallel, total) pairs:", loops)
    print(f"Subtracting {network_offset}s network offset from latencies")
    print("Warming up server...")
    asyncio.run(stress(url, headers, body, [], 5, 10))
    time.sleep(0.5)

    header = "total/parallel    " + "".join(f"{k:>7}" for k in ("time", "avg", "p95", "min", "max"))
    print(header)

    for parallel, total in loops:
        latencies: list[float] = []
        start = time.perf_counter()
        asyncio.run(stress(url, headers, body, latencies, parallel, total))
        elapsed = time.perf_counter() - start
        results = {
            "time": elapsed,
            "avg": statistics.mean(latencies),
            "p95": statistics.quantiles(latencies, n=20)[18],
            "min": min(latencies),
            "max": max(latencies),
        }
        for k in ("avg", "p95", "min", "max"):
            results[k] = max(0.0, results[k] - network_offset)
        row = f"{total}/{parallel:<14}" + "".join(f"{v:>6.2f}s" for v in results.values())
        print(row)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Create `perf/README.md`**

```markdown
# Perf load-test scripts

`stress_trip_search.py` exercises `POST /trips/search` under increasing concurrency,
reports `time/avg/p95/min/max` per `(total, parallel)` pair.

## Usage

Local:
    just perf-trip-search

Against AWS (auto-resolves IP from terraform state):
    just perf-trip-search-aws

Or manually:
    STRESS_TARGET_URL=http://1.2.3.4 uv run --project app python -m perf.stress_trip_search --env aws

## Bodies

- `bodies/trip_search_heavy.py` — broad filters, matches ~5K trips. Default.
- `bodies/trip_search_light.py` — narrow filters, sanity check.

## Expected baseline (before Bug A fix)

p95 grows visibly with concurrency on a t3.small:

    total/parallel    time   avg   p95   min   max
    10/2              ~1.2s  ~0.4s ~0.8s ~0.3s ~1.1s
    110/22            ~15s   ~1.8s ~3.5s ~0.4s ~5.8s

After the fix (composite index + push filters + selectinload enrichment):

    110/22            ~3s    ~0.1s ~0.05s ~0.02s ~0.2s
```

- [ ] **Step 6: Add justfile commands**

In `justfile`:
```
# Perf
perf-trip-search:
    uv run --project app python -m perf.stress_trip_search --env local

perf-trip-search-aws:
    @ip=$$(cd infra && tofu output -raw server_ip); \
        STRESS_TARGET_URL=http://$$ip uv run --project app python -m perf.stress_trip_search --env aws
```

- [ ] **Step 7: Local smoke test of the script**

```bash
just up
docker compose exec app alembic upgrade head
just seed-csv
just perf-trip-search
```

Expected: Table prints, last row shows p95 in the 0.5-3s range (Bug A working).

- [ ] **Step 8: Commit**

```bash
git add perf/ justfile
git commit -m "feat(perf): stress_trip_search.py + heavy/light bodies"
```

---

### Task 23: README + .env.example + spec polish

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/spec.md` (light touch)

- [ ] **Step 1: Update `README.md`** (top-level)

Replace its contents with:
```markdown
# sandbox-api

Logistics-dispatcher backend used as the demo project for an AI workshop on diagnosing
performance problems with Claude Code. See `docs/spec.md` for the baseline (phase 1)
spec and `docs/superpowers/specs/2026-05-17-phase2-workshop-content-design.md` for
the phase 2 (this) design.

## Quick start (local)

```bash
cp .env.example .env
# (edit JWT_SECRET_KEY at minimum)
just up
docker compose exec app alembic upgrade head
just seed-csv
```

Login:
```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dispatcher@example.com","password":"dispatcher123"}'
```

## Endpoints

Public:
- `GET /health/live`, `GET /health/ready`
- `POST /auth/login`

Protected (Bearer JWT):
- `GET /drivers` — list with status/terminal filters
- `GET /drivers/{id}/dashboard` — driver page with recent trips + month KPIs
- `POST /trips/search` — rich filter search (perf-target)
- `GET /trips/{id}` — trip detail
- `GET /loads/upcoming` — next N days
- `GET /reports/fleet-utilization?month=YYYY-MM` — pre-aggregated monthly report
- `GET /auth/me` — current user

## Common tasks

See `justfile` — `just up`, `just down`, `just logs`, `just test`, `just lint`,
`just seed-csv`, `just perf-trip-search`, etc.

## Deploy

Push to `main` triggers `.github/workflows/deploy.yml` (CI + build + SSH deploy
to AWS EC2 + smoke). Infra is provisioned via `Actions → Infra → Run workflow → apply`.
See `infra/README.md`.

## Adding a migration

```bash
just migrate "describe your change"
just migrate-up
```
```

- [ ] **Step 2: Verify `.env.example` already has JWT vars**

(Added in Task 1 — verify they're present.)
```bash
grep -E "JWT_SECRET_KEY|ACCESS_TOKEN_EXPIRE_MINUTES" .env.example
```

Expected: both lines present.

- [ ] **Step 3: Add a brief phase 2 note in `docs/spec.md`**

After the existing "## Контекст" section opening, append a note:
```markdown
> **Phase 2 status (2026-05-17):** baseline (this spec) is shipped. Active work is on
> phase 2 (dispatcher console) — see `docs/superpowers/specs/2026-05-17-phase2-workshop-content-design.md`
> for the full design. Endpoint catalog, models, and bugs intentionally planted for
> workshop demos live there, not here.
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/spec.md
git commit -m "docs: README rewrite for phase 2 + cross-link from spec.md"
```

---

## Session 5 — AWS deploy verify + bug verification

### Task 24: Push branch + verify CI green

**Files:** (no code changes — process steps)

- [ ] **Step 1: Verify local state is clean and all tests pass**

```bash
cd app && uv run pytest -v
```

Expected: all tests pass (auth, trips/detail, reports/fleet — drivers and loads have no tests by design).

- [ ] **Step 2: Run lint check**

```bash
cd app && uv run ruff check . && uv run ruff format --check .
```

Expected: no errors.

- [ ] **Step 3: Push branch and open PR**

```bash
git push -u origin phase2-impl
gh pr create --base main --head phase2-impl \
  --title "feat: phase 2 — dispatcher console with planted perf bugs" \
  --body "Implements phase 2 per docs/superpowers/specs/2026-05-17-phase2-workshop-content-design.md. Adds 14 models, 9 endpoints, JWT auth, CSV seed CLI, perf script, and 2 intentional perf bugs (Bug A in POST /trips/search, Bug B in GET /drivers/{id}/dashboard). See spec for full scope."
```

- [ ] **Step 4: Wait for CI to complete**

```bash
gh pr checks --watch
```

Expected: `ci` job green (lint + ruff format + pytest).

- [ ] **Step 5: Merge PR**

After CI green, merge via GitHub UI or:
```bash
gh pr merge --squash --delete-branch
```

This triggers `.github/workflows/deploy.yml` on `main`.

- [ ] **Step 6: Watch deploy workflow**

```bash
gh run watch
```

Expected: all 4 jobs green (`ci`, `build-and-push`, `deploy`, `smoke-test`).

---

### Task 25: Seed CSV on AWS + functional smoke

**Files:** (none — manual AWS verification)

- [ ] **Step 1: Get the server IP**

```bash
cd infra && tofu output -raw server_ip
# Or: cat the latest Infra workflow's summary
```

- [ ] **Step 2: Verify health endpoint**

```bash
SERVER_IP=$(cd infra && tofu output -raw server_ip)
curl -fsS "http://$SERVER_IP/health/ready"
```

Expected: `{"status":"ok","db":"ok"}`.

- [ ] **Step 3: Login should work without seeded CSV (users come from migration)**

```bash
curl -s -X POST "http://$SERVER_IP/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"dispatcher@example.com","password":"dispatcher123"}' | jq
```

Expected: JSON with `access_token`.

- [ ] **Step 4: Seed CSV on the AWS server via SSH**

```bash
ssh ubuntu@"$SERVER_IP" 'cd /opt/workshop && docker compose -f docker-compose.prod.yml exec -T app python -m src.scripts.seed_csv'
```

Expected: same table of row counts as local seed; ~2-3 minutes total.

- [ ] **Step 5: Verify CSV data via an endpoint**

```bash
TOKEN=$(curl -s -X POST "http://$SERVER_IP/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"dispatcher@example.com","password":"dispatcher123"}' | jq -r .access_token)
curl -s "http://$SERVER_IP/drivers?status=ACTIVE" -H "Authorization: Bearer $TOKEN" | jq '. | length'
```

Expected: > 0 (some number of active drivers from seeded data).

---

### Task 26: Verify Bug A reproduces on AWS

**Files:** (none — verification)

- [ ] **Step 1: Run perf script against AWS**

```bash
just perf-trip-search-aws
```

- [ ] **Step 2: Verify p95 numbers**

Inspect the output. Expected at `total/parallel = 110/22`:
- `p95` ≥ 1.0s
- `time` (total elapsed) ≥ 5s

If `p95 < 0.3s` on 22 parallel — Bug A is NOT reproducing. Investigate:
- Did `0003_indexes_baseline` accidentally add the composite index?
  ```bash
  ssh ubuntu@"$SERVER_IP" 'cd /opt/workshop && docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d sandbox_api -c "SELECT indexname FROM pg_indexes WHERE tablename = '\''trips'\'';"'
  ```
  None of the rows should contain both `driver_id` and `dispatch_date` together.
- Are the Python-side filters still in place?
  ```bash
  grep -A2 'min_distance' app/src/trips/service.py | head -10
  ```
  Should show the `[t for t in trips if ...]` lines.

- [ ] **Step 3: Record baseline numbers for workshop reference**

Save the output to `docs/workshop/perf-baseline-pre-fix.txt` for later comparison post-fix during demo.

```bash
just perf-trip-search-aws > docs/workshop/perf-baseline-pre-fix.txt 2>&1
```

---

### Task 27: Verify Bug B reproduces on AWS

**Files:** (none — verification)

- [ ] **Step 1: Time a dashboard request**

```bash
SERVER_IP=$(cd infra && tofu output -raw server_ip)
TOKEN=$(curl -s -X POST "http://$SERVER_IP/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"dispatcher@example.com","password":"dispatcher123"}' | jq -r .access_token)

for i in 1 2 3; do
  time curl -s "http://$SERVER_IP/drivers/$i/dashboard" \
    -H "Authorization: Bearer $TOKEN" > /dev/null
done
```

Expected: each call 500-2000ms. If <200ms — Bug B is not reproducing. Verify:
- N+1 in `service.py` is still present (no `selectinload` on the recent_trips loop)
- Inline metrics compute is still present (no use of `DriverMonthlyMetrics`)

- [ ] **Step 2: Record baseline timing**

```bash
{
  echo "=== Bug B baseline — /drivers/{id}/dashboard timings ==="
  for i in 1 2 3 4 5; do
    echo "driver $i:"
    time curl -s "http://$SERVER_IP/drivers/$i/dashboard" \
      -H "Authorization: Bearer $TOKEN" > /dev/null
    echo
  done
} 2>&1 | tee -a docs/workshop/perf-baseline-pre-fix.txt
```

---

### Task 28: Verify Bug C reproduces on AWS (bonus)

**Files:** (none — verification)

- [ ] **Step 1: Request fleet-utilization for current month**

```bash
CURRENT_MONTH=$(date +%Y-%m)
curl -s "http://$SERVER_IP/reports/fleet-utilization?month=$CURRENT_MONTH" \
  -H "Authorization: Bearer $TOKEN" | jq '.trucks | length, .data_computed_at'
```

Expected:
- `trucks` array length is 0 or very small (data not present for current month)
- `data_computed_at` is in the past (~last day of current month at 23:55)

This is Bug C — data refresh job doesn't exist. Workshop bonus demo material.

- [ ] **Step 2: Request fleet-utilization for a month that IS in the seeded data**

```bash
curl -s "http://$SERVER_IP/reports/fleet-utilization?month=2024-06" \
  -H "Authorization: Bearer $TOKEN" | jq '.trucks | length, .data_computed_at'
```

Expected: > 0 trucks, all populated. Confirms endpoint works on historical data.

---

### Task 29: Commit perf baseline + close phase 2

**Files:**
- Create: `docs/workshop/perf-baseline-pre-fix.txt`
- Modify: `docs/superpowers/plans/2026-05-17-phase2-dispatcher-console.md` (mark complete)

- [ ] **Step 1: Verify baseline file exists**

```bash
ls -lh docs/workshop/perf-baseline-pre-fix.txt
```

- [ ] **Step 2: Add a note linking to it from `docs/workshop/`**

If you maintain an index, link the file. Otherwise skip.

- [ ] **Step 3: Commit baseline**

```bash
git checkout -b phase2-perf-baseline
git add docs/workshop/perf-baseline-pre-fix.txt
git commit -m "docs(workshop): record pre-fix perf baseline for Bug A and Bug B reference"
git push -u origin phase2-perf-baseline
gh pr create --base main --head phase2-perf-baseline \
  --title "docs(workshop): perf baseline pre-fix" \
  --body "Records p95 baseline on AWS so during workshop demo we have a definite before/after."
# After merge:
gh pr merge --squash --delete-branch
```

- [ ] **Step 4: Final sanity sweep**

Verify the full acceptance criteria from the spec one more time:
```bash
# Health
curl -fsS "http://$SERVER_IP/health/ready"

# Login
TOKEN=$(curl -s -X POST "http://$SERVER_IP/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"dispatcher@example.com","password":"dispatcher123"}' | jq -r .access_token)
[ -n "$TOKEN" ] && echo "✓ login works"

# Each business endpoint
curl -fsS "http://$SERVER_IP/drivers?status=ACTIVE" -H "Authorization: Bearer $TOKEN" > /dev/null && echo "✓ /drivers"
curl -fsS "http://$SERVER_IP/drivers/1/dashboard" -H "Authorization: Bearer $TOKEN" > /dev/null && echo "✓ /drivers/{id}/dashboard"
curl -fsS "http://$SERVER_IP/trips/1" -H "Authorization: Bearer $TOKEN" > /dev/null && echo "✓ /trips/{id}"
curl -fsS -X POST "http://$SERVER_IP/trips/search" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"limit":5}' > /dev/null && echo "✓ /trips/search"
curl -fsS "http://$SERVER_IP/loads/upcoming" -H "Authorization: Bearer $TOKEN" > /dev/null && echo "✓ /loads/upcoming"
curl -fsS "http://$SERVER_IP/reports/fleet-utilization?month=2024-06" -H "Authorization: Bearer $TOKEN" > /dev/null && echo "✓ /reports/fleet-utilization"
```

All 6 business endpoints + 2 health + 1 auth = 9 endpoints, all functional. Phase 2 is **ready for workshop**.

---

## Acceptance criteria verification

Cross-check against the spec (`docs/superpowers/specs/2026-05-17-phase2-workshop-content-design.md` Section 9):

### Code & schema
- [ ] 14 SQLAlchemy models in `app/src/models/` (Task 2-6)
- [ ] User model + JWT auth + login endpoint (Task 2, 12-14)
- [ ] 9 endpoints — all returning correct shapes (Task 11, 14, 16-21)
- [ ] 3 baseline migrations (Task 7-9)
- [ ] **Verified** missing composite index for Bug A (Task 9 Step 4)
- [ ] Bug A and B in place (Task 17, 19)
- [ ] Demo users (`dispatcher@example.com` / `dispatcher123`) work via login (Task 8, 14)

### CSV seed
- [ ] `app/src/scripts/seed_csv.py` as CLI command (Task 10)
- [ ] `just seed-csv` works locally, ~570K rows in ~2 min (Task 10 Step 4)
- [ ] Idempotent + reset (Task 10 Step 5-6)

### Local dev
- [ ] `git clone && cp .env.example .env && just up && just seed-csv` → end-to-end (Task 10)
- [ ] `curl localhost:8000/health/ready` → `{"status":"ok","db":"ok"}` (preserved by Task 11)
- [ ] `POST /auth/login` returns JWT (Task 14 Step 3)
- [ ] `just test` — all tests green with intentional gaps (Task 24)

### CI
- [ ] PR feature branch — `ci` job green (Task 24 Step 4)
- [ ] Merge to main — `deploy.yml` all 4 jobs green (Task 24 Step 6)
- [ ] Smoke test on AWS — `db:ok` (Task 25 Step 2)

### AWS prod
- [ ] After first merge → SSH + seed → entries loaded (Task 25 Step 4)
- [ ] `POST /auth/login` returns JWT (Task 25 Step 3)
- [ ] `GET /drivers/1/dashboard` → ~600-1500ms (Task 27 — Bug B working)
- [ ] `just perf-trip-search-aws` → `p95 ≥ 1s on 22 parallel` (Task 26 — Bug A working)

### Documentation
- [ ] `README.md` updated with logistics-domain one-liner (Task 23)
- [ ] `.env.example` contains `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` (Task 1)
- [ ] `perf/README.md` — how to run, what numbers mean (Task 22)

### Workshop bonus state
- [ ] Bug C (stale fleet-utilization) works — current month returns stale data (Task 28)
- [ ] Tests for `drivers/`, `loads/`, `trips/search` **intentionally absent** (verified by absence — no test files in those dirs except `trips/test_trip_detail.py`)

---

## Self-review notes

The plan was checked for:

1. **Spec coverage**: every spec requirement maps to a task (see acceptance checklist above).
2. **Placeholders**: no `TBD`/`TODO`/`fill in later` — all code is concrete. The only `TODO`-shaped string is the spec's _negation_ rule about not putting `# TODO: bug for demo` comments in code, repeated in plan's preamble.
3. **Type consistency**:
   - `LoginRequest`, `TokenResponse`, `CurrentUserResponse` schemas (Task 13) used in router (Task 14)
   - `DriverListItem` defined in Task 16, reused in `DriverDashboardResponse` (Task 17)
   - `TripSearchRequest`/`TripSearchResponse`/`TripSearchItem` defined in Task 19, used in router same task
   - `FleetUtilizationResponse`/`TruckUtilizationItem` defined in Task 21, used in router same task
   - All FK column names match across model definitions
   - `get_current_user` signature consistent across all router files
4. **No `# TODO` comments leak into code** — verified by inspection of each model/service/router task's code blocks.
5. **Migration order**: `0001 (schema) → 0002 (seed users) → 0003 (extra indexes)` with explicit `down_revision` chain.

6. **Small spec-aligned addition — `GET /auth/me`**: spec section 4 lists 9 endpoints; this plan adds `GET /auth/me` in Task 14 as a token-introspection helper (industry-standard, makes JWT roundtrip tests in Task 15 cleaner). Total endpoint count in implementation = 10. If you want strict spec parity, remove the `/auth/me` route from Task 14's router code, and rewrite Task 15's `test_me_*` tests to hit another protected endpoint (e.g. `/drivers`) instead.

---

## End of plan
