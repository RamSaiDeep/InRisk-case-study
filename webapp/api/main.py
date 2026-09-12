"""The API layer: thin wrappers only.

Every route calls exactly one thing from the layers below and translates its
result or error into HTTP. No business logic lives here.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from data_layer import cache, jobs, location
from data_layer.config import (
    CACHE_IS_EPHEMERAL,
    ERA5_CELL_DEG,
    REPORT_EXPORT_ENABLED,
    Misconfigured,
    NotCached,
    PincodeNotFound,
    UpstreamError,
    latest_complete_year,
)
from pricing_engine import InvalidInputs, price

from . import exports
from .schemas import (
    Coordinate,
    DataRequest,
    DataResponse,
    JobResponse,
    LocationRequest,
    LocationResponse,
    PriceRequest,
    PriceResponse,
    SeriesResponse,
    SeriesYear,
)

app = FastAPI(
    title="Parametric weather-index pricing workbench",
    version="0.1.0",
    summary="Prices a weather-index insurance contract for any Indian pincode.",
)


# --- error mapping: this layer's one HTTP-specific responsibility ---------
#
# pincode not found -> 404   upstream schema changed -> 502
# server misconfigured -> 500   priced before data fetched -> 409
# invalid input (bad slider state) -> 422


def _error(status: int, kind: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail, "kind": kind})


class JobNotFound(Exception):
    """An expired or mistyped job id. Job state is in memory, so it does not
    survive a restart - which the frontend must treat as "fetch again"."""


@app.exception_handler(JobNotFound)
async def _job_not_found(_: Request, exc: JobNotFound) -> JSONResponse:
    return _error(404, "job_not_found", str(exc))


@app.exception_handler(RequestValidationError)
async def _request_invalid(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Normalize pydantic's own 422 into the same shape every other error
    uses, so the frontend has one error contract rather than two."""
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(part) for part in first.get("loc", ())[1:])
    message = first.get("msg", "invalid request")
    return _error(422, "invalid_inputs", f"{field}: {message}" if field else message)


@app.exception_handler(PincodeNotFound)
async def _not_found(_: Request, exc: PincodeNotFound) -> JSONResponse:
    return _error(404, "pincode_not_found", str(exc))


@app.exception_handler(UpstreamError)
async def _upstream(_: Request, exc: UpstreamError) -> JSONResponse:
    return _error(502, "upstream_error", str(exc))


@app.exception_handler(Misconfigured)
async def _misconfigured(_: Request, exc: Misconfigured) -> JSONResponse:
    return _error(500, "misconfigured", str(exc))


@app.exception_handler(NotCached)
async def _not_cached(_: Request, exc: NotCached) -> JSONResponse:
    return _error(409, "not_cached", str(exc))


@app.exception_handler(InvalidInputs)
async def _invalid_inputs(_: Request, exc: InvalidInputs) -> JSONResponse:
    return _error(422, "invalid_inputs", str(exc))


# --- routes ---------------------------------------------------------------


@app.get("/api/health")
def health() -> dict[str, object]:
    """Enough for the frontend to show the usable year range on first load."""
    return {
        "status": "ok",
        "latest_complete_year": latest_complete_year(),
        # A deployed instance keeps nothing between restarts, so the frontend
        # can say that rather than implying the fetch is a one-off.
        "ephemeral": CACHE_IS_EPHEMERAL,
        "report_export": REPORT_EXPORT_ENABLED,
    }


@app.post("/api/location", response_model=LocationResponse)
def resolve(request: LocationRequest) -> LocationResponse:
    """Fast confirmation step - shows the resolved pixel before committing to
    a slow fetch."""
    resolved = location.resolve_location(request.pincode)
    return LocationResponse(
        pincode=resolved["pincode"],
        centroid=Coordinate(lat=resolved["centroid"][1], lon=resolved["centroid"][0]),
        pixel=Coordinate(lat=resolved["pixel"][1], lon=resolved["pixel"][0]),
        outline=resolved["outline"],
        cell_deg=ERA5_CELL_DEG,
        attributes=resolved["attributes"],
        cached=resolved["cached"],
    )


