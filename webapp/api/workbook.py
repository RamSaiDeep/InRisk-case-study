"""Workbook export.

Rebuilds Solar_Parametric_Workings.xlsx from a live pricing run: the same six
sheets in the same order, driven by the same formulas. The sheets carry
formulas rather than baked values on purpose - the character of the original
workbook is that Inputs drives everything downstream, so someone can open the
export, change a cell and watch it recompute without the app.

The one thing that differs from the original: the band structure is
generalised to N levels, so row positions are computed rather than fixed.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from pricing_engine import PricingInputs, PricingResult
from pricing_engine.types import BacktestRow

HEADING = Font(bold=True, size=12)
SUBHEAD = Font(bold=True, size=10)
NOTE = Font(size=9, italic=True, color="6B6B6B")
HEADER_FILL = PatternFill("solid", fgColor="EFEFEC")
WRAP = Alignment(wrap_text=True, vertical="top")

INR = '"₹"#,##0.00'
KWH = "#,##0.00"


def _level_names(levels: int) -> list[str]:
    if levels == 3:
        return ["Mild", "Moderate", "Severe"]
    return [f"Level {i}" for i in range(1, levels + 1)]


def _write_readme(sheet: Any, meta: dict[str, Any], levels: int) -> None:
    sheet.column_dimensions["B"].width = 104
    rows = [
        ("Solar Generation Shortfall Cover - pricing workbook", HEADING),
        (None, None),
        (
            f"Exported from the pricing workbench for pincode {meta['pincode']} "
            f"on {date.today().isoformat()}.",
            None,
        ),
        (None, None),
        ("What is in here", SUBHEAD),
        (
            "Inputs - the only cells you should need to change. Every other "
            "sheet reads from here.",
            None,
        ),
        (
            "Raw Data - the daily ERA5-Land irradiance readings this pricing "
            "is built on, exactly as fetched.",
            None,
        ),
        (
            "Index & Backtest - each year's readings summed, normalised to a "
            "365-day year, turned into modelled generation and run through "
            "the payout bands.",
            None,
        ),
        (
            "Premium - where the bands sit, how often they would have paid, "
            "and the price that follows.",
            None,
        ),
        ("Assumptions & Limitations - what was assumed, and where this could be wrong.", None),
        (None, None),
        ("Where the data comes from", SUBHEAD),
        (f"Pincode: {meta['pincode']}", None),
        (
            f"ERA5-Land pixel: {meta['pixel_lat']:.6f}°N, {meta['pixel_lon']:.6f}°E",
            None,
        ),
        (f"Years priced: {meta['start_year']}-{meta['end_year']}", None),
        (
            "Variable: Surface Solar Radiation Downwards (SSRD), daily sums, "
            "converted from J/m² to kWh/m².",
            None,
        ),
        (None, None),
        (
            f"This contract has {levels} paying "
            f"{'level' if levels == 1 else 'levels'}. The formulas below are "
            "written for that structure.",
            NOTE,
        ),
    ]
    for index, (text, font) in enumerate(rows, start=2):
        if text is None:
            continue
        cell = sheet.cell(row=index, column=2, value=text)
        if font:
            cell.font = font
        cell.alignment = WRAP


def _write_inputs(sheet: Any, inputs: PricingInputs, levels: int) -> dict[str, int]:
    """Returns the row each input landed on, so other sheets can reference it."""
    sheet.column_dimensions["B"].width = 40
    sheet.column_dimensions["C"].width = 12
    sheet.column_dimensions["D"].width = 14
    sheet.column_dimensions["E"].width = 70

    sheet["B2"] = "Inputs"
    sheet["B2"].font = HEADING
    sheet["B3"] = (
        "These are the only cells you should need to change. Every other sheet "
        "reads from here."
    )
    sheet["B3"].font = NOTE

    for column, title in zip("BCDE", ("Parameter", "Value", "Unit", "Note")):
        cell = sheet[f"{column}5"]
        cell.value = title
        cell.font = SUBHEAD
        cell.fill = HEADER_FILL

    at: dict[str, int] = {}
    row = 7
    sheet.cell(row=row, column=2, value="The solar system and the customer's contract").font = SUBHEAD
    row += 1
    for key, label, value, unit, note in [
        ("capacity_kw", "Installed capacity", inputs.capacity_kw, "kW", "A kVA rating is treated as kWp, assuming unity power factor."),
        ("pr", "Performance ratio", inputs.pr, "—", "The share of sunlight that actually becomes usable electricity, after all real-world losses."),
        ("aep50", "Expected annual generation (AEP50)", inputs.aep50, "kWh/yr", "What the customer was promised in a normal year. Also used as the trigger."),
        ("tariff", "Electricity tariff", inputs.tariff, "₹/kWh", "Used to turn a shortfall in kWh into a rupee payout."),
    ]:
        sheet.cell(row=row, column=2, value=label)
        sheet.cell(row=row, column=3, value=value)
        sheet.cell(row=row, column=4, value=unit)
        sheet.cell(row=row, column=5, value=note).alignment = WRAP
        at[key] = row
        row += 1

    row += 1
    sheet.cell(row=row, column=2, value="How the payout bands are set").font = SUBHEAD
    row += 1
    sheet.cell(row=row, column=2, value="Trigger (fixed at expected generation)")
    sheet.cell(row=row, column=3, value=f"=C{at['aep50']}")
    sheet.cell(row=row, column=5, value="The policy only pays when the year falls short of what was promised.").alignment = WRAP
    at["trigger"] = row
    row += 1

    names = _level_names(levels)
    for index, sigma in enumerate(inputs.boundary_sigmas):
        sheet.cell(row=row, column=2, value=f"{names[index]} / {names[index + 1]} boundary")
        sheet.cell(row=row, column=3, value=sigma)
        sheet.cell(row=row, column=4, value="× std dev")
        sheet.cell(row=row, column=5, value=f"How far below the trigger the {names[index]} band ends.").alignment = WRAP
        at[f"boundary_{index}"] = row
        row += 1
    for index, sigma in enumerate(inputs.payout_sigmas):
        sheet.cell(row=row, column=2, value=f"{names[index]} payout point")
        sheet.cell(row=row, column=3, value=sigma)
        sheet.cell(row=row, column=4, value="× std dev")
        sheet.cell(row=row, column=5, value=f"Where in the {names[index]} band the fixed payout is set.").alignment = WRAP
        at[f"payout_{index}"] = row
        row += 1

    row += 1
    sheet.cell(row=row, column=2, value="Pricing").font = SUBHEAD
    row += 1
    for key, label, value, unit, note in [
        ("risk_coeff", "Risk margin", inputs.risk_coeff, "× std dev of payout", "A cushion held against how much the payout swings from year to year, not just its average."),
        ("expense_pct", "Running costs", inputs.expense_pct, "% of price", "Administration, distribution, and claims handling."),
        ("profit_pct", "Profit margin", inputs.profit_pct, "% of price", "What the insurer keeps."),
    ]:
        sheet.cell(row=row, column=2, value=label)
        sheet.cell(row=row, column=3, value=value)
        sheet.cell(row=row, column=4, value=unit)
        sheet.cell(row=row, column=5, value=note).alignment = WRAP
        at[key] = row
        row += 1

    row += 1
    sheet.cell(row=row, column=2, value="Worked out from the above").font = SUBHEAD
    row += 1
    sheet.cell(row=row, column=2, value="Expected annual savings")
    sheet.cell(row=row, column=3, value=f"=C{at['aep50']}*C{at['tariff']}").number_format = INR
    at["expected_savings"] = row
    return at


def _write_raw_data(sheet: Any, frame: pd.DataFrame) -> int:
    """Every daily reading the pricing is built on. Returns the last row."""
    sheet.column_dimensions["A"].width = 12
    for column, title in enumerate(
        ["date", "latitude", "longitude", "ssrd_j_m2", "ssrd_kwh_m2"], start=1
    ):
        cell = sheet.cell(row=1, column=column, value=title)
        cell.font = SUBHEAD
        cell.fill = HEADER_FILL
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    for offset, record in enumerate(frame.itertuples(index=False), start=2):
        sheet.cell(row=offset, column=1, value=record.date.date()).number_format = "yyyy-mm-dd"
        sheet.cell(row=offset, column=2, value=float(record.latitude))
        sheet.cell(row=offset, column=3, value=float(record.longitude))
        sheet.cell(row=offset, column=4, value=float(record.ssrd_j_m2))
        sheet.cell(row=offset, column=5, value=float(record.ssrd_kwh_m2))
    sheet.freeze_panes = "A2"
    return len(frame) + 1


def _payout_formula(row: int, levels: int, premium_rows: dict[str, int], trigger_ref: str) -> str:
    """The band test, most severe first, as nested IFs.

    Deliberately not IFS: that is a "future function" in the xlsx format and
    has to be stored as _xlfn.IFS to be recognised. Written plainly it reads
    as #NAME? outside Excel - which is what the reference workbook does in
    LibreOffice. Nested IF needs no prefix and evaluates everywhere.

    The comparisons are strict `<`, matching the engine: a year exactly on a
    boundary takes the milder level.
    """
    # Built inside-out, starting from the most severe payout: each step wraps
    # the chain in "is it milder than this boundary?".
    formula = f"Premium!$C${premium_rows[f'payout_{levels - 1}']}"
    for level in range(levels - 1, 0, -1):
        boundary = f"Premium!$C${premium_rows[f'boundary_{level - 1}']}"
        milder = f"Premium!$C${premium_rows[f'payout_{level - 1}']}"
        formula = f"IF(E{row}<{boundary},{formula},{milder})"
    # Outermost: a year at or above the trigger pays nothing at all.
    return f"=IF(E{row}<{trigger_ref},{formula},0)"


def _write_backtest(
    sheet: Any,
    backtest: tuple[BacktestRow, ...],
    last_raw_row: int,
    input_rows: dict[str, int],
    premium_rows: dict[str, int],
    levels: int,
) -> dict[str, int]:
    sheet.column_dimensions["A"].width = 8
    sheet["A2"] = "From Daily Weather to a Yearly Payout"
    sheet["A2"].font = HEADING
    sheet["A3"] = (
        "Each year's daily sunlight readings are added up, turned into a "
        "modelled amount of electricity, and checked against the payout bands."
    )
    sheet["A3"].font = NOTE

    headers = [
        "Year",
        "Days",
        "Sunlight, summed (kWh/m²)",
        "Yearly index (kWh/m²)",
        "Modelled generation (kWh)",
        "Payout (₹)",
    ]
    for column, title in enumerate(headers, start=1):
        cell = sheet.cell(row=5, column=column, value=title)
        cell.font = SUBHEAD
        cell.fill = HEADER_FILL
        sheet.column_dimensions[get_column_letter(column)].width = max(12, len(title) * 0.9)

    raw = f"'Raw Data'!$A$2:$A${last_raw_row}"
    values = f"'Raw Data'!$E$2:$E${last_raw_row}"
    trigger_ref = f"Inputs!$C${input_rows['trigger']}"

    first = 6
    for offset, year_row in enumerate(backtest):
        row = first + offset
        sheet.cell(row=row, column=1, value=year_row.year)
        sheet.cell(
            row=row,
            column=2,
            value=f'=COUNTIFS({raw}, ">="&DATE(A{row},1,1), {raw}, "<="&DATE(A{row},12,31))',
        )
        sheet.cell(
            row=row,
            column=3,
            value=f'=SUMIFS({values}, {raw}, ">="&DATE(A{row},1,1), {raw}, "<="&DATE(A{row},12,31))',
        ).number_format = KWH
        sheet.cell(row=row, column=4, value=f"=C{row}/B{row}*365").number_format = KWH
        sheet.cell(
            row=row,
            column=5,
            value=f"=D{row}*Inputs!$C${input_rows['pr']}*Inputs!$C${input_rows['capacity_kw']}",
        ).number_format = KWH
        sheet.cell(
            row=row, column=6, value=_payout_formula(row, levels, premium_rows, trigger_ref)
        ).number_format = INR
    last = first + len(backtest) - 1

    summary = last + 2
    sheet.cell(row=summary, column=1, value="A few numbers used elsewhere in this workbook").font = SUBHEAD
    rows = {"first": first, "last": last}
    for offset, (label, formula, fmt, note) in enumerate(
        [
            ('Average yearly index (a "normal" year)', f"=AVERAGE(D{first}:D{last})", KWH, None),
            ("Standard deviation of the index", f"=STDEV(D{first}:D{last})", KWH, None),
            (
                "Average modelled generation",
                f"=AVERAGE(E{first}:E{last})",
                KWH,
                "Modelled directly from the weather rather than forced to match AEP50, so this will not equal the expected figure.",
            ),
            (
                "Standard deviation of modelled generation",
                f"=STDEV(E{first}:E{last})",
                KWH,
                "This is the number the payout bands are actually set from.",
            ),
        ],
        start=1,
    ):
        row = summary + offset
        sheet.cell(row=row, column=1, value=label)
        sheet.cell(row=row, column=3, value=formula).number_format = fmt
        if note:
            sheet.cell(row=row, column=4, value=note).font = NOTE
        rows[["index_mean", "index_stdev", "generation_mean", "generation_stdev"][offset - 1]] = row
    return rows


def _premium_layout(levels: int) -> dict[str, int]:
    """Row positions on the Premium sheet, which every other sheet references."""
    layout = {"sigma": 7}
    row = 8
    for index in range(levels - 1):
        layout[f"boundary_{index}"] = row
        row += 1
    for index in range(levels):
        layout[f"payout_{index}"] = row
        row += 1
    row += 2
    layout["years_triggering"] = row
    layout["average_paying"] = row + 1
    layout["burn_cost"] = row + 2
    row += 5
    layout["burn_cost_restated"] = row
    layout["payout_stdev"] = row + 1
    layout["risk_margin"] = row + 2
    layout["technical"] = row + 3
    layout["gross"] = row + 4
    return layout


def _write_premium(
    sheet: Any,
    layout: dict[str, int],
    input_rows: dict[str, int],
    backtest_rows: dict[str, int],
    levels: int,
) -> None:
    sheet.column_dimensions["B"].width = 56
    sheet.column_dimensions["C"].width = 14
    sheet.column_dimensions["D"].width = 74

    sheet["B2"] = "Setting the Payout Bands and the Price"
    sheet["B2"].font = HEADING
    sheet["B4"] = "Payout bands"
    sheet["B4"].font = SUBHEAD
    sheet["B5"] = (
        "The bands are set from how much the modelled generation typically "
        "varies year to year, not from a round percentage."
    )
    sheet["B5"].font = NOTE

    names = _level_names(levels)
    payout_range = f"'Index & Backtest'!F{backtest_rows['first']}:F{backtest_rows['last']}"

    sheet.cell(row=layout["sigma"], column=2, value="How much generation typically varies (std dev)")
    sheet.cell(
        row=layout["sigma"],
        column=3,
        value=f"='Index & Backtest'!C{backtest_rows['generation_stdev']}",
    ).number_format = KWH

    trigger = f"Inputs!$C${input_rows['trigger']}"
    for index in range(levels - 1):
        row = layout[f"boundary_{index}"]
        sheet.cell(row=row, column=2, value=f"{names[index]} / {names[index + 1]} boundary")
        sheet.cell(
            row=row,
            column=3,
            value=f"={trigger}-Inputs!$C${input_rows[f'boundary_{index}']}*$C${layout['sigma']}",
        ).number_format = KWH
    for index in range(levels):
        row = layout[f"payout_{index}"]
        sheet.cell(row=row, column=2, value=f"{names[index]} payout")
        sheet.cell(
            row=row,
            column=3,
            value=f"=Inputs!$C${input_rows[f'payout_{index}']}*$C${layout['sigma']}*Inputs!$C${input_rows['tariff']}",
        ).number_format = INR
    sheet.cell(
        row=layout[f"payout_{levels - 1}"],
        column=4,
        value="The most the policy can ever pay in one year.",
    ).font = NOTE

    head = layout["years_triggering"] - 2
    sheet.cell(row=head, column=2, value="How often it pays, and how much").font = SUBHEAD
    sheet.cell(row=layout["years_triggering"], column=2, value="Years that would have triggered a payout")
    sheet.cell(row=layout["years_triggering"], column=3, value=f'=COUNTIF({payout_range},">0")')
    sheet.cell(row=layout["average_paying"], column=2, value="Average payout in a year that pays")
    sheet.cell(
        row=layout["average_paying"], column=3, value=f'=AVERAGEIF({payout_range},">0")'
    ).number_format = INR
    sheet.cell(
        row=layout["burn_cost"],
        column=2,
        value='Average payout across all years (the "burn cost")',
    )
    sheet.cell(
        row=layout["burn_cost"], column=3, value=f"=AVERAGE({payout_range})"
    ).number_format = INR
    sheet.cell(
        row=layout["burn_cost"],
        column=4,
        value="The honest, no-margin cost of the risk. Everything below adds a margin on top of it.",
    ).font = NOTE

    head = layout["burn_cost_restated"] - 1
    sheet.cell(row=head, column=2, value="From cost to price").font = SUBHEAD
    sheet.cell(row=layout["burn_cost_restated"], column=2, value="Burn cost")
    sheet.cell(
        row=layout["burn_cost_restated"], column=3, value=f"=C{layout['burn_cost']}"
    ).number_format = INR
    sheet.cell(
        row=layout["payout_stdev"], column=2, value="How much the payout swings year to year (std dev)"
    )
    sheet.cell(
        row=layout["payout_stdev"], column=3, value=f"=STDEV({payout_range})"
    ).number_format = INR
    sheet.cell(row=layout["risk_margin"], column=2, value="Risk margin")
    sheet.cell(
        row=layout["risk_margin"],
        column=3,
        value=f"=Inputs!$C${input_rows['risk_coeff']}*C{layout['payout_stdev']}",
    ).number_format = INR
    sheet.cell(row=layout["technical"], column=2, value="Cost of the risk, including that cushion")
    sheet.cell(
        row=layout["technical"],
        column=3,
        value=f"=C{layout['burn_cost_restated']}+C{layout['risk_margin']}",
    ).number_format = INR
    sheet.cell(row=layout["gross"], column=2, value="Price charged to the customer")
    gross = sheet.cell(
        row=layout["gross"],
        column=3,
        value=(
            f"=C{layout['technical']}/(1-Inputs!$C${input_rows['expense_pct']}"
            f"-Inputs!$C${input_rows['profit_pct']})"
        ),
    )
    gross.number_format = INR
    gross.font = Font(bold=True)
    sheet.cell(
        row=layout["gross"],
        column=4,
        value=(
            "Running costs and profit are both a share of this final price, not "
            "of the cost above, so this line divides rather than simply adding "
            "them on."
        ),
    ).font = NOTE


def _write_assumptions(sheet: Any, result: PricingResult, terms: Any) -> None:
    sheet.column_dimensions["B"].width = 108
    sheet["A2"] = "What We Assumed, and Where This Could Be Wrong"
    sheet["A2"].font = HEADING

    unobserved = [
        index + 1
        for index in range(len(result.bands.payouts))
        if result.summary.level_year_counts.get(index + 1, 0) == 0
    ]
    names = _level_names(len(result.bands.payouts))
    generated = [
        f"Only {result.summary.years} years of history are available - enough to "
        "estimate a typical year reasonably well, but not enough to say much "
        "about a truly extreme one.",
        "Because the payout is a fixed amount per band rather than a smoothly "
        "scaling one, two very similar weather years can receive noticeably "
        "different payouts if they land on opposite sides of a boundary"
        + (
            f" - the closest call here is {result.summary.closest_call_year}, "
            f"{result.summary.closest_call_distance:.1f} kWh from an edge."
            if result.summary.closest_call_year is not None
            else "."
        ),
        f"Mean modelled generation is {result.summary.mean_generation:,.0f} kWh, "
        f"{result.summary.mean_generation_vs_trigger:+.2%} against the "
        f"{result.bands.trigger:,.0f} kWh trigger "
        f"({result.summary.mean_generation_sigmas_from_trigger:+.2f} standard "
        "deviations). This is noted, not corrected.",
    ]
    if unobserved:
        listed = ", ".join(names[level - 1] for level in unobserved)
        generated.append(
            f"No year on record reached the {listed} "
            f"{'band' if len(unobserved) == 1 else 'bands'}. That payout is a "
            "reasonable estimate, not something observed."
        )

    row = 4
    for title, items in [
        ("About this pricing run", generated),
        ("About the modelling", list(terms.modelling_assumptions)),
        ("About the price", list(terms.pricing_limitations)),
    ]:
        sheet.cell(row=row, column=1, value=title).font = SUBHEAD
        row += 1
        for item in items:
            cell = sheet.cell(row=row, column=2, value=f"•  {item}")
            cell.alignment = WRAP
            sheet.row_dimensions[row].height = 30
            row += 1
        row += 1


def build_workbook(
    result: PricingResult,
    inputs: PricingInputs,
    frame: pd.DataFrame,
    meta: dict[str, Any],
    terms: Any,
) -> BytesIO:
    """The six sheets, in the original's order."""
    levels = len(result.bands.payouts)
    workbook = Workbook()

    readme = workbook.active
    readme.title = "README"
    inputs_sheet = workbook.create_sheet("Inputs")
    raw_sheet = workbook.create_sheet("Raw Data")
    backtest_sheet = workbook.create_sheet("Index & Backtest")
    premium_sheet = workbook.create_sheet("Premium")
    assumptions_sheet = workbook.create_sheet("Assumptions & Limitations")

    _write_readme(readme, meta, levels)
    input_rows = _write_inputs(inputs_sheet, inputs, levels)
    last_raw_row = _write_raw_data(raw_sheet, frame)
    premium_layout = _premium_layout(levels)
    backtest_rows = _write_backtest(
        backtest_sheet, result.backtest, last_raw_row, input_rows, premium_layout, levels
    )
    _write_premium(premium_sheet, premium_layout, input_rows, backtest_rows, levels)
    _write_assumptions(assumptions_sheet, result, terms)

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream
