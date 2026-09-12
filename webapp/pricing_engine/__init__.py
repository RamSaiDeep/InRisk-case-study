"""Pricing engine: pure functions, standard library only.

Nothing in this package reads a file, opens a socket, or touches the cache.
"""

from .bands import (
    apply_bands,
    assign_year_level_payout,
    compute_level_boundaries,
    compute_level_payouts,
    compute_sigma,
)
from .contract import REFERENCE_INPUTS, InvalidInputs, PricingInputs
from .engine import price
from .generation import apply_generation, model_year_generation
from .index import compute_annual_index, group_by_year, normalize_year
from .premium import (
    compute_burn_cost,
    compute_payout_sigma,
    compute_premium,
    compute_risk_margin,
    gross_up,
)
from .stats import compute_summary_stats
from .types import (
    AnnualIndexRow,
    BacktestRow,
    BandStructure,
    DailyReading,
    GenerationRow,
    PremiumBreakdown,
    PricingResult,
    SummaryStats,
    YearGroup,
)

__all__ = [
    "AnnualIndexRow",
    "BacktestRow",
    "BandStructure",
    "DailyReading",
    "GenerationRow",
    "InvalidInputs",
    "PremiumBreakdown",
    "PricingInputs",
    "PricingResult",
    "REFERENCE_INPUTS",
    "SummaryStats",
    "YearGroup",
    "apply_bands",
    "apply_generation",
    "assign_year_level_payout",
    "compute_annual_index",
    "compute_burn_cost",
    "compute_level_boundaries",
    "compute_level_payouts",
    "compute_payout_sigma",
    "compute_premium",
    "compute_risk_margin",
    "compute_sigma",
    "compute_summary_stats",
    "group_by_year",
    "gross_up",
    "model_year_generation",
    "normalize_year",
    "price",
]
