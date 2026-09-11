"""Daily rooftop-solar generation model driven by ERA5-Land.

The index must be a deterministic, auditable function of published weather
data -- no site telemetry -- so generation is *modelled*, never metered:

    E_d = C_kwp * GHI_d * PR_ref * (1 + gamma * (T_cell_d - 25))
    T_cell_d = T_amb_d + k * GHI_d

`PR_ref` is not the client's 80%: it is solved so that the 20-year mean of
the modelled annual energy equals the contractual AEP50 of 4,600 kWh. That
keeps the temperature term from double-counting losses the client's headline
PR already embeds, and anchors the index to the number the customer was sold.
"""

from __future__ import annotations

import pandas as pd

from . import config


def add_generation(
    df: pd.DataFrame,
    system: config.SystemSpec = config.SYSTEM,
    pv: config.PVModelSpec = config.PVMODEL,
) -> tuple[pd.DataFrame, float]:
    """Append modelled cell temperature and daily energy. Returns (df, PR_ref)."""
    out = df.copy()
    out["t_cell_c"] = out["temperature_c"] + pv.k_cell_rise * out["ssrd_kwh_m2"]
    out["temp_derate"] = 1.0 + pv.gamma_per_c * (out["t_cell_c"] - pv.t_ref_c)

    uncalibrated = system.capacity_kwp * out["ssrd_kwh_m2"] * out["temp_derate"]
    n_years = out["year"].nunique()
    pr_ref = system.aep50_kwh / (uncalibrated.sum() / n_years)

    out["gen_kwh"] = uncalibrated * pr_ref
    return out, pr_ref


def monthly_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Years x months matrix of modelled generation (kWh)."""
    return df.groupby(["year", "month"])["gen_kwh"].sum().unstack()


def monthly_normals(
    monthly: pd.DataFrame, system: config.SystemSpec = config.SYSTEM
) -> pd.Series:
    """Contractual monthly normals: climatology rescaled to sum to AEP50."""
    normals = monthly.mean()
    return normals * system.aep50_kwh / normals.sum()
