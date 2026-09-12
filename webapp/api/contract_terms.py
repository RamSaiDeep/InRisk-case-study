"""The non-numeric half of the policy.

`price()` returns numbers; a schedule also needs wording - what the peril is,
what settles a claim, how long settlement takes. None of it is derivable from
the data, so it lives here as named constants rather than being buried in a
string template. Everything with a number in it is filled from the pricing
result at render time, never hard-coded.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContractTerms:
    peril: str = (
        "Low solar irradiance leading to reduced rooftop solar electricity "
        "generation during the policy period."
    )
    reference_area: str = (
        "The ERA5-Land grid cell (~9 km resolution) named in this schedule. "
        "Claims settle on this cell's reading, irrespective of the actual "
        "rooftop generation."
    )
    reference_data_source: str = (
        "ERA5-Land (Copernicus Climate Change Service). This is the "
        "authoritative source for settlement."
    )
    index_definition: str = (
        "Modelled Generation (MG) = annual normalised SSRD index × "
        "performance ratio × installed capacity."
    )
    trigger_wording: str = (
        "The policy triggers when Modelled Generation falls below the strike "
        "named in this schedule."
    )
    exit_wording: str = (
        "The Modelled Generation at or below which the maximum payout is "
        "reached."
    )
    payout_wording: str = (
        "Fixed severity bands, by where Modelled Generation falls relative to "
        "the strike and the exit."
    )
    claim_settlement: str = (
        "Within 30 days of Calculation Agent notification, following final "
        "ERA5-Land data publication."
    )
    claim_documentation: str = (
        "Cover note or policy copy, and proof of insurable interest "
        "(installation invoice or loan document). No proof of physical loss "
        "is required."
    )
    policy_period: str = "1 January – 31 December"

    # Standing caveats. The ones that depend on the run - how many years, which
    # bands went unobserved - are generated from the result instead.
    modelling_assumptions: tuple[str, ...] = (
        "Horizontal irradiance stands in for the tilted plane-of-array "
        "irradiance the panels actually receive. The gap is treated as "
        "constant and folded into the performance ratio.",
        "A kVA rating is treated as kWp, assuming unity power factor.",
        "The system is grid-connected with no battery, so every unit "
        "generated is either used or exported, and every unit is worth the "
        "tariff.",
        "Generation is modelled directly from the weather rather than forced "
        "to match the expected annual generation, so mean modelled "
        "generation will not equal AEP50.",
        "The tariff is fixed for the policy year, and panel degradation is "
        "ignored, since this is a single-year policy.",
        "The ERA5-Land grid cell, about 9 km across, is assumed to represent "
        "the specific rooftop.",
    )
    pricing_limitations: tuple[str, ...] = (
        "ERA5-Land is a reanalysis, not a ground measurement. Any gap in "
        "variability, not just in average level, between the grid cell and "
        "the rooftop is unmeasured.",
        "The index reflects weather only. Soiling, shading, inverter faults "
        "and grid outages reduce real generation without moving the index.",
        "The premium is a burn cost plus a single risk margin. It does not "
        "separately allow for a shift in the weather pattern over time, nor "
        "for any gap between the grid cell and the customer's actual roof.",
        "Where a band sits in the payout structure is a judgement call made "
        "for clarity, not derived from an external standard.",
    )


DEFAULT_TERMS = ContractTerms()
