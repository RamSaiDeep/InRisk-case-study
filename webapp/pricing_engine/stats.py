"""Step 5 - summary stats.

Answers "how often and how badly does this pay", which is a different
question from "what should this cost", even though both read the same
payout series.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence

from .types import BacktestRow, SummaryStats


def compute_summary_stats(
    backtest: Sequence[BacktestRow],
    levels: int,
    trigger: float,
    sigma: float,
) -> SummaryStats:
    """`levels` is N, so a level with no years still reports a zero count."""
    paying = [row for row in backtest if row.payout > 0]
    counts = {level: 0 for level in range(levels + 1)}
    for row in backtest:
        counts[row.level] = counts.get(row.level, 0) + 1
    # Worst year is the least generation, not the largest payout: with fixed
    # per-level payouts several years tie on payout, and the weather is what
    # ranks them.
    worst = min(backtest, key=lambda row: row.generation, default=None)
    mean_generation = (
        statistics.fmean([row.generation for row in backtest]) if backtest else 0.0
    )
    closest = min(backtest, key=lambda row: row.distance_to_edge, default=None)
    return SummaryStats(
        years=len(backtest),
        years_triggering=len(paying),
        trigger_frequency=len(paying) / len(backtest) if backtest else 0.0,
        average_payout_when_paying=(
            statistics.fmean([row.payout for row in paying]) if paying else None
        ),
        worst_year=worst.year if worst else None,
        worst_year_payout=worst.payout if worst else None,
        level_year_counts=counts,
        mean_generation=mean_generation,
        mean_generation_vs_trigger=(
            mean_generation / trigger - 1 if trigger else 0.0
        ),
        mean_generation_sigmas_from_trigger=(
            (mean_generation - trigger) / sigma if sigma else 0.0
        ),
        closest_call_year=closest.year if closest else None,
        closest_call_distance=closest.distance_to_edge if closest else None,
    )
