"""API layer: routing and the error-mapping table.

No network: the cache is redirected to a temporary directory and seeded with
the reference series, so /api/price runs against real data while
/api/location and /api/data are exercised through stubs.
"""

from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from data_layer import cache, jobs, location
from data_layer.config import Misconfigured, PincodeNotFound, UpstreamError

REFERENCE_PAYLOAD = {
    "pincode": "380006",
    "start_year": 2005,
    "end_year": 2024,
    "inputs": {
        "capacity_kw": 3.0,
        "pr": 0.80,
        "aep50": 4600.0,
        "tariff": 5.75,
        "boundary_sigmas": [0.5, 1.0],
        "payout_sigmas": [0.25, 0.75, 1.25],
        "risk_coeff": 0.20,
        "expense_pct": 0.20,
        "profit_pct": 0.075,
    },
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    series_dir = tmp_path / "series"
    series_dir.mkdir()
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(cache, "METADATA_FILE", tmp_path / "metadata.json")
    monkeypatch.setattr(cache, "SERIES_DIR", series_dir)
    return TestClient(app)


@pytest.fixture
def seeded(client, reference_daily):
    """A cache holding the submitted 20-year series."""
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime([r.day for r in reference_daily]),
            "latitude": 22.999693294401865,
            "longitude": 72.601155692309760,
            "ssrd_j_m2": [r.ssrd * 3_600_000 for r in reference_daily],
            "ssrd_kwh_m2": [r.ssrd for r in reference_daily],
        }
    )
    cache.write_cache(
        "380006",
        frame,
        location={"pixel_lat": 22.999693294401865, "pixel_lon": 72.601155692309760},
        start_year=2005,
        end_year=2024,
    )
    return client


# --- health ---------------------------------------------------------------


