"""Burn-cost analysis, Monte Carlo loss simulation and premium build-up."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from . import config, product


# --------------------------------------------------------------- burn cost
def burn_cost(payouts: pd.Series) -> dict:
    """Empirical statistics of the back-tested annual payouts."""
    n = len(payouts)
    hits = payouts[payouts > 0]
    return {
        "years": n,
        "burn_cost_inr": float(payouts.mean()),
        "std_inr": float(payouts.std(ddof=1)),
        "hit_rate": float((payouts > 0).mean()),
        "mean_payout_given_hit_inr": float(hits.mean()) if len(hits) else 0.0,
        "max_inr": float(payouts.max()),
        "se_of_burn_inr": float(payouts.std(ddof=1) / np.sqrt(n)),
    }


def trend_test(annual: pd.Series) -> dict:
    """Is the index trending? Drives the normals-period discussion."""
    res = stats.linregress(annual.index.values.astype(float), annual.values)
    return {
        "slope_per_year": float(res.slope),
        "pct_per_decade": float(100 * res.slope * 10 / annual.mean()),
        "p_value": float(res.pvalue),
        "r_squared": float(res.rvalue**2),
    }


# ------------------------------------------------------------- monte carlo
@dataclass
class SimulationResult:
    payouts: np.ndarray

    @property
    def expected_loss(self) -> float:
        return float(self.payouts.mean())

    @property
    def std(self) -> float:
        return float(self.payouts.std(ddof=1))

    def percentiles(self, qs=(50, 75, 90, 95, 99, 99.5)) -> dict:
        return {f"P{q}": float(np.percentile(self.payouts, q)) for q in qs}

    @property
    def hit_rate(self) -> float:
        return float((self.payouts > 0).mean())


def simulate(
    monthly_index: pd.DataFrame,
    normals: pd.Series,
    pricing: config.PricingSpec = config.PRICING,
    prod: config.ProductSpec = config.PRODUCT,
) -> SimulationResult:
    """Multivariate-lognormal resampling of the 12 monthly indices.

    Monthly log-anomalies are assumed jointly normal with the empirical
    correlation structure (so a poor July and a poor August co-occur at the
    observed rate). Their dispersion is scaled by `variance_inflation` to
    offset the smoothing of a 9 km reanalysis grid relative to point
    observations -- see the limitations section of the report.
    """
    rng = np.random.default_rng(pricing.random_seed)

    log_anom = np.log(monthly_index / normals)
    mu = log_anom.mean().values
    sigma = log_anom.std(ddof=1).values * pricing.variance_inflation

    corr = np.corrcoef(log_anom.values, rowvar=False)
    # nearest-PSD nudge: 20 years of data can yield a near-singular matrix
    eigenvalues, eigenvectors = np.linalg.eigh(corr)
    corr = eigenvectors @ np.diag(np.clip(eigenvalues, 1e-6, None)) @ eigenvectors.T
    d = np.sqrt(np.diag(corr))
    corr = corr / np.outer(d, d)
    chol = np.linalg.cholesky(corr)

    z = rng.standard_normal((pricing.n_simulations, 12)) @ chol.T
    sim_index = normals.values * np.exp(mu + z * sigma)

    return SimulationResult(product.annual_payout_array(sim_index, normals.values, prod))


# ----------------------------------------------------------------- premium
def premium_buildup(
    expected_loss: float,
    payout_std: float,
    pricing: config.PricingSpec = config.PRICING,
    prod: config.ProductSpec = config.PRODUCT,
    system: config.SystemSpec = config.SYSTEM,
) -> dict:
    """Expected loss -> risk load -> expenses -> gross commercial premium."""
    risk_load = pricing.risk_load_factor * payout_std
    technical = expected_loss + risk_load
    gross = technical / (1.0 - pricing.expense_ratio)

    return {
        "expected_loss_inr": expected_loss,
        "risk_load_inr": risk_load,
        "technical_premium_inr": technical,
        "expense_and_margin_inr": gross - technical,
        "gross_premium_inr": gross,
        "gross_premium_rounded_inr": float(np.ceil(gross / 25.0) * 25.0),
        "expected_loss_ratio": expected_loss / gross,
        "rate_on_line": gross / prod.max_payout_inr,
        "pct_of_annual_savings": gross / system.expected_annual_savings_inr,
        "pct_of_capex": gross / system.capex_inr,
    }
