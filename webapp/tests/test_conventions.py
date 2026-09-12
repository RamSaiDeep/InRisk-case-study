"""The conventions that are easy to get wrong and change every output."""

from __future__ import annotations

from datetime import date

import pytest

from pricing_engine import (
    DailyReading,
    InvalidInputs,
    assign_year_level_payout,
    compute_burn_cost,
    compute_payout_sigma,
    compute_sigma,
    group_by_year,
    gross_up,
    normalize_year,
)

TRIGGER = 4600.0
BOUNDARIES = (4557.674502, 4515.349003)
PAYOUTS = (121.685808, 365.057423, 608.429039)


def test_sigma_is_sample_not_population():
    # Population sigma of this series is 2.0; sample sigma is ~2.1381.
    assert compute_sigma([1, 3, 5, 7, 9][:]) == pytest.approx(3.1623, abs=0.0001)
    assert compute_sigma([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(2.1381, abs=0.0001)


def test_payout_sigma_spans_every_year_including_zeros():
    payouts = [0.0] * 14 + [121.685808] * 3 + [365.057423] * 3
    assert compute_payout_sigma(payouts) == pytest.approx(133.30, abs=0.005)


def test_reference_case_cannot_discriminate_the_payout_sigma_convention():
    """A trap worth documenting: on the submitted 14/3/3 split the sigma over
    all years and the sigma over paying years only agree to 2e-07, so the
    reference premium does NOT prove the convention is right."""
    payouts = [0.0] * 14 + [121.685808] * 3 + [365.057423] * 3
    paying_only = [p for p in payouts if p > 0]
    assert compute_payout_sigma(paying_only) == pytest.approx(133.30, abs=0.005)


def test_the_two_payout_sigma_conventions_do_diverge():
    """Same question asked of a series that can tell them apart: one paying
    year in twenty has no spread among payers at all."""
    payouts = [0.0] * 19 + [500.0]
    assert compute_payout_sigma(payouts) == pytest.approx(111.80, abs=0.005)
    with pytest.raises(InvalidInputs):
        compute_payout_sigma([p for p in payouts if p > 0])


def test_burn_cost_spans_every_year_including_zeros():
    payouts = [0.0] * 14 + [121.685808] * 3 + [365.057423] * 3
    assert compute_burn_cost(payouts) == pytest.approx(73.01, abs=0.005)


@pytest.mark.parametrize(
    ("generation", "expected_level"),
    [
        (4600.01, 0),  # above the trigger
        (4600.0, 0),   # exactly at the trigger: does not pay
        (4599.99, 1),
        (4557.674502, 1),  # exactly on the mild/moderate boundary: milder level
        (4557.674501, 2),
        (4515.349003, 2),  # exactly on the exit: still moderate
        (4515.349002, 3),
        (0.0, 3),
    ],
)
def test_boundary_comparisons_are_strict(generation, expected_level):
    level, payout = assign_year_level_payout(generation, TRIGGER, BOUNDARIES, PAYOUTS)
    assert level == expected_level
    assert payout == (0.0 if expected_level == 0 else PAYOUTS[expected_level - 1])


def test_normalize_scales_a_leap_year_down():
    assert normalize_year(366.0, 366) == pytest.approx(365.0)
    assert normalize_year(365.0, 365) == pytest.approx(365.0)


def test_normalize_rescales_a_short_year_as_if_complete():
    """Documented behaviour, and the reason the data layer refuses partial
    years: a gap is silently scaled up rather than flagged."""
    assert normalize_year(100.0, 100) == pytest.approx(365.0)


def test_group_by_year_counts_readings_present():
    daily = [
        DailyReading(day=date(2020, 1, 1), ssrd=5.0),
        DailyReading(day=date(2020, 1, 2), ssrd=5.0),
        DailyReading(day=date(2021, 1, 1), ssrd=4.0),
    ]
    groups = group_by_year(daily)
    assert [(g.year, g.days, g.sunlight_sum) for g in groups] == [
        (2020, 2, 10.0),
        (2021, 1, 4.0),
    ]


def test_gross_up_divides_rather_than_adding():
    technical, gross = gross_up(73.011485, 26.660025, 0.20, 0.075)
    assert technical == pytest.approx(99.67, abs=0.005)
    assert gross == pytest.approx(137.48, abs=0.005)
    # Adding the loadings on instead would land ~10 rupees low.
    assert gross != pytest.approx(technical * 1.275, abs=0.005)


def test_gross_up_rejects_loadings_that_reach_one():
    with pytest.raises(InvalidInputs):
        gross_up(73.0, 26.7, 0.80, 0.20)
