"""Test fixtures.

The CSV loader lives here deliberately: parsing files is the data layer's
job, and the pricing engine must stay importable without it.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest

from pricing_engine import DailyReading

FIXTURES = Path(__file__).parent / "fixtures"
REFERENCE_CSV = FIXTURES / "ERA5_SSRD_380006_2005_2024.csv"


def load_daily(path: Path) -> list[DailyReading]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            DailyReading(
                day=date.fromisoformat(row["date"][:10]),
                ssrd=float(row["ssrd_kwh_m2"]),
            )
            for row in csv.DictReader(handle)
        ]


@pytest.fixture(scope="session")
def reference_daily() -> list[DailyReading]:
    """Pincode 380006, SSRD daily sums, 2005-2024 - the submitted dataset."""
    return load_daily(REFERENCE_CSV)
