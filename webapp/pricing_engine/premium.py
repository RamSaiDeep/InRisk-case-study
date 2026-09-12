"""Step 4 - premium."""

from __future__ import annotations

import statistics
from collections.abc import Sequence

from .contract import InvalidInputs
from .types import PremiumBreakdown


def compute_burn_cost(payouts: Sequence[float]) -> float:
    """Mean payout across all years - the honest, no-margin cost of the risk.

    All years, including the ones that pay nothing.
    """
    if not payouts:
        raise InvalidInputs("no years to average")
    return statistics.fmean(payouts)


def compute_payout_sigma(payouts: Sequence[float]) -> float:
    """Sample standard deviation (n-1) of payout, across all years.

    Across every year including the zero-payout ones - this measures how
    much the payout swings year to year, which is a different question from
    how severe a paying year is. Feeds the risk margin only.
    """
    if len(payouts) < 2:
        raise InvalidInputs("at least two years are needed to measure variation")
    return statistics.stdev(payouts)


def compute_risk_margin(payout_sigma: float, risk_coeff: float) -> float:
    """Standard-deviation premium principle."""
    return risk_coeff * payout_sigma


def gross_up(
    burn_cost: float, risk_margin: float, expense_pct: float, profit_pct: float
) -> tuple[float, float]:
    """(technical premium, gross premium).

    Expenses and profit are shares of the final price, not of the cost, so
    this divides rather than adding them on. Both numbers are returned so a
    premium waterfall can render every step.
    """
    if expense_pct + profit_pct >= 1:
        raise InvalidInputs("expense_pct + profit_pct must be below 1")
    technical = burn_cost + risk_margin
    return technical, technical / (1 - expense_pct - profit_pct)


def compute_premium(
    payouts: Sequence[float],
    risk_coeff: float,
    expense_pct: float,
    profit_pct: float,
) -> PremiumBreakdown:
    """Orchestrator: payout series -> full premium breakdown."""
    burn_cost = compute_burn_cost(payouts)
    payout_sigma = compute_payout_sigma(payouts)
    risk_margin = compute_risk_margin(payout_sigma, risk_coeff)
    technical, gross = gross_up(burn_cost, risk_margin, expense_pct, profit_pct)
    return PremiumBreakdown(
        burn_cost=burn_cost,
        payout_sigma=payout_sigma,
        risk_margin=risk_margin,
        technical_premium=technical,
        gross_premium=gross,
    )
