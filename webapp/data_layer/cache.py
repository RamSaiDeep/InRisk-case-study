"""Cache store: a parquet file per pincode plus one small JSON index.

Pure file I/O - no network, no Earth Engine. Everything here is safe to
unit-test with a temporary directory.
"""

from __future__ import annotations

import json
from functools import lru_cache
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from pricing_engine import DailyReading

from .config import CACHE_DIR, CENTROID_INDEX, METADATA_FILE, SERIES_DIR


def _ensure_dirs() -> None:
    SERIES_DIR.mkdir(parents=True, exist_ok=True)


def series_path(pincode: str) -> Path:
    return SERIES_DIR / f"{pincode}_ssrd.parquet"


def load_metadata() -> dict[str, Any]:
    """The small index tracking which pincodes are cached and what range
    each covers. A missing or corrupt file reads as empty rather than
    raising - a cache is a convenience, never the source of truth."""
    if not METADATA_FILE.exists():
        return {"pincodes": {}}
    try:
        data = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"pincodes": {}}
    data.setdefault("pincodes", {})
    return data


def save_metadata(metadata: dict[str, Any]) -> None:
    _ensure_dirs()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # Write-then-rename so a crash mid-write cannot leave a half file.
    temp = METADATA_FILE.with_suffix(".json.tmp")
    temp.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    temp.replace(METADATA_FILE)


def get_cache_entry(pincode: str) -> dict[str, Any] | None:
    return load_metadata()["pincodes"].get(pincode)


def covers_range(pincode: str, start_year: int, end_year: int) -> bool:
    """Answers "do I need to fetch anything?" without opening the data file."""
    entry = get_cache_entry(pincode)
    if not entry or "start_year" not in entry:
        return False
    return entry["start_year"] <= start_year and entry["end_year"] >= end_year


def read_cached_df(pincode: str) -> pd.DataFrame | None:
    path = series_path(pincode)
    if not path.exists():
        return None
    return pd.read_parquet(path)


def daily_series(
    frame: pd.DataFrame, start_year: int | None = None, end_year: int | None = None
) -> list[DailyReading]:
    """DataFrame -> the engine's unit contract (kWh/m2 per day).

    This is the one place the two layers meet, so the year filter lives here
    rather than in the engine, which has no concept of a requested range.
    """
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    if start_year is not None:
        frame = frame[frame["date"].dt.year >= start_year]
    if end_year is not None:
        frame = frame[frame["date"].dt.year <= end_year]
    return [
        DailyReading(day=row.date.date(), ssrd=float(row.ssrd_kwh_m2))
        for row in frame.sort_values("date").itertuples()
    ]


@lru_cache(maxsize=8)
def _daily_series_memo(
    pincode: str, start_year: int | None, end_year: int | None, _stamp: int
) -> tuple[DailyReading, ...]:
    frame = read_cached_df(pincode)
    if frame is None:
        return ()
    return tuple(daily_series(frame, start_year, end_year))


def cached_daily_series(
    pincode: str, start_year: int | None = None, end_year: int | None = None
) -> list[DailyReading]:
    """The engine-ready series for a cached pincode, held in memory.

    Every slider change re-prices the same 7,305 readings, so re-reading and
    re-boxing them per request is pure overhead. Keyed on the data file's
    modification time, so a re-fetch invalidates the memo by itself.
    """
    path = series_path(pincode)
    stamp = path.stat().st_mtime_ns if path.exists() else 0
    return list(_daily_series_memo(pincode, start_year, end_year, stamp))


def write_cache(
    pincode: str,
    frame: pd.DataFrame,
    location: dict[str, Any],
    start_year: int,
    end_year: int,
) -> None:
    """Persists a successful fetch: the data file plus its metadata entry."""
    _ensure_dirs()
    frame.to_parquet(series_path(pincode), index=False, compression="zstd")
    metadata = load_metadata()
    entry = metadata["pincodes"].setdefault(pincode, {})
    entry.update(
        {
            "start_year": start_year,
            "end_year": end_year,
            "rows": int(len(frame)),
            "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
            **location,
        }
    )
    save_metadata(metadata)


def save_resolved_location(
    pincode: str,
    centroid: tuple[float, float],
    pixel: tuple[float, float],
    attributes: dict[str, Any] | None = None,
) -> None:
    """Persists just the location resolution, independent of whether any
    data has been fetched yet."""
    metadata = load_metadata()
    entry = metadata["pincodes"].setdefault(pincode, {})
    entry.update(
        {
            "centroid_lon": centroid[0],
            "centroid_lat": centroid[1],
            "pixel_lon": pixel[0],
            "pixel_lat": pixel[1],
            "resolved_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    )
    if attributes:
        entry["attributes"] = attributes
    save_metadata(metadata)


def centroid_index_exists() -> bool:
    return CENTROID_INDEX.exists()
