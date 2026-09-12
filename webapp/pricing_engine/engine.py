"""Top-level orchestrator. Owns sequencing only - no formula lives here."""

from __future__ import annotations

from collections.abc import Iterable

from .bands import apply_bands
from .contract import PricingInputs
from .generation import apply_generation
from .index import compute_annual_index
from .premium import compute_premium
from .stats import compute_summary_stats
from .types import DailyReading, PricingResult


def price(daily: Iterable[DailyReading], inputs: PricingInputs) -> PricingResult:
    """The single entry point the API calls.

    Pure: no file reads, no network, no cache lookups - which is what makes
    it cheap enough to re-run on every slider change.
    """
    annual = compute_annual_index(daily)
    generation = apply_generation(annual, inputs.pr, inputs.capacity_kw)
    backtest, bands = apply_bands(
        generation,
        trigger=inputs.aep50,
        tariff=inputs.tariff,
        boundary_sigmas=inputs.boundary_sigmas,
        payout_sigmas=inputs.payout_sigmas,
    )
    payouts = [row.payout for row in backtest]
    return PricingResult(
        backtest=tuple(backtest),
        bands=bands,
        premium=compute_premium(
            payouts, inputs.risk_coeff, inputs.expense_pct, inputs.profit_pct
        ),
        summary=compute_summary_stats(
            backtest, inputs.levels, inputs.aep50, bands.sigma
        ),
    )
