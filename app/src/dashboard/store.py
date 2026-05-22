import glob
import json
import os
import tempfile

from src.config import settings

_counts: dict[str, dict[str, int]] = {}


def increment(route: str, status: int) -> None:
    bucket = _counts.setdefault(route, {})
    key = str(status)
    bucket[key] = bucket.get(key, 0) + 1
    _persist()


def _persist() -> None:
    os.makedirs(settings.STATS_DIR, exist_ok=True)
    target = os.path.join(settings.STATS_DIR, f"stats.{os.getpid()}.json")
    fd, tmp_path = tempfile.mkstemp(dir=settings.STATS_DIR, prefix=".stats.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(_counts, f)
        os.replace(tmp_path, target)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def read_merged() -> dict[str, dict[str, int]]:
    merged: dict[str, dict[str, int]] = {}
    pattern = os.path.join(settings.STATS_DIR, "stats.*.json")
    for path in glob.glob(pattern):
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        for route, statuses in data.items():
            bucket = merged.setdefault(route, {})
            for status, count in statuses.items():
                bucket[status] = bucket.get(status, 0) + count
    return merged
