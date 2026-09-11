"""End-to-end analysis for the 380006 rooftop-solar parametric product.

Run from the repository root:

    .venv/Scripts/python.exe scripts/run_analysis.py

Writes every table quoted in REPORT.md to outputs/tables/ and every figure to
outputs/figures/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from case_study import config, data, generation, pricing, product  # noqa: E402

TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

INK, ACCENT, WARN = "#1f2933", "#2f6f9f", "#c1462e"
plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

results: dict = {}


def save(df: pd.DataFrame, name: str, **kw) -> pd.DataFrame:
    df.to_csv(TABLES / f"{name}.csv", **kw)
    return df


# =====================================================================
# 0. Data and quality control
# =====================================================================
daily = data.load_daily(str(ROOT / config.MASTER_CSV))
qc = data.quality_report(daily)
results["data_quality"] = qc
print("QC:", qc)

daily, pr_ref = generation.add_generation(daily)
monthly = generation.monthly_matrix(daily)
normals = generation.monthly_normals(monthly)
annual_gen = daily.groupby("year")["gen_kwh"].sum()

results["model"] = {
    "calibrated_pr_ref": pr_ref,
    "implied_effective_pr": float(
        config.SYSTEM.aep50_kwh
        / (config.SYSTEM.capacity_kwp * daily["ssrd_kwh_m2"].sum() / 20)
    ),
    "client_stated_pr": config.SYSTEM.performance_ratio,
    "mean_annual_ghi_kwh_m2": float(daily.groupby("year")["ssrd_kwh_m2"].sum().mean()),
    "mean_temp_derate": float(daily["temp_derate"].mean()),
    "mean_annual_gen_kwh": float(annual_gen.mean()),
    "annual_gen_cv_pct": float(100 * annual_gen.std(ddof=1) / annual_gen.mean()),
}
print("Model:", results["model"])


# =====================================================================
# TASK 1. Weather index selection -- variable screening
# =====================================================================
mm = (
    daily.groupby(["year", "month"])
    .agg(gen=("gen_kwh", "sum"), ghi=("ssrd_kwh_m2", "sum"),
         temp=("temperature_c", "mean"), precip=("precipitation_mm", "sum"),
         raindays=("precipitation_mm", lambda s: (s > 1.0).sum()))
    .reset_index()
)
# de-seasonalise: the question is which variable explains *anomalies*, not the
# shared annual cycle, which any variable would appear to "explain".
for col in ["gen", "ghi", "temp", "precip", "raindays"]:
    mm[f"{col}_a"] = mm[col] - mm.groupby("month")[col].transform("mean")

screen = []
for label, col in [("GHI (SSRD)", "ghi_a"), ("Mean temperature", "temp_a"),
                   ("Total precipitation", "precip_a"), ("Rain-day count", "raindays_a")]:
    r = stats.pearsonr(mm[col], mm["gen_a"])
    screen.append({
        "variable": label, "pearson_r": r.statistic, "r_squared": r.statistic**2,
        "unexplained_variance_pct": 100 * (1 - r.statistic**2), "p_value": r.pvalue,
    })
screening = save(pd.DataFrame(screen).round(4), "task1_variable_screening", index=False)
print("\nTask 1 screening:\n", screening.to_string(index=False))

# marginal contribution of the temperature term to the index itself
ghi_only = config.SYSTEM.capacity_kwp * daily["ssrd_kwh_m2"]
ghi_only = ghi_only * config.SYSTEM.aep50_kwh / (ghi_only.sum() / 20)
ghi_only_monthly = ghi_only.groupby([daily["year"], daily["month"]]).sum().unstack()
results["temperature_contribution"] = {
    "index_cv_ghi_only_pct": float(
        100 * ghi_only_monthly.sum(axis=1).std(ddof=1) / ghi_only_monthly.sum(axis=1).mean()),
    "index_cv_with_temp_pct": results["model"]["annual_gen_cv_pct"],
    "mean_abs_monthly_diff_kwh": float((monthly - ghi_only_monthly).abs().mean().mean()),
    "max_abs_monthly_diff_kwh": float((monthly - ghi_only_monthly).abs().max().max()),
}


# =====================================================================
# TASK 2/3. Structure choice -- monthly vs annual accumulation
# =====================================================================
struct = []
for frac in [0.90, 0.95, 0.98, 1.00]:
    ap = product.annual_index_payout(annual_gen, frac)
    struct.append({"structure": f"Netted annual index, strike {frac:.0%} of AEP50",
                   "burn_cost_inr": ap.mean(), "years_triggered": int((ap > 0).sum()),
                   "max_annual_inr": ap.max()})
for ded in [0.0, 60.0, 100.0, 140.0]:
    spec = config.ProductSpec(annual_deductible_kwh=ded)
    ap = product.annual_payout(monthly, normals, spec)
    struct.append({"structure": f"Monthly-accumulated AGS, deductible {ded:.0f} kWh",
                   "burn_cost_inr": ap.mean(), "years_triggered": int((ap > 0).sum()),
                   "max_annual_inr": ap.max()})
structures = save(pd.DataFrame(struct).round(1), "task2_structure_comparison", index=False)
print("\nStructure comparison:\n", structures.to_string(index=False))

# monthly interannual variability -- the evidence behind the structure choice
var_tbl = pd.DataFrame({
    "normal_kwh": normals.round(0),
    "std_kwh": monthly.std(ddof=1).round(1),
    "cv_pct": (100 * monthly.std(ddof=1) / monthly.mean()).round(2),
    "worst_year_pct_of_normal": (100 * monthly.min() / monthly.mean()).round(1),
})
var_tbl.index = config.MONTH_NAMES
save(var_tbl, "task1_monthly_variability", index_label="month")
print("\nMonthly variability:\n", var_tbl.to_string())


# =====================================================================
# TASK 3. Back-test and pricing
# =====================================================================
short_m = product.monthly_shortfall(monthly, normals)
ags = product.annual_shortfall(monthly, normals)
pay_a = product.annual_payout(monthly, normals)

backtest = pd.DataFrame({
    "modelled_generation_kwh": annual_gen.round(0),
    "pct_of_aep50": (100 * annual_gen / config.SYSTEM.aep50_kwh).round(1),
    "months_short": (short_m > 0).sum(axis=1),
    "AGS_index_kwh": ags.round(0),
    "payout_inr": pay_a.round(0),
})
save(backtest, "task3_backtest", index_label="year")
print("\nBack-test:\n", backtest.to_string())

burn = pricing.burn_cost(pay_a)
trend = pricing.trend_test(annual_gen)
results["burn_cost"] = burn
results["trend"] = trend
print("\nBurn:", {k: round(v, 3) for k, v in burn.items()})
print("Trend:", {k: round(v, 4) for k, v in trend.items()})

sim = pricing.simulate(monthly, normals)
results["simulation"] = {
    "expected_loss_inr": sim.expected_loss, "std_inr": sim.std,
    "hit_rate": sim.hit_rate, **sim.percentiles(),
}
print("Simulation:", {k: round(v, 1) for k, v in results["simulation"].items()})

prem = pricing.premium_buildup(sim.expected_loss, sim.std)
results["premium"] = prem
print("Premium:", {k: round(v, 3) for k, v in prem.items()})

save(pd.DataFrame([
    {"component": "Expected loss (burn cost, simulated)", "inr": prem["expected_loss_inr"]},
    {"component": f"Risk load ({config.PRICING.risk_load_factor:.0%} x sd)", "inr": prem["risk_load_inr"]},
    {"component": "= Technical premium", "inr": prem["technical_premium_inr"]},
    {"component": f"Expenses & margin ({config.PRICING.expense_ratio:.0%} of gross)", "inr": prem["expense_and_margin_inr"]},
    {"component": "= Gross commercial premium", "inr": prem["gross_premium_inr"]},
]).round(0), "task3_premium_buildup", index=False)

# --- sensitivities -------------------------------------------------------
sens = []
for ded in [60.0, 80.0, 100.0, 120.0, 140.0]:
    spec = config.ProductSpec(annual_deductible_kwh=ded)
    s = pricing.simulate(monthly, normals, prod=spec)
    p = pricing.premium_buildup(s.expected_loss, s.std, prod=spec)
    hist = product.annual_payout(monthly, normals, spec)
    sens.append({
        "deductible_kwh": ded, "historical_burn_inr": hist.mean(),
        "simulated_EL_inr": s.expected_loss, "hit_rate_pct": 100 * s.hit_rate,
        "gross_premium_inr": p["gross_premium_inr"],
        "premium_pct_of_savings": 100 * p["pct_of_annual_savings"],
    })
save(pd.DataFrame(sens).round(2), "task3_deductible_sensitivity", index=False)

vsens = []
for k in [1.0, 1.25, 1.5, 2.0]:
    ps = config.PricingSpec(variance_inflation=k)
    s = pricing.simulate(monthly, normals, pricing=ps)
    p = pricing.premium_buildup(s.expected_loss, s.std, pricing=ps)
    vsens.append({"variance_inflation": k, "implied_annual_cv_pct": results["model"]["annual_gen_cv_pct"] * k,
                  "expected_loss_inr": s.expected_loss, "gross_premium_inr": p["gross_premium_inr"]})
save(pd.DataFrame(vsens).round(2), "task3_variance_sensitivity", index=False)

# normals estimated on the most recent decade instead of the full record
recent = monthly.loc[2015:]
recent_norm = recent.mean() * config.SYSTEM.aep50_kwh / recent.mean().sum()
results["normals_period"] = {
    "burn_20yr_normals_inr": float(pay_a.mean()),
    "burn_10yr_normals_inr": float(product.annual_payout(monthly, recent_norm).mean()),
}
print("Normals period:", results["normals_period"])


# =====================================================================
# Figures
# =====================================================================
# 1 -- where the risk actually sits
fig, ax = plt.subplots(figsize=(7.2, 3.4))
ax.boxplot([monthly[m] for m in range(1, 13)], tick_labels=config.MONTH_NAMES,
           medianprops=dict(color=ACCENT), widths=0.6)
ax.plot(range(1, 13), config.PRODUCT.monthly_strike_fraction * normals.values, "--",
        color=WARN, lw=1.4, label="Contractual monthly normal (strike)")
ax.set_ylabel("Modelled monthly generation (kWh)")
ax.set_title("Interannual spread of monthly generation, 2005–2024", loc="left")
ax.legend(frameon=False, fontsize=8)
for i, m in enumerate(range(1, 13), start=1):
    ax.annotate(f"{100*monthly[m].std(ddof=1)/monthly[m].mean():.0f}%", (i, monthly[m].max()),
                textcoords="offset points", xytext=(0, 5), ha="center", fontsize=7, color=INK)
fig.tight_layout(); fig.savefig(FIGURES / "fig1_monthly_spread.png"); plt.close(fig)

# 2 -- why an annual index fails (markers, not bars: the axis is truncated)
fig, ax = plt.subplots(figsize=(7.2, 3.0))
ax.vlines(annual_gen.index, 0.95 * config.SYSTEM.aep50_kwh, annual_gen.values,
          color=ACCENT, lw=1.0, alpha=0.45)
ax.plot(annual_gen.index, annual_gen.values, "o", color=ACCENT, ms=5.5, zorder=3,
        label="Modelled annual generation")
ax.axhline(config.SYSTEM.aep50_kwh, color=INK, lw=1.2, label="AEP50 = 4,600 kWh")
ax.axhline(0.95 * config.SYSTEM.aep50_kwh, color=WARN, ls="--", lw=1.5,
           label="Strike at a conventional 5% annual deductible")
ax.set_ylim(4280, 4820)
ax.set_xticks(range(2005, 2025, 2))
ax.set_ylabel("Annual generation (kWh)")
ax.set_title("An annual index never triggers: all 20 years clear a 5% deductible", loc="left")
ax.legend(frameon=False, fontsize=8, loc="lower right", ncol=3,
          bbox_to_anchor=(1.0, -0.02))
fig.tight_layout(); fig.savefig(FIGURES / "fig2_annual_index_fails.png"); plt.close(fig)

# 3 -- back-test: the index, the deductible, and what got paid
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(8.0, 4.0), sharex=True,
                              gridspec_kw={"height_ratios": [1.4, 1]})
bottom = np.zeros(len(monthly))
cmap = plt.get_cmap("YlGnBu")
for m in range(1, 13):
    vals = short_m[m].values
    if vals.sum() > 0:
        ax.bar(monthly.index, vals, bottom=bottom, width=0.7,
               color=cmap(0.22 + 0.062 * m), label=config.MONTH_NAMES[m - 1])
        bottom += vals
ax.axhline(config.PRODUCT.annual_deductible_kwh, color=WARN, ls="--", lw=1.5,
           label=f"Deductible {config.PRODUCT.annual_deductible_kwh:.0f} kWh")
ax.set_ylabel("AGS index (kWh)")
ax.set_ylim(0, bottom.max() * 1.06)
ax.set_title("Back-test: monthly shortfall accumulates to the settlement index",
             loc="left", pad=26)
ax.legend(frameon=False, fontsize=7, ncol=7, loc="upper center",
          bbox_to_anchor=(0.5, 1.19), columnspacing=1.1, handlelength=1.3)

ax2.bar(monthly.index, pay_a.values, width=0.7,
        color=[ACCENT if v > 0 else "#d5dbe1" for v in pay_a.values])
ax2.axhline(burn["burn_cost_inr"], color=WARN, ls="--", lw=1.4,
            label=f"Burn cost ₹{burn['burn_cost_inr']:.0f}")
ax2.set_ylabel("Payout (₹)"); ax2.set_xticks(monthly.index[::2])
ax2.legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(FIGURES / "fig3_backtest.png"); plt.close(fig)

# 4 -- simulated loss distribution
fig, ax = plt.subplots(figsize=(7.2, 3.2))
ax.hist(sim.payouts, bins=70, color=ACCENT, alpha=0.85)
for lbl, v, c in [("Expected loss", sim.expected_loss, WARN),
                  ("P99", np.percentile(sim.payouts, 99), INK),
                  ("Maximum payout", config.PRODUCT.max_payout_inr, "#6b7280")]:
    ax.axvline(v, color=c, ls="--", lw=1.3)
    ax.annotate(f"{lbl}\n₹{v:,.0f}", (v, ax.get_ylim()[1] * 0.75),
                fontsize=7.5, color=c, ha="left", xytext=(4, 0), textcoords="offset points")
ax.set_xlabel("Annual payout (₹)"); ax.set_ylabel("Simulations")
ax.set_title(f"Simulated annual loss distribution ({config.PRICING.n_simulations:,} years)", loc="left")
fig.tight_layout(); fig.savefig(FIGURES / "fig4_loss_distribution.png"); plt.close(fig)

# 5 -- basis risk of a rainfall index
fig, ax = plt.subplots(figsize=(4.6, 3.4))
ax.scatter(mm["precip_a"], mm["gen_a"], s=9, color=ACCENT, alpha=0.55, edgecolor="none")
r2 = float(screening.loc[screening.variable == "Total precipitation", "r_squared"].iloc[0])
ax.set_xlabel("Monthly precipitation anomaly (mm)")
ax.set_ylabel("Monthly generation anomaly (kWh)")
ax.set_title(f"Rainfall explains only {100*r2:.0f}% of\ngeneration variance", loc="left", fontsize=9)
fig.tight_layout(); fig.savefig(FIGURES / "fig5_rainfall_basis_risk.png"); plt.close(fig)

with open(TABLES / "results.json", "w") as fh:
    json.dump(results, fh, indent=2, default=float)

print(f"\nWrote tables to {TABLES} and figures to {FIGURES}")