def test_health_reports_the_usable_year_range(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["latest_complete_year"] >= 2024


# --- /api/price: the fast loop -------------------------------------------


def test_price_reproduces_the_reference_premium(seeded):
    response = seeded.post("/api/price", json=REFERENCE_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert body["bands"]["sigma"] == pytest.approx(84.65, abs=0.005)
    assert body["bands"]["max_payout"] == pytest.approx(608.43, abs=0.005)
    assert body["premium"]["burn_cost"] == pytest.approx(73.01, abs=0.005)
    assert body["premium"]["gross_premium"] == pytest.approx(137.48, abs=0.005)
    assert body["summary"]["years_triggering"] == 6
    assert len(body["backtest"]) == 20


def test_price_serializes_the_chart_fields(seeded):
    body = seeded.post("/api/price", json=REFERENCE_PAYLOAD).json()
    row_2024 = next(r for r in body["backtest"] if r["year"] == 2024)
    assert row_2024["distance_to_edge"] == pytest.approx(1.71, abs=0.01)
    assert body["summary"]["closest_call_year"] == 2024


def test_price_on_an_unfetched_pincode_is_409_not_a_fetch(client):
    """The endpoint must never fetch on the fly."""
    payload = REFERENCE_PAYLOAD | {"pincode": "110001"}
    response = client.post("/api/price", json=payload)
    assert response.status_code == 409
    assert response.json()["kind"] == "not_cached"


def test_price_with_out_of_order_bands_is_422(seeded):
    payload = {**REFERENCE_PAYLOAD, "inputs": {**REFERENCE_PAYLOAD["inputs"],
                                               "boundary_sigmas": [1.0, 0.5]}}
    response = seeded.post("/api/price", json=payload)
    assert response.status_code == 422
    assert response.json()["kind"] == "invalid_inputs"


def test_price_with_mismatched_list_lengths_is_422(seeded):
    payload = {**REFERENCE_PAYLOAD, "inputs": {**REFERENCE_PAYLOAD["inputs"],
                                               "payout_sigmas": [0.25, 0.75]}}
    assert seeded.post("/api/price", json=payload).status_code == 422


def test_price_with_loadings_over_one_is_422(seeded):
    payload = {**REFERENCE_PAYLOAD, "inputs": {**REFERENCE_PAYLOAD["inputs"],
                                               "expense_pct": 0.8, "profit_pct": 0.3}}
    assert seeded.post("/api/price", json=payload).status_code == 422


def test_malformed_pincode_is_422(client):
    assert client.post("/api/price", json=REFERENCE_PAYLOAD | {"pincode": "38000"}).status_code == 422
    assert client.post("/api/location", json={"pincode": "abcdef"}).status_code == 422


# --- /api/location: error mapping ---------------------------------------


def test_unknown_pincode_is_404(client, monkeypatch):
    def boom(pincode, **kwargs):
        raise PincodeNotFound(f"pincode {pincode} is not in the bharatlas layer")

    monkeypatch.setattr(location, "resolve_location", boom)
    response = client.post("/api/location", json={"pincode": "999999"})
    assert response.status_code == 404
    assert response.json()["kind"] == "pincode_not_found"


def test_upstream_schema_change_is_502(client, monkeypatch):
    def boom(pincode, **kwargs):
        raise UpstreamError("bharatlas did not return JSON - API shape changed")

    monkeypatch.setattr(location, "resolve_location", boom)
    response = client.post("/api/location", json={"pincode": "380006"})
    assert response.status_code == 502
    assert response.json()["kind"] == "upstream_error"


def test_missing_credentials_is_500(client, monkeypatch):
    def boom(pincode, **kwargs):
        raise Misconfigured("no Earth Engine credentials on this machine")

    monkeypatch.setattr(location, "resolve_location", boom)
    response = client.post("/api/location", json={"pincode": "380006"})
    assert response.status_code == 500
    assert response.json()["kind"] == "misconfigured"


def test_location_returns_both_coordinates(client, monkeypatch):
    monkeypatch.setattr(
        location,
        "resolve_location",
        lambda pincode, **kwargs: {
            "pincode": pincode,
            "centroid": (72.561220, 23.022274),
            "pixel": (72.601156, 22.999693),
            "outline": [[72.55, 23.01], [72.57, 23.01], [72.57, 23.03], [72.55, 23.01]],
            "attributes": {"Office_Name": "Ellisbridge SO"},
            "cached": True,
        },
    )
    body = client.post("/api/location", json={"pincode": "380006"}).json()
    assert body["pixel"] == {"lat": 22.999693, "lon": 72.601156}
    assert body["centroid"]["lat"] == 23.022274
    assert body["cached"] is True
    # The confirmation screen draws the boundary and the cell around the pixel.
    assert len(body["outline"]) == 4
    assert body["cell_deg"] == 0.1


# --- /api/data and jobs -------------------------------------------------


def test_data_returns_ready_when_already_cached(seeded):
    body = seeded.post(
        "/api/data", json={"pincode": "380006", "start_year": 2005, "end_year": 2024}
    ).json()
    assert body["status"] == "ready"
    assert body["rows"] == 7305
    assert body["job_id"] is None


def test_data_starts_a_job_when_not_cached(client, monkeypatch):
    monkeypatch.setattr(jobs, "start_fetch_job", lambda *a: "job123")
    body = client.post(
        "/api/data", json={"pincode": "110001", "start_year": 2005, "end_year": 2024}
    ).json()
    assert body == {"status": "fetching", "pincode": "110001", "job_id": "job123", "rows": None}


def test_an_incomplete_year_is_refused_as_422(client):
    """ERA5-Land's publication lag: the app never requests a year whose final
    data does not exist yet."""
    from data_layer.config import latest_complete_year

    response = client.post(
        "/api/data",
        json={"pincode": "380006", "start_year": 2005, "end_year": latest_complete_year() + 1},
    )
    assert response.status_code == 422
    assert "lags" in response.text


def test_a_single_year_is_refused(client):
    response = client.post(
        "/api/data", json={"pincode": "380006", "start_year": 2024, "end_year": 2024}
    )
    assert response.status_code == 422


def test_reversed_year_range_is_422(client):
    response = client.post(
        "/api/data", json={"pincode": "380006", "start_year": 2024, "end_year": 2005}
    )
    assert response.status_code == 422


def test_job_status_round_trip(client, monkeypatch):
    monkeypatch.setattr(
        jobs,
        "get_status",
        lambda job_id: {
            "job_id": job_id,
            "pincode": "380006",
            "start_year": 2005,
            "end_year": 2024,
            "status": "running",
            "progress": 0.6,
            "message": "Fetched 12/20 years (2016)",
            "rows": None,
            "error": None,
        },
    )
    body = client.get("/api/jobs/abc123").json()
    assert body["progress"] == 0.6
    assert body["message"] == "Fetched 12/20 years (2016)"


def test_unknown_job_is_404_with_its_own_kind(client, monkeypatch):
    monkeypatch.setattr(jobs, "get_status", lambda job_id: None)
    response = client.get("/api/jobs/nope")
    assert response.status_code == 404
    assert response.json()["kind"] == "job_not_found"


def test_every_422_uses_the_same_error_shape(client):
    """One error contract for the frontend: pydantic's own validation errors
    are normalized to {detail, kind} like the engine's."""
    body = client.post("/api/location", json={"pincode": "38000"}).json()
    assert body["kind"] == "invalid_inputs"
    assert "pincode" in body["detail"]


# --- exports (step 4) ---------------------------------------------------


def test_export_routes_share_the_price_path(seeded):
    """Both exports run the same pricing call, so they fail the same 409 an
    unfetched /api/price would. What they render is covered in test_exports."""
    unfetched = seeded.post("/api/export/xlsx", json=REFERENCE_PAYLOAD | {"pincode": "110001"})
    assert unfetched.status_code == 409
    assert seeded.post("/api/export/xlsx", json=REFERENCE_PAYLOAD).status_code == 200


# --- /api/series: the data table ----------------------------------------


def test_series_summarises_and_pages_the_fetched_data(seeded):
    body = seeded.get("/api/series/380006?offset=0&limit=5").json()
    assert body["rows"] == 7305
    assert body["first_day"] == "2005-01-01"
    assert body["last_day"] == "2024-12-31"
    assert len(body["years"]) == 20
    assert body["years"][0] == {"year": 2005, "days": 365, "sunlight_sum": pytest.approx(1985.888878, abs=1e-6)}
    assert len(body["daily"]) == 5
    assert body["daily"][0]["date"] == "2005-01-01"


def test_series_paging_moves_the_window(seeded):
    first = seeded.get("/api/series/380006?offset=0&limit=3").json()["daily"]
    second = seeded.get("/api/series/380006?offset=3&limit=3").json()["daily"]
    assert first[0]["date"] == "2005-01-01"
    assert second[0]["date"] == "2005-01-04"


def test_series_on_an_unfetched_pincode_is_409(client):
    assert client.get("/api/series/110001").status_code == 409
