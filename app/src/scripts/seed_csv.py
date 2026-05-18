"""CSV seed CLI — loads app/data/*.csv into Postgres via COPY.

Usage:
    python -m src.scripts.seed_csv          # idempotent
    python -m src.scripts.seed_csv --reset  # TRUNCATE then seed
"""

from __future__ import annotations

import asyncio
import csv
import io
import re
from pathlib import Path

import asyncpg
import typer

from src.config import settings

app = typer.Typer(add_completion=False)

# Load order — FK parents before children
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

DATA_DIR = Path(__file__).resolve().parents[2] / "data"  # /app/data inside container

# Columns whose values are business-key strings (e.g. "DRV00001") that must be
# converted to their integer suffix before inserting into the DB.
_ID_COLUMNS: dict[str, set[str]] = {
    "drivers": {"driver_id"},
    "trucks": {"truck_id"},
    "trailers": {"trailer_id"},
    "customers": {"customer_id"},
    "facilities": {"facility_id"},
    "routes": {"route_id"},
    "loads": {"load_id", "customer_id", "route_id"},
    "trips": {"trip_id", "load_id", "driver_id", "truck_id", "trailer_id"},
    "fuel_purchases": {"fuel_purchase_id", "trip_id", "truck_id", "driver_id"},
    "maintenance_records": {"maintenance_id", "truck_id"},
    "delivery_events": {"event_id", "load_id", "trip_id", "facility_id"},
    "safety_incidents": {"incident_id", "trip_id", "truck_id", "driver_id"},
    "driver_monthly_metrics": {"driver_id"},
    "truck_utilization_metrics": {"truck_id"},
}

_PREFIX_RE = re.compile(r"^[A-Za-z]+0*(\d+)$")


def _to_int_or_none(value: str) -> int | None:
    """Strip alphabetic prefix and leading zeros; return None for empty string."""
    if not value:
        return None
    m = _PREFIX_RE.match(value)
    if m:
        return int(m.group(1))
    raise ValueError(f"unexpected ID format: {value!r}")


def _transform_row(row: dict[str, str], id_cols: set[str]) -> list[str]:
    """Return CSV row values with ID columns converted to plain integers."""
    result = []
    for col, val in row.items():
        if col in id_cols:
            converted = _to_int_or_none(val)
            result.append("" if converted is None else str(converted))
        else:
            result.append(val)
    return result


def _connect_kwargs() -> dict[str, object]:
    """Parse the SQLAlchemy DATABASE_URL into asyncpg kwargs.

    Avoids DSN string parsing — base64-generated passwords routinely contain
    `/` or `+` which break asyncpg's URL parser (it mistakes parts of the
    password for host/port). Pass components separately instead.
    """
    from sqlalchemy.engine.url import make_url

    url = make_url(settings.DATABASE_URL)
    return {
        "host": url.host,
        "port": url.port,
        "user": url.username,
        "password": url.password,
        "database": url.database,
    }


async def _table_has_data(conn: asyncpg.Connection, table: str) -> bool:
    return (await conn.fetchrow(f"SELECT 1 FROM {table} LIMIT 1")) is not None


async def _truncate_all(conn: asyncpg.Connection) -> None:
    # Reverse order so FKs allow truncate; CASCADE handles edge cases
    for table in reversed(LOAD_ORDER):
        await conn.execute(f"TRUNCATE {table} RESTART IDENTITY CASCADE")


async def _copy_csv(conn: asyncpg.Connection, table: str) -> int:
    csv_path = DATA_DIR / f"{table}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"missing CSV: {csv_path}")

    id_cols = _ID_COLUMNS.get(table, set())
    buf = io.StringIO()
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        writer = csv.writer(buf)
        writer.writerow(reader.fieldnames)
        for row in reader:
            writer.writerow(_transform_row(row, id_cols))

    buf.seek(0)
    binary_buf = io.BytesIO(buf.read().encode())
    result = await conn.copy_to_table(
        table_name=table,
        source=binary_buf,
        format="csv",
        header=True,
    )
    return int(result.split()[-1])


async def _seed(reset: bool) -> None:
    conn = await asyncpg.connect(**_connect_kwargs())
    try:
        if not reset and await _table_has_data(conn, "trips"):
            typer.echo("data already seeded — exiting (use --reset to force)")
            return
        if reset:
            typer.echo("--reset: TRUNCATE 14 domain tables")
            await _truncate_all(conn)
        for table in LOAD_ORDER:
            count = await _copy_csv(conn, table)
            typer.echo(f"  {table:30} {count:>10,} rows")
        typer.echo("seed complete")
    finally:
        await conn.close()


@app.command()
def main(
    reset: bool = typer.Option(False, "--reset", help="TRUNCATE domain tables before seeding"),
) -> None:
    """Load app/data/*.csv into Postgres via COPY."""
    asyncio.run(_seed(reset))


if __name__ == "__main__":
    app()
