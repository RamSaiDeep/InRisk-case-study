"""Row and result types for the pricing engine.

Unit contract with the data layer: a "daily series" is a sequence of
`DailyReading`, whose `ssrd` is daily-summed Surface Solar Radiation
Downwards in **kWh/m2** (ERA5-Land publishes J/m2; the division by
3.6e6 belongs to the data layer, not here). Everything downstream
assumes that unit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class DailyReading:
    """One day of irradiance at the resolved ERA5-Land pixel."""

    day: date
    ssrd: float  # kWh/m2, daily sum


@dataclass(frozen=True, slots=True)
class YearGroup:
    """Raw per-year grouping, before any normalization."""

    year: int
    days: int  # readings present in the series, not calendar length
    sunlight_sum: float  # kWh/m2


@dataclass(frozen=True, slots=True)
class AnnualIndexRow:
    year: int
    days: int
    sunlight_sum: float
    index: float  # kWh/m2, normalized to a 365-day year


@dataclass(frozen=True, slots=True)
class GenerationRow:
    year: int
    days: int
    sunlight_sum: float
    index: float
    generation: float  # kWh


@dataclass(frozen=True, slots=True)
class BacktestRow:
    year: int
    days: int
    sunlight_sum: float
    index: float
    generation: float
    level: int  # 0 = no payout, 1 = least severe paying level, N = most severe
    payout: float  # currency units
    # Distance to the closest band edge (the trigger or any boundary). Small
    # values are the cliff-edge cases: a near-identical year on the other
    # side of that edge would have been paid a different fixed amount.
    nearest_edge: float  # kWh, the edge itself
    distance_to_edge: float  # kWh, always positive


@dataclass(frozen=True, slots=True)
class BandStructure:
    """The contract geometry, derived once per pricing run."""

    sigma: float  # std dev of modelled generation, kWh
    trigger: float  # kWh
    boundaries: tuple[float, ...]  # kWh, descending; length N-1
    payouts: tuple[float, ...]  # currency, one per level; length N

    @property
    def exit_level(self) -> float:
        """The generation at or below which the most severe payout applies."""
        return self.boundaries[-1] if self.boundaries else self.trigger

    @property
    def max_payout(self) -> float:
        """Sum insured: the most this contract can ever pay in one year."""
        return max(self.payouts)


@dataclass(frozen=True, slots=True)
class PremiumBreakdown:
    burn_cost: float
    payout_sigma: float
    risk_margin: float
    technical_premium: float
    gross_premium: float


@dataclass(frozen=True, slots=True)
class SummaryStats:
    years: int
    years_triggering: int
    trigger_frequency: float  # share of years with a payout, 0..1
    average_payout_when_paying: float | None  # None when no year pays
    worst_year: int | None  # lowest modelled generation
    worst_year_payout: float | None
    level_year_counts: dict[int, int]  # level -> year count, including level 0
    # Modelled generation against the trigger the user supplied. The contract
    # never derives one from the other, so this is the disclosure that says
    # how far apart they sit - and it moves when PR or capacity moves.
    mean_generation: float  # kWh
    mean_generation_vs_trigger: float  # share, e.g. 0.0124 = 1.24% above
    mean_generation_sigmas_from_trigger: float
    # The year that came closest to a band edge without crossing it.
    closest_call_year: int | None
    closest_call_distance: float | None  # kWh


@dataclass(frozen=True, slots=True)
class PricingResult:
    """What `price` returns: everything the API serializes, nothing more."""

    backtest: tuple[BacktestRow, ...]
    bands: BandStructure
    premium: PremiumBreakdown
    summary: SummaryStats
