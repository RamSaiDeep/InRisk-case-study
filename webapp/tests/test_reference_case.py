"""Regression test against the submitted case study.

Every number here comes from Solar_Parametric_Workings.xlsx at the
reference parameters. A deviation is a bug, not a rounding difference.
"""

from __future__ import annotations

import pytest

from pricing_engine import REFERENCE_INPUTS, price


@pytest.fixture(scope="module")
def result(reference_daily):
    return price(reference_daily, REFERENCE_INPUTS)


def test_twenty_complete_years(result):
    assert len(result.backtest) == 20
    assert result.backtest[0].year == 2005
    assert result.backtest[-1].year == 2024
    # Leap years normalize against 366 readings, not 365.
    assert {row.year for row in result.backtest if row.days == 366} == {
        2008, 2012, 2016, 2020, 2024
    }


def test_sigma_of_generation(result):
    assert result.bands.sigma == pytest.approx(84.65, abs=0.005)


def test_band_boundaries(result):
    assert result.bands.trigger == 4600.0
    assert result.bands.boundaries[0] == pytest.approx(4557.67, abs=0.005)
    assert result.bands.boundaries[1] == pytest.approx(4515.35, abs=0.005)
    assert result.bands.exit_level == pytest.approx(4515.35, abs=0.005)


def test_level_payouts(result):
    assert result.bands.payouts[0] == pytest.approx(121.69, abs=0.005)
    assert result.bands.payouts[1] == pytest.approx(365.06, abs=0.005)
    assert result.bands.payouts[2] == pytest.approx(608.43, abs=0.005)
    assert result.bands.max_payout == pytest.approx(608.43, abs=0.005)


def test_premium_build_up(result):
    assert result.premium.burn_cost == pytest.approx(73.01, abs=0.005)
    assert result.premium.payout_sigma == pytest.approx(133.30, abs=0.005)
    assert result.premium.risk_margin == pytest.approx(26.66, abs=0.005)
    assert result.premium.technical_premium == pytest.approx(99.67, abs=0.005)
    assert result.premium.gross_premium == pytest.approx(137.48, abs=0.005)


def test_summary_stats(result):
    assert result.summary.years_triggering == 6
    assert result.summary.trigger_frequency == pytest.approx(0.30)
    assert result.summary.average_payout_when_paying == pytest.approx(243.37, abs=0.005)
    assert result.summary.worst_year == 2019
    assert result.summary.worst_year_payout == pytest.approx(365.06, abs=0.005)
    # 14 dry, 3 mild, 3 moderate, 0 severe.
    assert result.summary.level_year_counts == {0: 14, 1: 3, 2: 3, 3: 0}


def test_which_years_pay_which_level(result):
    by_level = {}
    for row in result.backtest:
        by_level.setdefault(row.level, []).append(row.year)
    assert by_level[1] == [2011, 2016, 2024]
    assert by_level[2] == [2013, 2019, 2021]
    assert 3 not in by_level


def test_mean_generation_sits_above_aep50(result):
    """The disclosed consequence of modelling generation rather than
    anchoring it to AEP50."""
    mean_generation = sum(r.generation for r in result.backtest) / 20
    assert mean_generation == pytest.approx(4657.24, abs=0.01)
    assert mean_generation / REFERENCE_INPUTS.aep50 - 1 == pytest.approx(0.0124, abs=0.0001)
