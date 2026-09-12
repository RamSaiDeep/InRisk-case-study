"""Step 1 - annual index. Pure grouping plus one methodology decision."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from .types import AnnualIndexRow, DailyReading, YearGroup

DAYS_IN_NORMAL_YEAR = 365


def group_by_year(daily: Iterable[DailyReading]) -> list[YearGroup]:
    """One row per calendar year: reading count and raw summed irradiance.

    No judgment calls here - `days` counts the readings actually present,
    which is what makes `normalize_year` able to scale a short year.
    """
    days: dict[int, int] = {}
    totals: dict[int, float] = {}
    for reading in daily:
        year = reading.day.year
        days[year] = days.get(year, 0) + 1
        totals[year] = totals.get(year, 0.0) + reading.ssrd
    return [
        YearGroup(year=year, days=days[year], sunlight_sum=totals[year])
        for year in sorted(days)
    ]


def normalize_year(sunlight_sum: float, days: int) -> float:
    """The 365-day leap-year correction: mean daily irradiance x 365.

    The one methodology decision in this step. Note this also rescales a
    year with missing readings as though it were complete, which is why the
    data layer never ingests an incomplete calendar year in the first place.
    """
    if days <= 0:
        raise ValueError("cannot normalize a year with no readings")
    return sunlight_sum / days * DAYS_IN_NORMAL_YEAR


def compute_annual_index(daily: Iterable[DailyReading]) -> list[AnnualIndexRow]:
    """Orchestrator: daily series -> full annual table."""
    return [
        AnnualIndexRow(
            year=group.year,
            days=group.days,
            sunlight_sum=group.sunlight_sum,
            index=normalize_year(group.sunlight_sum, group.days),
        )
        for group in group_by_year(daily)
    ]


def index_series(rows: Sequence[AnnualIndexRow]) -> list[float]:
    return [row.index for row in rows]
