"""Export formatters.

Both take the same result object /api/price returns, so a downloaded file can
never disagree with what is on screen.
"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse, Response, StreamingResponse

from data_layer import cache
from data_layer.config import REPORT_EXPORT_ENABLED, NotCached
from pricing_engine import PricingResult

from .contract_terms import DEFAULT_TERMS
from .report import build_pdf
from .workbook import build_workbook


def _meta(request: Any) -> dict[str, Any]:
    """Where this pricing run happened - read from the cache entry written
    when the data was fetched, so an export always names the pixel the numbers
    actually came from."""
    entry = cache.get_cache_entry(request.pincode) or {}
    return {
        "pincode": request.pincode,
        "start_year": request.start_year,
        "end_year": request.end_year,
        "pixel_lat": entry.get("pixel_lat", float("nan")),
        "pixel_lon": entry.get("pixel_lon", float("nan")),
        "attributes": entry.get("attributes", {}),
    }


def xlsx_response(request: Any, result: PricingResult) -> StreamingResponse:
    frame = cache.read_cached_df(request.pincode)
    if frame is None:
        raise NotCached(f"{request.pincode} has no cached data file to export")
    frame = frame.copy()
    frame["date"] = frame["date"].astype("datetime64[ns]")
    years = frame["date"].dt.year
    frame = frame[(years >= request.start_year) & (years <= request.end_year)]
    stream = build_workbook(
        result, request.inputs.to_engine(), frame, _meta(request), DEFAULT_TERMS
    )
    filename = f"Solar_Parametric_{request.pincode}_{request.start_year}-{request.end_year}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def report_response(request: Any, result: PricingResult) -> Response:
    if not REPORT_EXPORT_ENABLED:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "the report export is switched off on this instance",
                "kind": "export_disabled",
            },
        )
    pdf = build_pdf(result, request.inputs.to_engine(), _meta(request), DEFAULT_TERMS)
    filename = f"Solar_Parametric_{request.pincode}_{request.start_year}-{request.end_year}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
