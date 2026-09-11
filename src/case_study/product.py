"""Policy wording expressed as code.

Structure: an *annual aggregate generation-shortfall* cover.

    AGS_y = sum_m max(0, strike * Normal_m - Index_m)        [kWh]
    Payout_y = min( rate * max(0, AGS_y - deductible), limit )  [INR]

Two design choices carry the product:

1.  Shortfall is accumulated *monthly and never netted*. Annual GHI at this
    location has a CV of only ~1.8%, so a single annual index offsets a poor
    monsoon against a bright winter and never triggers -- see the structure
    comparison table. Summing monthly downside deviations preserves the
    within-year adverse spells that actually hurt a monthly EMI.

2.  A single annual deductible in kWh, rather than a deductible in every
    month, keeps the wording to three numbers and stops the policy paying
    trivial amounts that cost more to settle than they are worth.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def monthly_shortfall(
    monthly_index: pd.DataFrame,
    normals: pd.Series,
    prod: config.ProductSpec = config.PRODUCT,
) -> pd.DataFrame:
    """kWh by which each year x month cell falls below its strike."""
    return (prod.monthly_strike_fraction * normals - monthly_index).clip(lower=0.0)


def annual_shortfall(
    monthly_index: pd.DataFrame,
    normals: pd.Series,
    prod: config.ProductSpec = config.PRODUCT,
) -> pd.Series:
    """The index that settles the policy: AGS in kWh."""
    return monthly_shortfall(monthly_index, normals, prod).sum(axis=1)


def annual_payout(
    monthly_index: pd.DataFrame,
    normals: pd.Series,
    prod: config.ProductSpec = config.PRODUCT,
) -> pd.Series:
    """Settlement amount (INR) for each policy year."""
    ags = annual_shortfall(monthly_index, normals, prod)
    gross = prod.payout_rate_inr_per_kwh * (ags - prod.annual_deductible_kwh).clip(lower=0.0)
    return gross.clip(upper=prod.max_payout_inr)


def annual_payout_array(
    index: np.ndarray,
    normals: np.ndarray,
    prod: config.ProductSpec = config.PRODUCT,
) -> np.ndarray:
    """Vectorised twin of `annual_payout` for Monte Carlo (n_sims x 12)."""
    shortfall = np.clip(prod.monthly_strike_fraction * normals - index, 0.0, None)
    ags = shortfall.sum(axis=1)
    gross = prod.payout_rate_inr_per_kwh * np.clip(ags - prod.annual_deductible_kwh, 0.0, None)
    return np.minimum(gross, prod.max_payout_inr)


def exhaustion_point_kwh(prod: config.ProductSpec = config.PRODUCT) -> float:
    """Shortfall at which the limit is reached -- quoted in the policy schedule."""
    return prod.annual_deductible_kwh + prod.max_payout_inr / prod.payout_rate_inr_per_kwh


def annual_index_payout(
    annual_gen: pd.Series,
    strike_fraction: float,
    system: config.SystemSpec = config.SYSTEM,
) -> pd.Series:
    """Rejected alternative: a single netted annual index. Kept for comparison."""
    strike = strike_fraction * system.aep50_kwh
    return (strike - annual_gen).clip(lower=0.0) * system.tariff_inr_per_kwh
