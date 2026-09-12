"""Request and response shapes.

Pydantic owns input validation so a bad slider state is rejected here, as a
422, before any engine function sees it.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

from pricing_engine import PricingInputs

Pincode = Annotated[str, Field(pattern=r"^\d{6}$", description="Six-digit Indian pincode")]


class Coordinate(BaseModel):
    lat: float
    lon: float


# --- /api/location --------------------------------------------------------


class LocationRequest(BaseModel):
    pincode: Pincode


class LocationResponse(BaseModel):
    pincode: str
    centroid: Coordinate
    pixel: Coordinate
    #: Outer ring as [lon, lat] pairs, simplified for drawing only.
    outline: list[list[float]]
    #: ERA5-Land grid step in degrees, so the cell can be drawn around pixel.
    cell_deg: float
    attributes: dict[str, str]
    cached: bool


# --- /api/data ------------------------------------------------------------


class YearRange(BaseModel):
    start_year: int = Field(ge=1950)
    end_year: int

    @model_validator(mode="after")
    def check_range(self) -> YearRange:
        from data_layer.config import latest_complete_year

        if self.end_year < self.start_year:
            raise ValueError("end_year cannot be before start_year")
        latest = latest_complete_year()
        if self.end_year > latest:
            raise ValueError(
                f"{self.end_year} is not a complete published year yet - "
                f"ERA5-Land's final data lags by two to three months, so the "
                f"latest usable year is {latest}"
            )
        if self.end_year - self.start_year < 1:
            raise ValueError("at least two years are needed to measure variation")
        return self


class DataRequest(YearRange):
    pincode: Pincode


class DataResponse(BaseModel):
    status: Literal["ready", "fetching"]
    pincode: str
    job_id: str | None = None
    rows: int | None = None


# --- /api/jobs/{job_id} ---------------------------------------------------


class JobResponse(BaseModel):
    job_id: str
    pincode: str
    start_year: int
    end_year: int
    status: Literal["pending", "running", "done", "error"]
    progress: float
    message: str
    rows: int | None = None
    error: str | None = None


class SeriesYear(BaseModel):
    year: int
    days: int
    sunlight_sum: float


class SeriesResponse(BaseModel):
    """What was actually fetched, for the reader to look at before pricing."""

    pincode: str
    rows: int
    first_day: str
    last_day: str
    years: list[SeriesYear]
    #: A window of daily readings, for the table.
    daily: list[dict[str, float | str]]
    offset: int
    limit: int


# --- /api/price -----------------------------------------------------------


class InputsModel(BaseModel):
    """Mirrors the engine's input contract one field for one field."""

    capacity_kw: float = Field(gt=0)
    pr: float = Field(gt=0, le=1)
    aep50: float = Field(gt=0, description="Also the trigger; taken as given")
    tariff: float = Field(gt=0)
    boundary_sigmas: list[float] = Field(description="Length N-1, strictly increasing")
    payout_sigmas: list[float] = Field(min_length=1, description="Length N")
    risk_coeff: float = Field(ge=0)
    expense_pct: float = Field(ge=0, lt=1)
    profit_pct: float = Field(ge=0, lt=1)

    def to_engine(self) -> PricingInputs:
        """The engine re-validates; this conversion is the only coupling."""
        return PricingInputs(
            capacity_kw=self.capacity_kw,
            pr=self.pr,
            aep50=self.aep50,
            tariff=self.tariff,
            boundary_sigmas=tuple(self.boundary_sigmas),
            payout_sigmas=tuple(self.payout_sigmas),
            risk_coeff=self.risk_coeff,
            expense_pct=self.expense_pct,
            profit_pct=self.profit_pct,
        )


class PriceRequest(BaseModel):
    pincode: Pincode
    start_year: int
    end_year: int
    inputs: InputsModel


class BacktestRowModel(BaseModel):
    year: int
    days: int
    sunlight_sum: float
    index: float
    generation: float
    level: int
    payout: float
    nearest_edge: float
    distance_to_edge: float


class BandsModel(BaseModel):
    sigma: float
    trigger: float
    boundaries: list[float]
    payouts: list[float]
    exit_level: float
    max_payout: float


class PremiumModel(BaseModel):
    burn_cost: float
    payout_sigma: float
    risk_margin: float
    technical_premium: float
    gross_premium: float


class SummaryModel(BaseModel):
    years: int
    years_triggering: int
    trigger_frequency: float
    average_payout_when_paying: float | None
    worst_year: int | None
    worst_year_payout: float | None
    level_year_counts: dict[int, int]
    mean_generation: float
    mean_generation_vs_trigger: float
    mean_generation_sigmas_from_trigger: float
    closest_call_year: int | None
    closest_call_distance: float | None


class PriceResponse(BaseModel):
    pincode: str
    start_year: int
    end_year: int
    backtest: list[BacktestRowModel]
    bands: BandsModel
    premium: PremiumModel
    summary: SummaryModel

    @classmethod
    def from_result(
        cls, result: Any, pincode: str, start_year: int, end_year: int
    ) -> PriceResponse:
        return cls(
            pincode=pincode,
            start_year=start_year,
            end_year=end_year,
            backtest=[BacktestRowModel(**row.__dict__ if not hasattr(row, "__slots__")
                      else {f: getattr(row, f) for f in row.__slots__})
                      for row in result.backtest],
            bands=BandsModel(
                sigma=result.bands.sigma,
                trigger=result.bands.trigger,
                boundaries=list(result.bands.boundaries),
                payouts=list(result.bands.payouts),
                exit_level=result.bands.exit_level,
                max_payout=result.bands.max_payout,
            ),
            premium=PremiumModel(
                **{f: getattr(result.premium, f) for f in result.premium.__slots__}
            ),
            summary=SummaryModel(
                **{f: getattr(result.summary, f) for f in result.summary.__slots__}
            ),
        )


class ErrorResponse(BaseModel):
    detail: str
    kind: str
