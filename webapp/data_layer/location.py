"""Location resolution - the fast path.

Two network hops and no 20-year pull: confirm the pincode exists, find its
polygon centroid, snap that to the ERA5-Land grid.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any

import httpx
import pyarrow.parquet as pq
import shapely

from . import cache
from .config import (
    BHARATLAS_BASE,
    CENTROID_INDEX,
    ERA5_COLLECTION,
    ERA5_SCALE_M,
    GEE_PROJECT,
    HTTP_TIMEOUT,
    PINCODE_COLUMN,
    PINCODE_LAYER,
    OUTLINE_TOLERANCE_DEG,
    PINCODE_PARQUET_URL,
    Misconfigured,
    PincodeNotFound,
    UpstreamError,
)

_ee_ready = False


def _service_account_key() -> str | None:
    """A deployed instance authenticates as a service account, not as a person.

    EE_SERVICE_ACCOUNT_JSON holds the key itself (for hosts that inject
    secrets as environment variables) or a path to it. A personal OAuth
    credential must never be shipped in an image.
    """
    return os.environ.get("EE_SERVICE_ACCOUNT_JSON") or None


def _credentials_present() -> bool:
    """Distinguishes "this server was never set up" from "Google is down"."""
    from pathlib import Path as _Path

    if _service_account_key():
        return True
    return (_Path.home() / ".config" / "earthengine" / "credentials").exists()


def _init_ee() -> Any:
    """Initialize Earth Engine once per process."""
    global _ee_ready
    import ee

    if not _ee_ready:
        if not _credentials_present():
            raise Misconfigured(
                "no Earth Engine credentials - run `earthengine authenticate` "
                "locally, or set EE_SERVICE_ACCOUNT_JSON when deployed"
            )
        key = _service_account_key()
        try:
            if key:
                blob = (
                    Path(key).read_text(encoding="utf-8")
                    if key.strip().startswith("{") is False and Path(key).exists()
                    else key
                )
                info = json.loads(blob)
                credentials = ee.ServiceAccountCredentials(
                    info["client_email"], key_data=blob
                )
                ee.Initialize(credentials, project=os.environ.get("GEE_PROJECT", GEE_PROJECT))
            else:
                ee.Initialize(project=os.environ.get("GEE_PROJECT", GEE_PROJECT))
        except Exception as exc:  # noqa: BLE001 - any failure here is upstream
            raise UpstreamError(f"could not initialize Earth Engine: {exc}") from exc
        _ee_ready = True
    return ee


class _HttpRangeFile(io.RawIOBase):
    """A seekable file over HTTP range requests.

    Lets pyarrow read a remote parquet's footer and individual column chunks
    without pulling bytes it does not need.
    """

    def __init__(self, url: str, client: httpx.Client) -> None:
        self._url = url
        self._client = client
        self._pos = 0
        head = client.head(url, follow_redirects=True)
        if head.status_code != 200 or "content-length" not in head.headers:
            raise UpstreamError(f"cannot range-read {url}: HTTP {head.status_code}")
        self._size = int(head.headers["content-length"])

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            self._pos = offset
        elif whence == io.SEEK_CUR:
            self._pos += offset
        else:
            self._pos = self._size + offset
        return self._pos

    def tell(self) -> int:
        return self._pos

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = self._size - self._pos
        if size == 0:
            return b""
        end = min(self._pos + size, self._size) - 1
        response = self._client.get(
            self._url,
            headers={"Range": f"bytes={self._pos}-{end}"},
            follow_redirects=True,
        )
        if response.status_code not in (200, 206):
            raise UpstreamError(f"range read failed: HTTP {response.status_code}")
        self._pos += len(response.content)
        return response.content


def verify_pincode(pincode: str) -> dict[str, str]:
    """Confirm the pincode exists and return its post-office attributes.

    Cheap (~0.5s) and the only call that can tell a typo from a real
    pincode, so it runs before anything expensive.
    """
    url = f"{BHARATLAS_BASE}/layers/{PINCODE_LAYER}/query"
    try:
        response = httpx.get(
            url, params={PINCODE_COLUMN: pincode}, timeout=30, follow_redirects=True
        )
    except httpx.HTTPError as exc:
        raise UpstreamError(f"bharatlas unreachable: {exc}") from exc
    # Unknown paths on this host answer 200 with the site's HTML, so the
    # content type is checked rather than the status code alone.
    if "json" not in response.headers.get("content-type", ""):
        raise UpstreamError("bharatlas did not return JSON - API shape changed")
    try:
        rows = response.json()["data"]["rows"]
    except (KeyError, ValueError) as exc:
        raise UpstreamError(f"unexpected bharatlas response: {exc}") from exc
    if not rows:
        raise PincodeNotFound(f"pincode {pincode} is not in the bharatlas layer")
    return {str(k): str(v).strip() for k, v in rows[0].items()}


def build_centroid_index(client: httpx.Client | None = None) -> None:
    """One-time bootstrap: every Indian pincode's centroid, computed locally.

    The published parquet stores all 19,312 polygons in a single row group
    with no page index, so there is no way to read one polygon's geometry on
    its own. Rather than pay that cost per lookup, the two columns we need
    are pulled once (~19.7 MB) and reduced to a ~300 KB centroid index that
    every later resolution reads locally.
    """
    import pyarrow as pa

    owned = client is None
    client = client or httpx.Client(timeout=HTTP_TIMEOUT)
    try:
        table = pq.ParquetFile(
            _HttpRangeFile(PINCODE_PARQUET_URL, client)
        ).read_row_group(0, columns=[PINCODE_COLUMN, "geometry"])
    finally:
        if owned:
            client.close()
    geometries = shapely.from_wkb(
        table.column("geometry").to_numpy(zero_copy_only=False)
    )
    centroids = shapely.centroid(geometries)
    # Centroids come from the full-resolution polygon; the stored outline is
    # simplified to about 110 m, which is for drawing only and never feeds a
    # coordinate the pricing depends on.
    outlines = shapely.to_wkb(
        shapely.simplify(geometries, OUTLINE_TOLERANCE_DEG, preserve_topology=True)
    )
    CENTROID_INDEX.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.table(
            {
                "pincode": table.column(PINCODE_COLUMN),
                "lon": pa.array(shapely.get_x(centroids)),
                "lat": pa.array(shapely.get_y(centroids)),
                "outline": pa.array(outlines),
            }
        ),
        CENTROID_INDEX,
        compression="zstd",
    )


def _index_table() -> Any:
    """The local index, rebuilt if it predates the outline column."""
    if CENTROID_INDEX.exists():
        table = pq.read_table(CENTROID_INDEX)
        if "outline" in table.column_names:
            return table
    build_centroid_index()
    return pq.read_table(CENTROID_INDEX)


def _row_for(pincode: str, table: Any) -> int:
    codes = table.column("pincode").to_pylist()
    try:
        return codes.index(pincode)
    except ValueError as exc:
        raise PincodeNotFound(f"pincode {pincode} has no boundary polygon") from exc


def get_pincode_outline(pincode: str) -> list[list[float]]:
    """The pincode's outer ring as [lon, lat] pairs, for drawing only.

    Interior rings are dropped and a multi-part pincode yields its largest
    part: this is a locator sketch, not a survey.
    """
    table = _index_table()
    geometry = shapely.from_wkb(
        table.column("outline")[_row_for(pincode, table)].as_py()
    )
    if geometry.geom_type == "MultiPolygon":
        geometry = max(geometry.geoms, key=lambda part: part.area)
    return [[round(x, 6), round(y, 6)] for x, y in geometry.exterior.coords]


def get_pincode_centroid(pincode: str) -> tuple[float, float]:
    """(lon, lat) of the pincode's boundary polygon centroid.

    Planar centroid of the polygon. Checked against Earth Engine's geodesic
    centroid for the reference pincode: the two agree to within 3 cm, far
    inside a ~9 km ERA5-Land cell.
    """
    table = _index_table()
    row = _row_for(pincode, table)
    return (
        float(table.column("lon")[row].as_py()),
        float(table.column("lat")[row].as_py()),
    )


def snap_to_era5_pixel(lon: float, lat: float) -> tuple[float, float]:
    """Snap a coordinate to the center of its ERA5-Land grid cell.

    Done by sampling the grid itself rather than rounding to 0.1 degrees:
    the collection's own reprojection is what decides a cell's center, and
    it does not land exactly on a tenth of a degree.
    """
    ee = _init_ee()
    image = (
        ee.ImageCollection(ERA5_COLLECTION)
        .filterDate("2005-01-01", "2005-01-02")
        .first()
    )
    try:
        sample = (
            image.select("temperature_2m")
            .sample(
                region=ee.Geometry.Point([lon, lat]),
                scale=ERA5_SCALE_M,
                geometries=True,
            )
            .first()
            .getInfo()
        )
    except Exception as exc:  # noqa: BLE001
        raise UpstreamError(f"Earth Engine sample failed: {exc}") from exc
    if not sample:
        raise UpstreamError(f"no ERA5-Land cell covers {lat}, {lon} (land only)")
    pixel = sample["geometry"]["coordinates"]
    return float(pixel[0]), float(pixel[1])


def resolve_location(pincode: str, *, use_cache: bool = True) -> dict[str, Any]:
    """Orchestrator: pincode -> centroid + pixel.

    Cached independently of whether a data fetch ever happens.
    """
    if use_cache:
        entry = cache.get_cache_entry(pincode)
        if entry and "pixel_lat" in entry:
            return {
                "pincode": pincode,
                "centroid": (entry["centroid_lon"], entry["centroid_lat"]),
                "pixel": (entry["pixel_lon"], entry["pixel_lat"]),
                "outline": get_pincode_outline(pincode),
                "attributes": entry.get("attributes", {}),
                "cached": True,
            }
    attributes = verify_pincode(pincode)
    centroid = get_pincode_centroid(pincode)
    pixel = snap_to_era5_pixel(*centroid)
    cache.save_resolved_location(pincode, centroid, pixel, attributes)
    return {
        "pincode": pincode,
        "centroid": centroid,
        "pixel": pixel,
        "outline": get_pincode_outline(pincode),
        "attributes": attributes,
        "cached": False,
    }