@app.post("/api/data", response_model=DataResponse)
def request_data(request: DataRequest) -> DataResponse:
    """Returns immediately with either "ready" or a job_id to poll."""
    if cache.covers_range(request.pincode, request.start_year, request.end_year):
        entry = cache.get_cache_entry(request.pincode) or {}
        return DataResponse(
            status="ready", pincode=request.pincode, rows=entry.get("rows")
        )
    job_id = jobs.start_fetch_job(
        request.pincode, request.start_year, request.end_year
    )
    return DataResponse(status="fetching", pincode=request.pincode, job_id=job_id)


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def job_status(job_id: str) -> JobResponse:
    """Pollable progress for the fetching screen."""
    status = jobs.get_status(job_id)
    if status is None:
        raise JobNotFound(f"no job {job_id}")
    return JobResponse(**status)


@app.get("/api/series/{pincode}", response_model=SeriesResponse)
def series(pincode: str, offset: int = 0, limit: int = 50) -> SeriesResponse:
    """The fetched readings themselves - a year-by-year summary plus a window
    of daily rows, so the data can be looked at before anything is priced."""
    frame = cache.read_cached_df(pincode)
    if frame is None:
        raise NotCached(f"{pincode} has not been fetched yet")
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values("date")
    grouped = frame.groupby(frame["date"].dt.year)["ssrd_kwh_m2"]
    window = frame.iloc[offset : offset + min(limit, 500)]
    return SeriesResponse(
        pincode=pincode,
        rows=len(frame),
        first_day=frame["date"].iloc[0].date().isoformat(),
        last_day=frame["date"].iloc[-1].date().isoformat(),
        years=[
            SeriesYear(year=int(year), days=int(values.count()), sunlight_sum=float(values.sum()))
            for year, values in grouped
        ],
        daily=[
            {
                "date": row.date.date().isoformat(),
                "ssrd_j_m2": float(row.ssrd_j_m2),
                "ssrd_kwh_m2": float(row.ssrd_kwh_m2),
            }
            for row in window.itertuples()
        ],
        offset=offset,
        limit=limit,
    )


@app.post("/api/price", response_model=PriceResponse)
def price_contract(request: PriceRequest) -> PriceResponse:
    """Fires on every input change.

    Never touches bharatlas or Earth Engine: if the pincode is not cached it
    fails with 409 rather than fetching on the fly.
    """
    result = _price(request)
    return PriceResponse.from_result(
        result, request.pincode, request.start_year, request.end_year
    )


def _price(request: PriceRequest):
    """Shared by /api/price and both exports, so they cannot drift apart."""
    if not cache.covers_range(request.pincode, request.start_year, request.end_year):
        raise NotCached(
            f"{request.pincode} has no cached data for "
            f"{request.start_year}-{request.end_year} - fetch it first"
        )
    series = cache.cached_daily_series(
        request.pincode, request.start_year, request.end_year
    )
    if not series:
        raise NotCached(f"{request.pincode} has a metadata entry but no data file")
    return price(series, request.inputs.to_engine())


@app.post("/api/export/xlsx")
def export_xlsx(request: PriceRequest):
    """Same result object as /api/price, rendered to a workbook."""
    return exports.xlsx_response(request, _price(request))


@app.post("/api/export/report")
def export_report(request: PriceRequest):
    """Same result object as /api/price, rendered to a PDF."""
    return exports.report_response(request, _price(request))


# --- the built frontend ---------------------------------------------------
#
# Mounted last, so every /api route wins over the catch-all. Absent in
# development, where Vite serves the UI and proxies /api here.

_UI_DIST = Path(__file__).resolve().parent.parent / "ui" / "dist"
if _UI_DIST.is_dir():
    app.mount("/", StaticFiles(directory=_UI_DIST, html=True), name="ui")
