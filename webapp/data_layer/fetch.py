"""Data pull - the slow path.

Follows the pull pattern proven in Code/notebooks/01_data_download.ipynb:
one year at a time, one ERA5-Land daily-aggregate collection, sampled at the
confirmed pixel with a first() reducer.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from . import cache, location
from .config import (
    ERA5_COLLECTION,
    ERA5_SCALE_M,
    J_PER_M2_TO_KWH_PER_M2,
    SSRD_BAND,
    UpstreamError,
)

ProgressCallback = Callable[[int, int, str], None]


def download_ssrd_year(lat: float, lon: float, year: int) -> pd.DataFrame:
    """One year of daily SSRD at one pixel.

    Isolated so progress can be reported year by year and a failed year does
    not force re-pulling the whole range. A single year is ~365 features,
    safely below Earth Engine's 5,000-element response limit.
    """
    ee = location._init_ee()
    point = ee.Geometry.Point([lon, lat])
    collection = (
        ee.ImageCollection(ERA5_COLLECTION)
        .filterDate(f"{year}-01-01", f"{year + 1}-01-01")
        .select(SSRD_BAND)
    )

    def extract(image: Any) -> Any:
        value = image.reduceRegion(
            reducer=ee.Reducer.first(), geometry=point, scale=ERA5_SCALE_M
        ).get(SSRD_BAND)
        return ee.Feature(
            None, {"date": image.date().format("YYYY-MM-dd"), "value": value}
        )

    try:
        info = collection.map(extract).getInfo()
    except Exception as exc:  # noqa: BLE001 - any GEE failure is upstream
        raise UpstreamError(f"Earth Engine pull failed for {year}: {exc}") from exc
    rows = [feature["properties"] for feature in info["features"]]
    if not rows:
        raise UpstreamError(f"Earth Engine returned no data for {year}")
    frame = pd.DataFrame(rows)
    frame["latitude"] = lat
    frame["longitude"] = lon
    frame = frame.rename(columns={"value": "ssrd_j_m2"})
    frame["ssrd_kwh_m2"] = frame["ssrd_j_m2"] * J_PER_M2_TO_KWH_PER_M2
    return frame[["date", "latitude", "longitude", "ssrd_j_m2", "ssrd_kwh_m2"]]


def download_ssrd(
    lat: float,
    lon: float,
    start_year: int,
    end_year: int,
    progress: ProgressCallback | None = None,
) -> pd.DataFrame:
    """Loops the per-year pull across the range, reporting progress as it goes."""
    total = end_year - start_year + 1
    frames = []
    for offset, year in enumerate(range(start_year, end_year + 1), start=1):
        frames.append(download_ssrd_year(lat, lon, year))
        if progress:
            progress(offset, total, f"Fetched {offset}/{total} years ({year})")
    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])
    return combined.sort_values("date").reset_index(drop=True)


def get_or_fetch_ssrd(
    pincode: str,
    start_year: int,
    end_year: int,
    progress: ProgressCallback | None = None,
) -> pd.DataFrame:
    """The one entry point everything else should call.

    Checks cache coverage first; only touches bharatlas or Earth Engine if
    the requested range is not already cached.
    """
    if cache.covers_range(pincode, start_year, end_year):
        cached = cache.read_cached_df(pincode)
        if cached is not None:
            if progress:
                progress(1, 1, "Served from cache")
            return cached
    resolved = location.resolve_location(pincode)
    pixel_lon, pixel_lat = resolved["pixel"]
    frame = download_ssrd(pixel_lat, pixel_lon, start_year, end_year, progress)
    cache.write_cache(
        pincode,
        frame,
        location={
            "centroid_lon": resolved["centroid"][0],
            "centroid_lat": resolved["centroid"][1],
            "pixel_lon": pixel_lon,
            "pixel_lat": pixel_lat,
            "attributes": resolved["attributes"],
        },
        start_year=start_year,
        end_year=end_year,
    )
    return frame
