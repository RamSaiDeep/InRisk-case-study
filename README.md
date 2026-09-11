# Parametric insurance for rooftop solar generation shortfall — Pincode 380006

Case study submission: a parametric weather product that compensates a residential
3 kVA rooftop solar customer when weather drives generation below expectation.

**Read [`REPORT.md`](REPORT.md) first** — it covers all four tasks.
AI use is declared in [`AI_USAGE.md`](AI_USAGE.md).

## Headline result

| | |
|---|---|
| Index | Annual aggregate generation shortfall (AGS), kWh, from ERA5-Land SSRD + 2 m temperature |
| Trigger | AGS > 100 kWh in the policy year |
| Payout | ₹5.75 per kWh above the deductible |
| Maximum payout | ₹1,500 |
| Historical burn cost (2005–2024) | ₹89, triggering in 8 of 20 years |
| Recommended gross premium | **₹450/year** (1.7% of expected annual savings) |

## Reproducing

```bash
uv sync
.venv/Scripts/python.exe scripts/run_analysis.py
```

Writes every table quoted in the report to `outputs/tables/` and every figure to
`outputs/figures/`. Runs in a few seconds; the Monte Carlo is seeded, so results
are deterministic.

To rebuild the submission PDF (`build/Parametric_Solar_Cover_380006.pdf`):

```bash
.venv/Scripts/python.exe scripts/build_report_pdf.py
```

Renders `REPORT.md` to styled HTML with figures inlined as base64, then prints it
via headless Chrome or Edge — no LaTeX or pandoc needed.

## Layout

```
raw/climate/     ERA5-Land daily extract, 2005-2024 (7,305 days, no gaps)
raw/boundary_file/  Pincode 380006 boundary used to pick the grid cell
notebooks/       Boundary selection and Earth Engine data download
src/case_study/  config, data QC, PV model, policy wording, pricing
scripts/         run_analysis.py — reproduces the whole study
outputs/         Generated tables and figures
```

Every assumption a reviewer might want to change lives in
[`src/case_study/config.py`](src/case_study/config.py); re-run the script to see
its effect propagate through the back-test, the pricing and the figures.
