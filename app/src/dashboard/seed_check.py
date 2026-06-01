import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.domain_tables import DOMAIN_TABLES


def _read_manifest() -> dict[str, int] | None:
    path = Path(settings.SEED_MANIFEST_PATH)
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


async def seed_check(session: AsyncSession) -> dict:
    expected = _read_manifest()

    tables = []
    total_rows = 0
    for name, model in DOMAIN_TABLES.items():
        rows = (await session.execute(select(func.count()).select_from(model))).scalar_one()
        total_rows += rows

        if expected is None:
            tables.append({"table": name, "rows": rows, "expected": None, "status": "unknown"})
            continue

        exp = expected[name]
        tables.append(
            {
                "table": name,
                "rows": rows,
                "expected": exp,
                "status": "ok" if rows == exp else "mismatch",
            }
        )

    if expected is None:
        return {
            "tables": tables,
            "overall_status": "unknown",
            "total_rows": total_rows,
            "total_expected": None,
        }

    overall = "ok" if all(t["status"] == "ok" for t in tables) else "mismatch"
    return {
        "tables": tables,
        "overall_status": overall,
        "total_rows": total_rows,
        "total_expected": sum(expected.values()),
    }
