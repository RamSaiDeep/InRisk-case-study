"""Live tests: these hit bharatlas and Google Earth Engine.

Excluded from the default run (`addopts = -m 'not live'`). Run them with:

    uv run pytest -m live
"""

from __future__ import annotations

import pandas as pd
import pytest

from conftest import REFERENCE_CSV
from data_layer import fetch, location
from data_layer.config import PincodeNotFound

pytestmark = pytest.mark.live

# The known-good resolution for the submitted case study.
REFERENCE_PINCODE = "380006"
KNOWN_PIXEL_LAT = 22.999693294401865
KNOWN_PIXEL_LON = 72.601155692309760


def test_bharatlas_schema_still_has_the_pincode_column():
    attributes = location.verify_pincode(REFERENCE_PINCODE)
    assert attributes["Pincode"] == REFERENCE_PINCODE
    assert attributes["Office_Name"] == "Ellisbridge SO"
    assert attributes["Circle"] == "Gujarat"


def test_unknown_pincode_is_reported_as_not_found():
    with pytest.raises(PincodeNotFound):
        location.verify_pincode("999999")


def test_centroid_matches_the_submitted_report():
    lon, lat = location.get_pincode_centroid(REFERENCE_PINCODE)
    assert lat == pytest.approx(23.02, abs=0.005)
    assert lon == pytest.approx(72.56, abs=0.005)


def test_pixel_snap_is_exact():
    """The acceptance check: the resolved pixel must be bit-identical to the
    coordinate the submitted report was built on."""
    lon, lat = location.snap_to_era5_pixel(72.561219775, 23.022273650)
    assert lat == pytest.approx(KNOWN_PIXEL_LAT, abs=1e-12)
    assert lon == pytest.approx(KNOWN_PIXEL_LON, abs=1e-12)


def test_resolve_location_end_to_end():
    resolved = location.resolve_location(REFERENCE_PINCODE, use_cache=False)
    assert resolved["pixel"][1] == pytest.approx(KNOWN_PIXEL_LAT, abs=1e-12)
    assert resolved["pixel"][0] == pytest.approx(KNOWN_PIXEL_LON, abs=1e-12)
    assert resolved["cached"] is False


def test_a_fetched_year_matches_the_report_fixture():
    """Strongest available check on the pull: a freshly downloaded year must
    equal the CSV the submitted workbook was built from."""
    fresh = fetch.download_ssrd_year(KNOWN_PIXEL_LAT, KNOWN_PIXEL_LON, 2005)
    fresh["date"] = pd.to_datetime(fresh["date"])
    fixture = pd.read_csv(REFERENCE_CSV, parse_dates=["date"])
    expected = fixture[fixture["date"].dt.year == 2005]
    merged = fresh.merge(expected, on="date", suffixes=("_fresh", "_report"))
    assert len(merged) == 365
    assert (merged["ssrd_kwh_m2_fresh"] - merged["ssrd_kwh_m2_report"]).abs().max() < 1e-12
    assert merged["ssrd_kwh_m2_fresh"].sum() == pytest.approx(1985.888878, abs=1e-6)
