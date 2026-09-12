"""The input contract the whole engine runs on."""

from __future__ import annotations

from dataclasses import dataclass, field


class InvalidInputs(ValueError):
    """Raised for a parameter set the engine cannot price.

    The API layer maps this to 422; nothing here knows about HTTP.
    """


@dataclass(frozen=True, slots=True)
class PricingInputs:
    capacity_kw: float
    pr: float
    aep50: float  # kWh/yr; taken as given, and used directly as the trigger
    tariff: float  # currency per kWh
    boundary_sigmas: tuple[float, ...]  # length N-1, strictly increasing
    payout_sigmas: tuple[float, ...]  # length N, one per paying level
    risk_coeff: float
    expense_pct: float
    profit_pct: float

    def __post_init__(self) -> None:
        if self.capacity_kw <= 0:
            raise InvalidInputs("capacity_kw must be positive")
        if not 0 < self.pr <= 1:
            raise InvalidInputs("pr must be in (0, 1]")
        if self.aep50 <= 0:
            raise InvalidInputs("aep50 must be positive")
        if self.tariff <= 0:
            raise InvalidInputs("tariff must be positive")
        if self.risk_coeff < 0:
            raise InvalidInputs("risk_coeff cannot be negative")
        if not self.payout_sigmas:
            raise InvalidInputs("at least one payout level is required")
        if len(self.payout_sigmas) != len(self.boundary_sigmas) + 1:
            raise InvalidInputs(
                f"payout_sigmas must have exactly one more entry than "
                f"boundary_sigmas (got {len(self.payout_sigmas)} payouts "
                f"for {len(self.boundary_sigmas)} boundaries)"
            )
        # An out-of-order list would silently create overlapping or inverted
        # bands, so it is rejected rather than sorted.
        for lower, upper in zip(self.boundary_sigmas, self.boundary_sigmas[1:]):
            if upper <= lower:
                raise InvalidInputs(
                    f"boundary_sigmas must be strictly increasing "
                    f"(got {self.boundary_sigmas})"
                )
        if any(s <= 0 for s in self.boundary_sigmas):
            raise InvalidInputs("boundary_sigmas must be positive")
        # Deliberately no ordering constraint on payout_sigmas: a
        # non-increasing payout curve is a legitimate choice.
        if self.expense_pct < 0 or self.profit_pct < 0:
            raise InvalidInputs("expense_pct and profit_pct cannot be negative")
        if self.expense_pct + self.profit_pct >= 1:
            raise InvalidInputs(
                f"expense_pct + profit_pct must be below 1 "
                f"(got {self.expense_pct + self.profit_pct:.4f})"
            )

    @property
    def levels(self) -> int:
        """N: the number of paying levels."""
        return len(self.payout_sigmas)


# The parameters from the submitted case study, used as the Workspace's
# opening state and as the engine's regression fixture.
REFERENCE_INPUTS = PricingInputs(
    capacity_kw=3.0,
    pr=0.80,
    aep50=4600.0,
    tariff=5.75,
    boundary_sigmas=(0.5, 1.0),
    payout_sigmas=(0.25, 0.75, 1.25),
    risk_coeff=0.20,
    expense_pct=0.20,
    profit_pct=0.075,
)
