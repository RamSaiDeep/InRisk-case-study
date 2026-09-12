"""Report export.

Markdown -> styled HTML -> headless Chrome --print-to-pdf. Chrome is used
because it is already on the machine, renders the rupee glyph correctly, and
gives real control over page breaks; there is no LaTeX or pandoc dependency.
This is the same pipeline that produced the submitted report.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import markdown

from data_layer.config import Misconfigured
from pricing_engine import PricingInputs, PricingResult

BROWSERS = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/chromium"),
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
]

CSS = """
@page { size: A4; margin: 16mm 15mm; }
* { box-sizing: border-box; }
body {
  font-family: "Segoe UI", "Nirmala UI", system-ui, sans-serif;
  font-size: 9.8pt; line-height: 1.45; color: #1f2933; margin: 0;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
h1 { font-size: 16pt; margin: 0 0 2pt; }
h2 { font-size: 11.5pt; margin: 16pt 0 4pt; padding-bottom: 2pt;
     border-bottom: 1px solid #d8dde3; }
h3 { font-size: 10pt; margin: 10pt 0 3pt; }
p { margin: 0 0 6pt; }
.lede { color: #52606d; margin-bottom: 10pt; }
table { width: 100%; border-collapse: collapse; margin: 4pt 0 10pt;
        font-size: 9pt; page-break-inside: avoid; }
th, td { border-bottom: 1px solid #e4e7eb; padding: 3.4pt 6pt; text-align: left;
         vertical-align: top; }
th { background: #f5f7fa; font-weight: 600; }
td:nth-child(n+2), th:nth-child(n+2) { text-align: right; }
table.terms td:nth-child(2), table.terms th:nth-child(2) { text-align: left; }
ol, ul { margin: 0 0 8pt; padding-left: 15pt; }
li { margin-bottom: 3pt; }
.headline { display: flex; gap: 18pt; margin: 8pt 0 12pt; }
.headline > div { flex: 1; border: 1px solid #e4e7eb; border-radius: 4pt;
                padding: 6pt 8pt; }
.headline .k { color: #52606d; font-size: 8pt; text-transform: uppercase;
               letter-spacing: 0.04em; }
.headline .v { font-size: 15pt; font-weight: 600; }
.footnote { color: #7b8794; font-size: 8pt; margin-top: 14pt; }
"""


def _find_browser() -> Path:
    # A container says where its browser is; a workstation is guessed at.
    configured = os.environ.get("CHROME_PATH")
    if configured and Path(configured).exists():
        return Path(configured)
    for candidate in BROWSERS:
        if candidate.exists():
            return candidate
    raise Misconfigured(
        "no Chrome or Edge on this machine - the report export renders PDF "
        "through headless Chrome"
    )


def _level_names(levels: int) -> list[str]:
    if levels == 3:
        return ["Mild", "Moderate", "Severe"]
    return [f"Level {i}" for i in range(1, levels + 1)]


def _table(headers: list[str], rows: list[list[str]]) -> str:
    """One markdown table as a single block.

    Rows must reach the parser together; split across blank lines they read as
    paragraphs of pipe characters.
    """
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines.extend("| " + " | ".join(cells) + " |" for cells in rows)
    return "\n".join(lines)


def _inr(value: float) -> str:
    return f"₹{value:,.2f}"


def build_markdown(
    result: PricingResult,
    inputs: PricingInputs,
    meta: dict[str, Any],
    terms: Any,
) -> str:
    bands = result.bands
    premium = result.premium
    summary = result.summary
    levels = len(bands.payouts)
    names = _level_names(levels)
    where = meta.get("attributes", {})
    place = ", ".join(
        part for part in [where.get("Office_Name"), where.get("Division"), where.get("Circle")] if part
    )

    lines: list[str] = []
    lines.append(f"# Solar Generation Shortfall Cover — Pincode {meta['pincode']}")
    lines.append(
        f'<p class="lede">A parametric cover against a below-normal year of '
        f"sunshine, priced on {summary.years} years of ERA5-Land irradiance "
        f"({meta['start_year']}–{meta['end_year']}) at "
        f"{meta['pixel_lat']:.4f}°N, {meta['pixel_lon']:.4f}°E"
        f"{f' · {place}' if place else ''}.</p>"
    )

    lines.append(
        '<div class="headline">'
        f'<div><div class="k">Premium</div><div class="v">{_inr(premium.gross_premium)}</div>'
        "per policy per year</div>"
        f'<div><div class="k">Sum insured</div><div class="v">{_inr(bands.max_payout)}</div>'
        "maximum payout</div>"
        f'<div><div class="k">Triggers</div><div class="v">{summary.years_triggering} of {summary.years}</div>'
        f"{summary.trigger_frequency:.0%} of years on record</div>"
        "</div>"
    )

    lines.append("## The policy")
    schedule = ['<table class="terms">', "<tr><th>Item</th><th>Description</th></tr>"]
    for label, value in [
        ("Peril", terms.peril),
        ("Reference area", terms.reference_area),
        ("Reference data source", terms.reference_data_source),
        ("Index", terms.index_definition),
        ("Trigger / strike", f"{terms.trigger_wording} The strike is {bands.trigger:,.0f} kWh."),
        ("Exit", f"{terms.exit_wording} Here, {bands.exit_level:,.2f} kWh."),
        ("Payout structure", terms.payout_wording),
        ("Policy period", terms.policy_period),
        ("Claim settlement", terms.claim_settlement),
        ("Claim documentation", terms.claim_documentation),
    ]:
        schedule.append(f"<tr><td>{label}</td><td>{value}</td></tr>")
    schedule.append("</table>")
    lines.append("\n".join(schedule))

    lines.append("## The insured installation")
    lines.append(
        _table(
            ["Item", "Value"],
            [
                ["Installed capacity", f"{inputs.capacity_kw:g} kW"],
                ["Performance ratio", f"{inputs.pr:.2f}"],
                ["Expected annual generation (AEP50)", f"{inputs.aep50:,.0f} kWh"],
                ["Electricity tariff", f"₹{inputs.tariff:,.2f}/kWh"],
                ["Expected annual savings", _inr(inputs.aep50 * inputs.tariff)],
            ],
        )
    )

    lines.append("## Payout bands")
    lines.append(
        f"σ = {bands.sigma:,.2f} kWh, the standard deviation of modelled "
        f"generation across the {summary.years} years priced. Every boundary "
        "and every payout below is a multiple of it."
    )
    band_rows = [["None", f"≥ {bands.trigger:,.2f} kWh", "—"]]
    for index, name in enumerate(names):
        upper = bands.trigger if index == 0 else bands.boundaries[index - 1]
        if index < len(bands.boundaries):
            window = f"{bands.boundaries[index]:,.2f} ≤ MG < {upper:,.2f} kWh"
        else:
            window = f"MG < {upper:,.2f} kWh"
        band_rows.append([name, window, _inr(bands.payouts[index])])
    lines.append(_table(["Band", "Modelled generation", "Payout"], band_rows))

    lines.append("## Backtest")
    paying = [row for row in result.backtest if row.payout > 0]
    if paying:
        listed = ", ".join(
            f"{row.year} ({_level_names(levels)[row.level - 1]})" for row in paying
        )
        lines.append(
            f"Running each year through the same contract produces "
            f"{len(paying)} payouts: {listed}. The worst year on record, "
            f"{summary.worst_year}, would have paid "
            f"{_inr(summary.worst_year_payout or 0)}."
        )
    else:
        lines.append("No year in the period priced would have triggered a payout.")
    lines.append(
        _table(
            ["Year", "Days", "Index kWh/m²", "Generation kWh", "Band", "Payout", "From edge"],
            [
                [
                    str(row.year),
                    str(row.days),
                    f"{row.index:,.2f}",
                    f"{row.generation:,.2f}",
                    "None" if row.level == 0 else names[row.level - 1],
                    "—" if row.payout == 0 else _inr(row.payout),
                    f"{row.distance_to_edge:,.2f}",
                ]
                for row in result.backtest
            ],
        )
    )

    lines.append("## Pricing")
    lines.append(
        _table(
            ["Build-up", "Per policy per year"],
            [
                ["Pure premium (burn cost)", _inr(premium.burn_cost)],
                [
                    f"Risk load ({inputs.risk_coeff:g} × standard deviation of payout)",
                    _inr(premium.risk_margin),
                ],
                ["Technical premium", _inr(premium.technical_premium)],
                [
                    f"Gross premium = technical ÷ (1 − {inputs.expense_pct:.1%} "
                    f"expenses − {inputs.profit_pct:.1%} profit)",
                    f"**{_inr(premium.gross_premium)}**",
                ],
            ],
        )
    )
    if summary.average_payout_when_paying is not None:
        lines.append(
            f"Years triggering: {summary.years_triggering} of {summary.years} "
            f"({summary.trigger_frequency:.0%}). Average severity when it pays: "
            f"{_inr(summary.average_payout_when_paying)}."
        )

    lines.append("## Assumptions and limitations")
    lines.append("### About this pricing run")
    lines.append(
        f"1. Mean modelled generation is {summary.mean_generation:,.0f} kWh, "
        f"{summary.mean_generation_vs_trigger:+.2%} against the "
        f"{bands.trigger:,.0f} kWh trigger "
        f"({summary.mean_generation_sigmas_from_trigger:+.2f}σ). Generation is "
        "modelled from the weather rather than anchored to AEP50, so the two "
        "are not expected to match. This is noted, not corrected."
    )
    unobserved = [
        names[index] for index in range(levels) if summary.level_year_counts.get(index + 1, 0) == 0
    ]
    if unobserved:
        lines.append(
            f"2. No year on record reached the {', '.join(unobserved)} "
            f"{'band' if len(unobserved) == 1 else 'bands'}, so that payout is "
            "a statistical extrapolation, not an observed outcome."
        )
    if summary.closest_call_year is not None:
        lines.append(
            f"{len(unobserved) + 2}. Payouts are fixed per band, so a year near "
            f"a boundary can be paid very differently from a near-identical "
            f"one on the other side. The closest call here is "
            f"{summary.closest_call_year}, "
            f"{summary.closest_call_distance:,.2f} kWh from an edge."
        )
    lines.append("### About the modelling")
    for item in terms.modelling_assumptions:
        lines.append(f"- {item}")
    lines.append("### About the price")
    for item in terms.pricing_limitations:
        lines.append(f"- {item}")

    lines.append(
        '<p class="footnote">Generated by the parametric pricing workbench from '
        f"ERA5-Land daily SSRD at {meta['pixel_lat']:.6f}°N, "
        f"{meta['pixel_lon']:.6f}°E. Every figure recomputes from the inputs "
        "above; none is hard-coded.</p>"
    )
    return "\n\n".join(lines)


def build_pdf(
    result: PricingResult, inputs: PricingInputs, meta: dict[str, Any], terms: Any
) -> bytes:
    browser = _find_browser()
    body = markdown.markdown(
        build_markdown(result, inputs, meta, terms), extensions=["tables", "md_in_html"]
    )
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{CSS}</style></head><body>{body}</body></html>"
    )
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "report.html"
        target = Path(directory) / "report.pdf"
        source.write_text(html, encoding="utf-8")
        completed = subprocess.run(
            [
                str(browser),
                "--headless",
                "--disable-gpu",
                # Containers run as root, and Chrome refuses to start as root
                # with its sandbox on. The sandbox buys nothing here: the only
                # page it ever opens is one this process just wrote to a temp
                # directory.
                "--no-sandbox",
                # /dev/shm is 64 MB by default in most containers, which
                # Chrome exhausts and then crashes.
                "--disable-dev-shm-usage",
                "--no-pdf-header-footer",
                f"--print-to-pdf={target}",
                source.as_uri(),
            ],
            capture_output=True,
            timeout=120,
        )
        if not target.exists():
            raise Misconfigured(
                f"headless browser produced no PDF: "
                f"{completed.stderr.decode(errors='replace')[:300]}"
            )
        return target.read_bytes()
