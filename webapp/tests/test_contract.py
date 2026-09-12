"""Input contract validation - the API layer's 422 cases."""

from __future__ import annotations

import pytest

from pricing_engine import REFERENCE_INPUTS, InvalidInputs, PricingInputs, price
from pricing_engine.contract import PricingInputs as _PI


def variant(**overrides) -> PricingInputs:
    base = {
        "capacity_kw": 3.0,
        "pr": 0.80,
        "aep50": 4600.0,
        "tariff": 5.75,
        "boundary_sigmas": (0.5, 1.0),
        "payout_sigmas": (0.25, 0.75, 1.25),
        "risk_coeff": 0.20,
        "expense_pct": 0.20,
        "profit_pct": 0.075,
    }
    return _PI(**(base | overrides))


def test_reference_inputs_are_valid():
    assert REFERENCE_INPUTS.levels == 3


def test_boundary_sigmas_must_be_strictly_increasing():
    with pytest.raises(InvalidInputs, match="strictly increasing"):
        variant(boundary_sigmas=(1.0, 0.5))
    with pytest.raises(InvalidInputs, match="strictly increasing"):
        variant(boundary_sigmas=(0.5, 0.5))


def test_payout_list_must_be_one_longer_than_boundary_list():
    with pytest.raises(InvalidInputs, match="one more entry"):
        variant(payout_sigmas=(0.25, 0.75))


def test_payouts_may_be_non_increasing():
    """Deliberate: a user may want a non-increasing payout curve."""
    assert variant(payout_sigmas=(1.25, 0.75, 0.25)).levels == 3


def test_loadings_must_leave_room():
    with pytest.raises(InvalidInputs, match="below 1"):
        variant(expense_pct=0.60, profit_pct=0.40)


def test_two_levels_price_end_to_end(reference_daily):
    """N is generalized: a two-level contract needs one boundary."""
    result = price(
        reference_daily, variant(boundary_sigmas=(0.75,), payout_sigmas=(0.4, 1.0))
    )
    assert len(result.bands.boundaries) == 1
    assert len(result.bands.payouts) == 2
    assert set(result.summary.level_year_counts) == {0, 1, 2}
    assert result.premium.gross_premium > 0


def test_single_level_needs_no_boundaries(reference_daily):
    result = price(reference_daily, variant(boundary_sigmas=(), payout_sigmas=(0.5,)))
    assert result.bands.boundaries == ()
    assert result.bands.exit_level == 4600.0
    assert result.summary.years_triggering == 6


def test_sigma_scales_with_pr_so_bands_move_too(reference_daily):
    """PR is not just a level shift: it rescales sigma, so band widths move
    while the trigger stays pinned at AEP50."""
    base = price(reference_daily, REFERENCE_INPUTS)
    lower_pr = price(reference_daily, variant(pr=0.75))
    assert lower_pr.bands.sigma < base.bands.sigma
    assert lower_pr.summary.years_triggering > base.summary.years_triggering
