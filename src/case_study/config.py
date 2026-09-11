"""Central parameter store for the 380006 rooftop-solar parametric product.

Every number a reviewer might want to challenge lives here, not inline in the
analysis, so the whole study can be re-run under different assumptions.
"""

from dataclasses import dataclass

# ---------------------------------------------------------------- location
PINCODE = "380006"          # Ellisbridge, Ahmedabad, Gujarat
LATITUDE = 22.9997
LONGITUDE = 72.6012
YEAR_START, YEAR_END = 2005, 2024

MASTER_CSV = "raw/climate/ERA5_380006_2005_2024_master.csv"


@dataclass(frozen=True)
class SystemSpec:
    """Rooftop system as specified in the case study brief."""

    capacity_kva: float = 3.0        # nameplate inverter rating
    dc_ac_ratio: float = 1.0         # assumption: 3 kVA inverter <-> 3 kWp array
    performance_ratio: float = 0.80  # client-supplied effective PR
    aep50_kwh: float = 4600.0        # P50 annual energy production
    tariff_inr_per_kwh: float = 5.75
    capex_inr: float = 250_000.0

    @property
    def capacity_kwp(self) -> float:
        return self.capacity_kva * self.dc_ac_ratio

    @property
    def expected_annual_savings_inr(self) -> float:
        return self.aep50_kwh * self.tariff_inr_per_kwh


@dataclass(frozen=True)
class PVModelSpec:
    """Coefficients of the daily energy model (see generation.py)."""

    gamma_per_c: float = -0.0040   # c-Si power temperature coefficient, /degC
    t_ref_c: float = 25.0          # STC cell temperature
    k_cell_rise: float = 3.0       # degC per (kWh/m2/day) irradiance-weighted rise


@dataclass(frozen=True)
class ProductSpec:
    """Terms of the parametric cover.

    Three numbers the customer has to understand: how many kWh of shortfall
    they carry themselves, what each kWh beyond that is worth, and the cap.
    """

    monthly_strike_fraction: float = 1.00   # month counts as short below 100% of normal
    annual_deductible_kwh: float = 100.0    # customer retains the first 100 kWh
    payout_rate_inr_per_kwh: float = 5.75   # = retail tariff, so 1 kWh lost = 1 kWh paid
    max_payout_inr: float = 1_500.0         # exhausted at 361 kWh of shortfall


@dataclass(frozen=True)
class PricingSpec:
    """Loadings applied on top of the modelled expected loss."""

    variance_inflation: float = 1.50   # ERA5-Land smoothing correction
    risk_load_factor: float = 0.20     # x std-dev of the annual payout
    expense_ratio: float = 0.25        # acquisition + admin + data + settlement
    n_simulations: int = 50_000
    random_seed: int = 7


SYSTEM = SystemSpec()
PVMODEL = PVModelSpec()
PRODUCT = ProductSpec()
PRICING = PricingSpec()

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
