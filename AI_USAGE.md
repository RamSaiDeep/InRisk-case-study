# Declaration of AI use

The case study asks that AI use be specified and prompts shared. This file is that declaration.

**Tool:** Claude (Anthropic), used through Claude Code in an interactive session against this repository.

## What was done without AI

- Selection of the location and boundary for pincode 380006 (`notebooks/boundary.ipynb`, `raw/boundary_file/`).
- Extraction of the ERA5-Land daily series for 2005–2024 via Google Earth Engine (`notebooks/data_download.ipynb`), including the choice of variables downloaded and the unit conversions to kWh/m², °C and mm.

## What AI was used for

- Exploratory analysis of the downloaded series (variability at daily, monthly, seasonal and annual scales).
- Screening candidate weather variables against de-seasonalised generation anomalies.
- Writing the daily PV generation model and the performance-ratio calibration.
- Structuring the product, back-testing it, and building the Monte Carlo pricing.
- Drafting `REPORT.md` and the code in `src/case_study/` and `scripts/`.

All outputs were reviewed against the generated tables in `outputs/tables/`, and every figure quoted in the report is reproducible by running `scripts/run_analysis.py`.

## Prompts

**Opening prompt (verbatim):**

> @"C:\Users\vrams\Downloads\Case Study - Quant Analyst.pdf"
> I am trying to solve this case study and I need you to come up with a basic solution for this one for me for all the tasks present here.
> I have done some ground work and downloaded the data.

The remainder of the session was a single continuous working thread rather than a series of discrete prompts. The substantive analytical turns were:

1. Read the case study brief and inspect the downloaded ERA5-Land CSVs and repository structure.
2. Run data quality control and quantify the interannual variability of the solar resource at daily, monthly, seasonal and annual resolution.
3. Test whether an annual index can support a product; on finding that annual GHI has a CV of only 1.8%, test monthly-accumulated and consecutive-day-spell alternatives instead.
4. Test the sensitivity of the burn cost to a variance-inflation adjustment for reanalysis smoothing.
5. Calibrate the deductible and maximum payout against the simulated loss distribution.
6. Write the analysis as a reproducible package, then draft the report.
7. Verify every number quoted in the report against the generated CSV tables and correct the discrepancies found.

## Judgement calls made during the session, and by whom

The following were decided in the session and are open to challenge by a reviewer:

| Decision | Basis |
|---|---|
| Monthly-accumulated shortfall rather than an annual index | Empirical — an annual index has zero burn cost at any sensible deductible |
| Rejecting a consecutive-low-day "spell" trigger | Empirical — maximum spell length clusters tightly at 2–6 days in every one of the 20 years, so a spell trigger discriminates poorly between good and bad years |
| Rejecting precipitation as the index variable | Empirical — leaves 53–71% of generation variance unexplained |
| Variance inflation factor of 1.5 | Judgemental, and flagged in the report as the largest open assumption; should be replaced with a measured ERA5-vs-satellite variance ratio before launch |
| γ = −0.40%/°C, cell-temperature rise 3 °C per kWh/m²/day | Standard c-Si values, not fitted to this site |
| Risk load 20% of std dev, expense ratio 25% | Judgemental placeholders for an actual expense study |
