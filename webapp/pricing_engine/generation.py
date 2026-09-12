"""Step 2 - modelled generation.

AEP50 does not enter this step at all: it is a user input that flows
straight through as the trigger, never derived from or compared against
modelled generation here.
"""

from __future__ import annotations

from collections.abc import Sequence

from .types import AnnualIndexRow, GenerationRow


def model_year_generation(index: float, pr: float, capacity_kw: float) -> float:
    """The physical formula: index x PR x capacity, in kWh.

    The entire generation methodology lives in this one line.
    """
    return index * pr * capacity_kw


def apply_generation(
    rows: Sequence[AnnualIndexRow], pr: float, capacity_kw: float
) -> list[GenerationRow]:
    """Orchestrator: annual index table -> table with generation added."""
    return [
        GenerationRow(
            year=row.year,
            days=row.days,
            sunlight_sum=row.sunlight_sum,
            index=row.index,
            generation=model_year_generation(row.index, pr, capacity_kw),
        )
        for row in rows
    ]


def generation_series(rows: Sequence[GenerationRow]) -> list[float]:
    return [row.generation for row in rows]
