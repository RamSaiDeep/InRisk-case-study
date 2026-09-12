"""Data layer: the only layer that touches the network."""

from .cache import (
    covers_range,
    daily_series,
    get_cache_entry,
    load_metadata,
    read_cached_df,
    save_metadata,
    save_resolved_location,
    write_cache,
)
from .config import DataLayerError, NotCached, PincodeNotFound, UpstreamError
from .fetch import download_ssrd, download_ssrd_year, get_or_fetch_ssrd
from .jobs import get_status, start_fetch_job
from .location import (
    get_pincode_centroid,
    resolve_location,
    snap_to_era5_pixel,
    verify_pincode,
)

__all__ = [
    "DataLayerError",
    "NotCached",
    "PincodeNotFound",
    "UpstreamError",
    "covers_range",
    "daily_series",
    "download_ssrd",
    "download_ssrd_year",
    "get_cache_entry",
    "get_or_fetch_ssrd",
    "get_pincode_centroid",
    "get_status",
    "load_metadata",
    "read_cached_df",
    "resolve_location",
    "save_metadata",
    "save_resolved_location",
    "snap_to_era5_pixel",
    "start_fetch_job",
    "verify_pincode",
    "write_cache",
]
