import type { Inputs, PriceResponse, Unit } from "../types";
import { levelName } from "../types";

// The contract in one strip, above the results. Every row is the output of one
// step and jumps straight back to it - the dashboard is the hub, not the end
// of a corridor.

const inr = (value: number) =>
  `₹${value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function InputsSummary({
  inputs,
  unit,
  units,
  years,
  result,
  onEdit,
}: {
  inputs: Inputs;
  unit: Unit;
  units: number;
  years: { start: number; end: number };
  result: PriceResponse | undefined;
  /** Step index to open. */
  onEdit: (step: number) => void;
}) {
  const levels = inputs.payout_sigmas.length;
  const sigma = result?.bands.sigma;

  const rows: { step: number; label: string; value: string; detail?: string }[] = [
    {
      step: 1,
      label: "Years priced",
      value: `${years.start}–${years.end}`,
      detail: `${years.end - years.start + 1} years of ERA5-Land`,
    },
    {
      step: 2,
      label: "Insured",
      value: `${units} × ${unit.capacity_kw} kW`,
      detail: `PR ${unit.pr.toFixed(2)} · ${(unit.aep50 * units).toLocaleString("en-IN")} kWh expected`,
    },
    {
      step: 3,
      label: "Tariff",
      value: `₹${inputs.tariff.toFixed(2)}/kWh`,
      detail: inr(inputs.aep50 * inputs.tariff) + " a normal year",
    },
    {
      step: 4,
      label: "Bands",
      value: `${levels} paying`,
      detail: inputs.boundary_sigmas.map((s) => `${s}σ`).join(" · ") || "single band",
    },
    {
      step: 5,
      label: "Payouts",
      value: result ? inr(result.bands.max_payout) + " max" : "—",
      detail: sigma
        ? inputs.payout_sigmas
            .map((s, i) => `${levelName(i + 1, levels)} ${inr(s * sigma * inputs.tariff)}`)
            .join(" · ")
        : inputs.payout_sigmas.map((s) => `${s}σ`).join(" · "),
    },
    {
      step: 6,
      label: "Loadings",
      value: `${(inputs.expense_pct * 100).toFixed(1)}% + ${(inputs.profit_pct * 100).toFixed(1)}%`,
      detail: `risk coefficient ${inputs.risk_coeff}`,
    },
  ];

  return (
    <section className="summary-strip">
      {rows.map((row) => (
        <button key={row.label} className="summary-cell" onClick={() => onEdit(row.step)}>
          <span className="summary-label">
            {row.label}
            <svg width="11" height="11" viewBox="0 0 12 12" aria-hidden className="summary-pencil">
              <path
                d="M8.2 1.3 10.7 3.8 4.4 10.1 1.3 10.7 1.9 7.6z"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.3"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <span className="summary-value">{row.value}</span>
          {row.detail && <span className="summary-detail">{row.detail}</span>}
        </button>
      ))}
    </section>
  );
}
