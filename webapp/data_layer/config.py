"""Constants and paths for the data layer. The only module that names
external services."""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from datetime import date  # noqa: TC003
from pathlib import Path

# --- Google Earth Engine -------------------------------------------------
GEE_PROJECT = "development-hruday"
ERA5_COLLECTION = "ECMWF/ERA5_LAND/DAILY_AGGR"
SSRD_BAND = "surface_solar_radiation_downwards_sum"
# ERA5-Land native resolution, ~0.1 degrees. Used both to snap a coordinate
# to a grid cell and to sample at that cell.
ERA5_SCALE_M = 11132
# ERA5-Land's native grid step, used to draw the cell around the pixel.
ERA5_CELL_DEG = 0.1
# ERA5-Land publishes SSRD as J/m2; the engine's unit contract is kWh/m2.
# This division is the data layer's responsibility, nowhere else.
J_PER_M2_TO_KWH_PER_M2 = 1 / 3_600_000

# --- bharatlas -----------------------------------------------------------
BHARATLAS_BASE = "https://bharatlas.com/api/v1"
PINCODE_LAYER = "datagov_pincodes"
PINCODE_COLUMN = "Pincode"  # verified against the layer's live schema
# The layer's geometry lives only in the bulk files: its parquet has a
# single row group and no page index, so one polygon cannot be range-read.
# The columns we need are pulled once and reduced to a centroid index.
# Boundaries are stored simplified, for drawing only: ~0.001 degrees is
# about 110 m, far inside a 9 km ERA5-Land cell.
OUTLINE_TOLERANCE_DEG = 0.001
PINCODE_PARQUET_URL = (
    "https://pub-0429b8e3b5a946e69ea007df844a6f1c.r2.dev"
    "/postal/boundaries/Datagov_Pincode_Boundaries.parquet"
)

# --- cache ---------------------------------------------------------------
# Where the cache lives is a deployment decision, not a code one.
#
#   CACHE_DIR=/tmp/cache   on a host whose /tmp is a tmpfs (Cloud Run, Fly),
#                          this keeps every byte in memory and discards it
#                          when the instance stops - nothing is ever written
#                          to a disk that outlives the process.
#   EPHEMERAL_CACHE=1      same effect anywhere: a fresh temp directory per
#                          process, removed when the process exits.
#
# Unset, it falls back to a folder beside the code, which is what a local
# development run wants.
_ENV_DIR = os.environ.get("CACHE_DIR")
if _ENV_DIR:
    CACHE_DIR = Path(_ENV_DIR)
elif os.environ.get("EPHEMERAL_CACHE") == "1":
    CACHE_DIR = Path(tempfile.mkdtemp(prefix="pricing-cache-"))
    atexit.register(shutil.rmtree, CACHE_DIR, True)
else:
    CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"

METADATA_FILE = CACHE_DIR / "metadata.json"
CENTROID_INDEX = CACHE_DIR / "pincode_centroids.parquet"
SERIES_DIR = CACHE_DIR / "series"

#: True when nothing survives this process. The UI says so, rather than
#: promising a speed that will not be there on the next visit.
CACHE_IS_EPHEMERAL = bool(
    os.environ.get("EPHEMERAL_CACHE") == "1"
    or (_ENV_DIR and str(CACHE_DIR).startswith(("/tmp", "/var/tmp")))
)

HTTP_TIMEOUT = 300.0


class DataLayerError(Exception):
    """Base for everything this layer raises."""


class PincodeNotFound(DataLayerError):
    """No such pincode in the bharatlas layer. API maps this to 404."""


class UpstreamError(DataLayerError):
    """bharatlas or GEE answered, but not in the shape we expect, or not at
    all. API maps this to 502."""


class Misconfigured(DataLayerError):
    """The server itself is not set up: no Earth Engine credentials, no
    writable cache directory. API maps this to 500."""


class NotCached(DataLayerError):
    """Asked to price a pincode whose data was never fetched. API maps this
    to 409."""


def latest_complete_year(today: "date | None" = None) -> int:
    """The most recent calendar year whose final ERA5-Land data is published.

    ERA5-Land's quality-controlled release lags the month it covers by two to
    three months, so a year only becomes usable in the spring that follows
    it. Requesting beyond this would normalize a part-year as if it were
    complete - which `normalize_year` would silently scale up.
    """
    from datetime import date as _date

    today = today or _date.today()
    return today.year - 1 if today.month >= 4 else today.year - 2
