"""Step 3 - bands and payouts, generalized to N user-defined levels."""

from __future__ import annotations

import statistics
from collections.abc import Sequence

from .contract import InvalidInputs
from .types import BacktestRow, BandStructure, GenerationRow


def compute_sigma(generation: Sequence[float]) -> float:
    """Sample standard deviation (n-1) of modelled generation.

    Sample, not population: this is what the reference workbook's STDEV
    computes, and the value every boundary and payout is scaled from.
    Computed once per run and threaded into both, never recomputed.
    """
    if len(generation) < 2:
        raise InvalidInputs("at least two years are needed to measure variation")
    return statistics.stdev(generation)


def compute_level_boundaries(
    trigger: float, sigma: float, boundary_sigmas: Sequence[float]
) -> tuple[float, ...]:
    """N-1 kWh boundaries, descending from the trigger.

    Ordering of `boundary_sigmas` is validated by the input contract; this
    re-checks because the function is public and callable on its own.
    """
    for lower, upper in zip(boundary_sigmas, boundary_sigmas[1:]):
        if upper <= lower:
            raise InvalidInputs("boundary_sigmas must be strictly increasing")
    return tuple(trigger - multiple * sigma for multiple in boundary_sigmas)


def compute_level_payouts(
    sigma: float, tariff: float, payout_sigmas: Sequence[float]
) -> tuple[float, ...]:
    """One fixed amount per level: the shortfall at that point, in currency.

    Each payout point is a shortfall in sigma units; converting at the
    tariff is what makes the payout the value of the electricity the
    customer did not get.
    """
    return tuple(point * sigma * tariff for point in payout_sigmas)


def assign_year_level_payout(
    generation: float,
    trigger: float,
    boundaries: Sequence[float],
    payouts: Sequence[float],
) -> tuple[int, float]:
    """(level, payout) for one year.

    Walks least-severe to most-severe. Comparisons are strict `<`, matching
    the reference workbook: a year landing exactly on a boundary takes the
    milder level, and a year exactly at the trigger does not pay at all.
    """
    if generation >= trigger:
        return 0, 0.0
    level = 1
    for boundary in boundaries:
        if generation >= boundary:
            break
        level += 1
    return level, payouts[level - 1]


def apply_bands(
    rows: Sequence[GenerationRow],
    trigger: float,
    tariff: float,
    boundary_sigmas: Sequence[float],
    payout_sigmas: Sequence[float],
) -> tuple[list[BacktestRow], BandStructure]:
    """Orchestrator: computes sigma once, threads it into both sides."""
    sigma = compute_sigma([row.generation for row in rows])
    bands = BandStructure(
        sigma=sigma,
        trigger=trigger,
        boundaries=compute_level_boundaries(trigger, sigma, boundary_sigmas),
        payouts=compute_level_payouts(sigma, tariff, payout_sigmas),
    )
    edges = (trigger, *bands.boundaries)
    backtest = []
    for row in rows:
        level, payout = assign_year_level_payout(
            row.generation, trigger, bands.boundaries, bands.payouts
        )
        nearest_edge = min(edges, key=lambda edge: abs(row.generation - edge))
        backtest.append(
            BacktestRow(
                year=row.year,
                days=row.days,
                sunlight_sum=row.sunlight_sum,
                index=row.index,
                generation=row.generation,
                level=level,
                payout=payout,
                nearest_edge=nearest_edge,
                distance_to_edge=abs(row.generation - nearest_edge),
            )
        )
    return backtest, bands
