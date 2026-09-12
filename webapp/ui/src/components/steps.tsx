import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Inputs, PriceResponse, Unit } from "../types";
import { levelName } from "../types";
import { NumberField } from "./fields";
import { BacktestChart } from "./BacktestChart";

const inr = (value: number) =>
  `₹${value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const kwh = (value: number) =>
  `${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })} kWh`;

// --- 1. the data itself ---------------------------------------------------

export function DataStep({ pincode }: { pincode: string }) {
  const [offset, setOffset] = useState(0);
  const page = 12;
  const series = useQuery({
    queryKey: ["series", pincode, offset],
    queryFn: () => api.series(pincode, offset, page),
  });

  if (!series.data) return <p className="muted">Loading the readings…</p>;
  const { rows, first_day, last_day, years, daily } = series.data;

  return (
    <>
      <p className="step-lede">
        {rows.toLocaleString("en-IN")} daily readings of surface solar radiation,{" "}
        {first_day} to {last_day}. This is the whole basis of the pricing —
        nothing else is used.
      </p>

      <h3>By year</h3>
      <div className="table-wrap scroll-190">
        <table>
          <thead>
            <tr>
              <th>Year</th>
              <th>Days</th>
              <th>Sunlight, summed (kWh/m²)</th>
            </tr>
          </thead>
          <tbody>
            {years.map((year) => (
              <tr key={year.year}>
                <td>{year.year}</td>
                <td>{year.days}</td>
                <td>{year.sunlight_sum.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="spaced">Daily readings</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>SSRD (J/m²)</th>
              <th>SSRD (kWh/m²)</th>
            </tr>
          </thead>
          <tbody>
            {daily.map((row) => (
              <tr key={row.date}>
                <td>{row.date}</td>
                <td>{row.ssrd_j_m2.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</td>
                <td>{row.ssrd_kwh_m2.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pager">
        <button onClick={() => setOffset(Math.max(0, offset - page))} disabled={offset === 0}>
          ← Earlier
        </button>
        <span className="muted">
          {offset + 1}–{Math.min(offset + page, rows)} of {rows.toLocaleString("en-IN")}
        </span>
        <button
          onClick={() => setOffset(Math.min(rows - page, offset + page))}
          disabled={offset + page >= rows}
        >
          Later →
        </button>
      </div>
    </>
  );
}

// --- 2. which years to price ---------------------------------------------

export function YearsStep({
  years,
  available,
  latestYear,
  onChange,
}: {
  years: { start: number; end: number };
  available: { first: number; last: number };
  latestYear: number;
  onChange: (start: number, end: number) => void;
}) {
  const options = (from: number, to: number) =>
    Array.from({ length: Math.max(0, to - from + 1) }, (_, i) => from + i).map((year) => (
      <option key={year} value={year}>
        {year}
      </option>
    ));
  const count = years.end - years.start + 1;
  return (
    <>
      <p className="step-lede">
        Which years should the price be built from? Everything downstream — the
        variation, the bands, the burn cost — is measured over this window.
      </p>
      <div className="field">
        <label className="field-label" htmlFor="start-year">
          From
        </label>
        <select
          id="start-year"
          value={years.start}
          onChange={(event) => onChange(Number(event.target.value), years.end)}
        >
          {options(available.first, years.end - 1)}
        </select>
      </div>
      <div className="field">
        <label className="field-label" htmlFor="end-year">
          To
        </label>
        <select
          id="end-year"
          value={years.end}
          onChange={(event) => onChange(years.start, Number(event.target.value))}
        >
          {options(years.start + 1, available.last)}
        </select>
      </div>
      <p className="step-note">
        <strong>{count} years</strong> selected. ERA5-Land publishes final data
        two to three months after a year ends, so {latestYear} is the latest
        usable year. Twenty or more years is the usual window for burn-cost
        pricing.
      </p>
    </>
  );
}

// --- 3. the insured unit, and how many ------------------------------------

export function UnitStep({
  unit,
  units,
  onUnit,
  onUnits,
}: {
  unit: Unit;
  units: number;
  onUnit: (next: Unit) => void;
  onUnits: (next: number) => void;
}) {
  return (
    <>
      <p className="step-lede">
        Describe one installation. The policy insures a number of identical
        units, so capacity and expected generation scale with the count; the
        performance ratio does not.
      </p>
      <h3>One unit</h3>
      <NumberField
        label="Installed capacity"
        note="A kVA rating is treated as kWp"
        value={unit.capacity_kw}
        step={0.5}
        suffix="kW"
        lower={{ value: 0.1, reason: "Capacity has to be positive — it multiplies the index to give generation." }}
        onChange={(capacity_kw) => onUnit({ ...unit, capacity_kw })}
      />
      <NumberField
        label="Performance ratio"
        note="Share of sunlight that becomes usable electricity"
        value={unit.pr}
        step={0.01}
        lower={{ value: 0.01, reason: "A performance ratio of zero would generate nothing at all." }}
        upper={{ value: 1, reason: "Cannot exceed 1: a panel cannot deliver more electricity than the sunlight falling on it." }}
        onChange={(pr) => onUnit({ ...unit, pr })}
      />
      <NumberField
        label="Expected annual generation"
        note="AEP50 — what one unit is promised in a normal year. Also the trigger."
        value={unit.aep50}
        step={50}
        suffix="kWh"
        lower={{ value: 1, reason: "The trigger has to be a positive amount of generation." }}
        onChange={(aep50) => onUnit({ ...unit, aep50 })}
      />

      <h3 className="spaced">How many units</h3>
      <NumberField
        label="Units insured"
        value={units}
        step={1}
        lower={{ value: 1, reason: "At least one unit has to be insured." }}
        onChange={(next) => onUnits(Math.max(1, Math.round(next)))}
      />
      <p className="step-note">
        Insuring {units.toLocaleString("en-IN")} {units === 1 ? "unit" : "units"}:{" "}
        <strong>
          {(unit.capacity_kw * units).toLocaleString("en-IN", { maximumFractionDigits: 2 })} kW
        </strong>{" "}
        total, expected <strong>{kwh(unit.aep50 * units)}</strong> a year.
      </p>
    </>
  );
}

// --- 4. tariff ------------------------------------------------------------

export function TariffStep({
  tariff,
  expectedGeneration,
  onChange,
}: {
  tariff: number;
  expectedGeneration: number;
  onChange: (next: number) => void;
}) {
  return (
    <>
      <p className="step-lede">
        What one unit of electricity is worth to the customer. This is what
        turns a shortfall in kWh into a payout in rupees.
      </p>
      <NumberField
        label="Electricity tariff"
        value={tariff}
        step={0.05}
        suffix="₹/kWh"
        lower={{ value: 0.01, reason: "A zero tariff would make every payout zero." }}
        onChange={onChange}
      />
      <p className="step-note">
        At this tariff a normal year is worth{" "}
        <strong>{inr(expectedGeneration * tariff)}</strong> of electricity across
        every insured unit.
      </p>
    </>
  );
}

// --- 5. how many bands, and where they sit --------------------------------

export function BandsStep({
  inputs,
  result,
  onChange,
}: {
  inputs: Inputs;
  result: PriceResponse | undefined;
  onChange: (bands: Pick<Inputs, "boundary_sigmas" | "payout_sigmas">) => void;
}) {
  const levels = inputs.payout_sigmas.length;
  const names = Array.from({ length: levels }, (_, i) => levelName(i + 1, levels));
  const sigma = result?.bands.sigma;
  const trigger = inputs.aep50;

  const setBoundary = (index: number, value: number) => {
    const next = [...inputs.boundary_sigmas];
    next[index] = value;
    onChange({ ...inputs, boundary_sigmas: next });
  };

  const addBand = () => {
    const lastBoundary = inputs.boundary_sigmas.at(-1) ?? 0;
    const lastPayout = inputs.payout_sigmas.at(-1) ?? 0.25;
    onChange({
      boundary_sigmas: [...inputs.boundary_sigmas, Number((lastBoundary + 0.5).toFixed(2))],
      payout_sigmas: [...inputs.payout_sigmas, Number((lastPayout + 0.5).toFixed(2))],
    });
  };

  const removeBand = () => {
    if (levels <= 1) return;
    onChange({
      boundary_sigmas: inputs.boundary_sigmas.slice(0, -1),
      payout_sigmas: inputs.payout_sigmas.slice(0, -1),
    });
  };

  return (
    <>
      <p className="step-lede">
        How many severity bands the policy has, and how far below the trigger
        each one ends. Boundaries are set in standard deviations of modelled
        generation, so they follow how much this location actually varies.
      </p>

      <div className="band-count">
        <div>
          <strong>
            {levels} paying {levels === 1 ? "band" : "bands"}
          </strong>
          <span className="field-note">
            {names.join(" · ")} — plus the years that pay nothing
          </span>
        </div>
        <span style={{ display: "flex", gap: 8 }}>
          <button onClick={removeBand} disabled={levels <= 1}>
            Remove band
          </button>
          <button onClick={addBand}>Add band</button>
        </span>
      </div>

      <h3 className="spaced">Where each band ends</h3>
      {inputs.boundary_sigmas.map((value, index) => {
        const previous = index === 0 ? 0 : inputs.boundary_sigmas[index - 1];
        const next = inputs.boundary_sigmas[index + 1];
        return (
          <NumberField
            key={index}
            label={`${names[index]} / ${names[index + 1]}`}
            note={
              sigma
                ? `${kwh(trigger - value * sigma)} — the trigger less ${value}σ`
                : `trigger less ${value}σ`
            }
            value={value}
            step={0.05}
            suffix="σ"
            lower={{
              value: Number((previous + 0.05).toFixed(2)),
              reason:
                index === 0
                  ? "Must sit below the trigger, so it cannot be zero or less."
                  : `Cannot go below ${previous}σ: ${names[index]} already ends there, and each band has to sit further below the trigger than the one before it.`,
            }}
            upper={
              next === undefined
                ? undefined
                : {
                    value: Number((next - 0.05).toFixed(2)),
                    reason: `Cannot exceed ${next}σ: ${names[index + 1]} ends there, and bands cannot overlap.`,
                  }
            }
            onChange={(v) => setBoundary(index, v)}
          />
        );
      })}

      {result ? (
        <>
          <div className="figure-row spaced">
            <div>
              <div className="figure-value">{result.bands.sigma.toFixed(2)} kWh</div>
              <div className="figure-label">σ — standard deviation of modelled generation</div>
            </div>
            <div>
              <div className="figure-value">{kwh(result.summary.mean_generation)}</div>
              <div className="figure-label">
                mean generation · {result.summary.mean_generation_vs_trigger >= 0 ? "+" : ""}
                {(result.summary.mean_generation_vs_trigger * 100).toFixed(2)}% against the trigger
              </div>
            </div>
            <div>
              <div className="figure-value">{result.summary.years_triggering}</div>
              <div className="figure-label">
                of {result.summary.years} years would have paid, as the bands stand
              </div>
            </div>
          </div>
          <BacktestChart backtest={result.backtest} bands={result.bands} levels={levels} />
        </>
      ) : (
        <p className="muted spaced">Modelling generation…</p>
      )}
    </>
  );
}

// --- 6. what each band pays ----------------------------------------------

export function PayoutsStep({
  inputs,
  result,
  onChange,
}: {
  inputs: Inputs;
  result: PriceResponse | undefined;
  onChange: (payout_sigmas: number[]) => void;
}) {
  const levels = inputs.payout_sigmas.length;
  const sigma = result?.bands.sigma;

  const setPayout = (index: number, value: number) => {
    const next = [...inputs.payout_sigmas];
    next[index] = value;
    onChange(next);
  };

  return (
    <>
      <p className="step-lede">
        Each band pays one fixed amount. The figure is a shortfall in standard
        deviations; the tariff turns it into rupees. Setting it at the midpoint
        of the band pays roughly the electricity that band's years actually
        lost.
      </p>
      {inputs.payout_sigmas.map((value, index) => {
        const lower = index === 0 ? 0 : inputs.boundary_sigmas[index - 1];
        const upper = inputs.boundary_sigmas[index];
        const midpoint =
          upper === undefined ? lower + 0.25 : Number(((lower + upper) / 2).toFixed(3));
        return (
          <NumberField
            key={index}
            label={`${levelName(index + 1, levels)} pays`}
            note={
              (sigma ? `${inr(value * sigma * inputs.tariff)} · ` : "") +
              (upper === undefined
                ? `band runs from ${lower}σ below the trigger and down · midpoint ${midpoint}σ`
                : `band runs ${lower}σ to ${upper}σ below the trigger · midpoint ${midpoint}σ`)
            }
            value={value}
            step={0.05}
            suffix="σ"
            lower={{
              value: 0.05,
              reason: "A band that pays nothing is the same as not having the band — remove it instead.",
            }}
            onChange={(next) => setPayout(index, next)}
          />
        );
      })}
      <p className="step-note">
        Most it can ever pay: <strong>{result ? inr(result.bands.max_payout) : "—"}</strong> in a
        year. Payouts need not increase with severity — a deliberately flat or
        falling curve is allowed. Bands are added or removed on the previous
        step.
      </p>
    </>
  );
}

// --- 7. pricing loadings --------------------------------------------------

export function PricingStep({
  inputs,
  result,
  onChange,
}: {
  inputs: Inputs;
  result: PriceResponse | undefined;
  onChange: (patch: Partial<Inputs>) => void;
}) {
  const headroom = (other: number) => Number((0.95 - other).toFixed(3));
  return (
    <>
      <p className="step-lede">
        The burn cost is what the history says the risk costs. These three add
        the margin on top of it.
      </p>
      <NumberField
        label="Risk coefficient"
        note="× standard deviation of payout — a cushion for how much the payout swings"
        value={inputs.risk_coeff}
        step={0.05}
        lower={{ value: 0, reason: "A negative risk load would price below the burn cost." }}
        onChange={(risk_coeff) => onChange({ risk_coeff })}
      />
      <NumberField
        label="Running costs"
        note="Administration, distribution, claims handling"
        value={inputs.expense_pct}
        step={0.005}
        asPercent
        lower={{ value: 0, reason: "Cannot be negative." }}
        upper={{
          value: headroom(inputs.profit_pct),
          reason: `Cannot exceed ${(headroom(inputs.profit_pct) * 100).toFixed(1)}% while profit is ${(inputs.profit_pct * 100).toFixed(1)}%: the premium divides by what is left after both, so together they have to stay under 100%.`,
        }}
        onChange={(expense_pct) => onChange({ expense_pct })}
      />
      <NumberField
        label="Profit margin"
        note="What the insurer keeps"
        value={inputs.profit_pct}
        step={0.005}
        asPercent
        lower={{ value: 0, reason: "Cannot be negative." }}
        upper={{
          value: headroom(inputs.expense_pct),
          reason: `Cannot exceed ${(headroom(inputs.expense_pct) * 100).toFixed(1)}% while running costs are ${(inputs.expense_pct * 100).toFixed(1)}%: the premium divides by what is left after both, so together they have to stay under 100%.`,
        }}
        onChange={(profit_pct) => onChange({ profit_pct })}
      />
      {result && (
        <dl className="waterfall spaced">
          <div className="stat">
            <dt>Burn cost</dt>
            <dd>{inr(result.premium.burn_cost)}</dd>
          </div>
          <div className="stat">
            <dt>Risk margin</dt>
            <dd>{inr(result.premium.risk_margin)}</dd>
          </div>
          <div className="stat">
            <dt>Technical premium</dt>
            <dd>{inr(result.premium.technical_premium)}</dd>
          </div>
          <div className="stat total">
            <dt>Gross premium</dt>
            <dd>{inr(result.premium.gross_premium)}</dd>
          </div>
        </dl>
      )}
      <p className="step-note">
        Running costs and profit are shares of the final price, not of the cost
        above, so the last line divides rather than adding them on.
      </p>
    </>
  );
}
