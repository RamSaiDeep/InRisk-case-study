"""Cache store: pure file I/O, tested against a temporary directory."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from data_layer import cache


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Point every cache path at a temporary directory."""
    series = tmp_path / "series"
    series.mkdir()
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(cache, "METADATA_FILE", tmp_path / "metadata.json")
    monkeypatch.setattr(cache, "SERIES_DIR", series)
    return tmp_path


def make_frame(years: range) -> pd.DataFrame:
    dates = pd.date_range(f"{years.start}-01-01", f"{years.stop - 1}-12-31", freq="D")
    return pd.DataFrame(
        {
            "date": dates,
            "latitude": 22.9997,
            "longitude": 72.6012,
            "ssrd_j_m2": 19_000_000.0,
            "ssrd_kwh_m2": 19_000_000.0 / 3_600_000,
        }
    )


def test_empty_cache_reads_as_empty(cache_dir):
    assert cache.load_metadata() == {"pincodes": {}}
    assert cache.get_cache_entry("380006") is None
    assert cache.read_cached_df("380006") is None
    assert cache.covers_range("380006", 2005, 2024) is False


def test_corrupt_metadata_reads_as_empty_rather_than_raising(cache_dir):
    cache.METADATA_FILE.write_text("{not json", encoding="utf-8")
    assert cache.load_metadata() == {"pincodes": {}}


def test_write_then_read_round_trip(cache_dir):
    frame = make_frame(range(2005, 2025))
    cache.write_cache(
        "380006",
        frame,
        location={"pixel_lat": 22.9997, "pixel_lon": 72.6012},
        start_year=2005,
        end_year=2024,
    )
    back = cache.read_cached_df("380006")
    assert len(back) == len(frame)
    entry = cache.get_cache_entry("380006")
    assert entry["start_year"] == 2005
    assert entry["end_year"] == 2024
    assert entry["rows"] == len(frame)
    assert entry["fetched_at"].endswith("+00:00")


def test_covers_range_answers_without_opening_the_data_file(cache_dir):
    cache.write_cache(
        "380006", make_frame(range(2005, 2025)), location={}, start_year=2005, end_year=2024
    )
    cache.series_path("380006").unlink()  # metadata alone must answer
    assert cache.covers_range("380006", 2005, 2024) is True
    assert cache.covers_range("380006", 2010, 2020) is True
    assert cache.covers_range("380006", 2000, 2024) is False
    assert cache.covers_range("380006", 2005, 2025) is False


def test_resolved_location_persists_without_any_data_fetch(cache_dir):
    cache.save_resolved_location(
        "380006",
        centroid=(72.561220, 23.022274),
        pixel=(72.601156, 22.999693),
        attributes={"Office_Name": "Ellisbridge SO"},
    )
    entry = cache.get_cache_entry("380006")
    assert entry["pixel_lat"] == 22.999693
    assert entry["attributes"]["Office_Name"] == "Ellisbridge SO"
    # No data file, and no year range claimed.
    assert cache.read_cached_df("380006") is None
    assert cache.covers_range("380006", 2005, 2024) is False


def test_a_later_fetch_keeps_the_resolved_location(cache_dir):
    cache.save_resolved_location("380006", (72.56, 23.02), (72.60, 23.00))
    cache.write_cache(
        "380006", make_frame(range(2005, 2025)), location={}, start_year=2005, end_year=2024
    )
    entry = cache.get_cache_entry("380006")
    assert entry["pixel_lat"] == 23.00
    assert entry["rows"] == 7305


def test_metadata_write_is_atomic(cache_dir):
    cache.save_metadata({"pincodes": {"380006": {"rows": 1}}})
    assert json.loads(cache.METADATA_FILE.read_text(encoding="utf-8"))["pincodes"]
    assert not list(cache_dir.glob("*.tmp"))


def test_daily_series_converts_to_the_engine_contract(cache_dir):
    frame = make_frame(range(2005, 2007))
    series = cache.daily_series(frame)
    assert len(series) == 730
    assert series[0].ssrd == pytest.approx(19_000_000 / 3_600_000)
    assert series[0].day.year == 2005


def test_daily_series_filters_to_the_requested_years(cache_dir):
    series = cache.daily_series(make_frame(range(2005, 2025)), 2019, 2020)
    assert {reading.day.year for reading in series} == {2019, 2020}
    assert len(series) == 366 + 365
