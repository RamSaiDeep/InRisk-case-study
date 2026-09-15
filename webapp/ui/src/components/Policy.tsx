import type { ReactNode } from "react";
import { POLICY } from "../api";
import { coords, inr, kwh } from "../format";
import type { LocationResponse, PriceResponse } from "../types";
import { levelName } from "../types";
import { BacktestChart } from "./BacktestChart";
import { PincodeMap } from "./PincodeMap";

export function placeName(location: LocationResponse): string {
  const { Office_Name, Division, Circle } = location.attributes;
  const office = Office_Name?.replace(/\s+(S\.?O|B\.?O|H\.?O|G\.?P\.?O)\.?$/i, "");
  return [office, Division, Circle].filter(Boolean).join(", ") || `Pincode ${location.pincode}`;
}

/** Everything under "Your Policy": terms and settlement area on the left,
 *  premium and payout sheet on the right, the twenty-year record beneath. */
export function PolicyDetails({
  location,
  result,
}: {
  location: LocationResponse;
  result: PriceResponse;
}) {
  const levels = result.bands.payouts.length;
  return (
    <>
      <div className="split">
        <div className="col">
          <CoverageTerms location={location} result={result} />
          <h3 className="rule spaced">Settlement Area</h3>
          <p className="note">
            Payouts use the weather reading for this grid square, not the
            unit's own meter. The square is drawn to scale over the pincode.
          </p>
          <PincodeMap location={location} />
        </div>
        <div className="col">
          <Premium result={result} />
          <PayoutSheet result={result} />
        </div>
      </div>

      <div className="col full">
        <h3 className="rule">Last {result.summary.years} Years</h3>
        <p className="note">
          Estimated yearly production of one unit, measured against the{" "}
          {kwh(result.bands.trigger)} trigger. Coloured bars are years the
          cover would have paid.
        </p>
        <BacktestChart backtest={result.backtest} bands={result.bands} levels={levels} />
        <details className="record">
          <summary>See every year</summary>
          <div className="table-wrap">
            <table className="sheet compact">
              <thead>
                <tr>
                  <th>Year</th>
                  <th className="num">Sunshine kWh/m²</th>
                  <th className="num">Production kWh</th>
                  <th>Band</th>
                  <th className="num">Payout</th>
                </tr>
              </thead>
              <tbody>
                {result.backtest.map((row) => (
                  <tr key={row.year} className={row.payout > 0 ? "paying" : undefined}>
                    <td>{row.year}</td>
                    <td className="num">{row.index.toFixed(1)}</td>
                    <td className="num">{row.generation.toFixed(0)}</td>
                    <td>{levelName(row.level, levels)}</td>
                    <td className="num">{row.payout === 0 ? "—" : inr(row.payout)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </div>
    </>
  );
}

function CoverageTerms({
  location,
  result,
}: {
  location: LocationResponse;
  result: PriceResponse;
}) {
  const { bands } = result;
  const { inputs } = POLICY;
  const terms: [string, ReactNode][] = [
    ["Policyholder", `Owner of a ${inputs.capacity_kw} kVA grid-connected solar unit`],
    ["Location", `${placeName(location)} (${location.pincode})`],
    [
      "Data source",
      `Surface solar radiation downwards, ERA5-Land (Geo Reference: ${coords(location.pixel.lat, location.pixel.lon, 1)})`,
    ],
    ["Payout based on", "Yearly solar irradiance, turned into the unit's expected production"],
    ["Coverage period", "1st January to 31st December (yearly payout)"],
    ["Payout calculation", "A fixed amount for each severity band - see the Payout Sheet"],
    ["Trigger level", `${kwh(bands.trigger)} a year (expected production)`],
    ["Maximum payout", `${inr(bands.max_payout)} a year`],
  ];

  return (
    <>
      <h3 className="rule">Coverage Terms</h3>
      <dl className="terms">
        {terms.map(([label, value]) => (
          <div key={label}>
            <dt className="label">{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </>
  );
}

function Premium({ result }: { result: PriceResponse }) {
  const { premium, summary } = result;
  const parts = [
    { key: "burn", label: "Average yearly payout", value: premium.burn_cost },
    { key: "risk", label: "Risk margin", value: premium.risk_margin },
    { key: "load", label: "Expenses & profit", value: premium.gross_premium - premium.technical_premium },
  ];
  const total = premium.gross_premium || 1;

  return (
    <>
      <h3 className="rule">Premium</h3>
      <div className="premium-figure">{inr(premium.gross_premium)}</div>
      <div className="premium-note">per unit, per year</div>
      {premium.gross_premium > 0 && (
        <div className="stack" aria-hidden>
          {parts.map((part) => (
            <span
              key={part.key}
              className={`stack-${part.key}`}
              style={{ width: `${(part.value / total) * 100}%` }}
            />
          ))}
        </div>
      )}
      <dl className="waterfall">
        {parts.map((part) => (
          <div key={part.key}>
            <dt>
              <span className={`dot stack-${part.key}`} />
              {part.label}
            </dt>
            <dd>{inr(part.value)}</dd>
          </div>
        ))}
      </dl>
      <div className="facts">
        <div>
          <span className="label">Years that paid</span>
          <strong>
            {summary.years_triggering} of {summary.years}
          </strong>
        </div>
        <div>
          <span className="label">Biggest payout</span>
          <strong>
            {summary.worst_year === null
              ? "None"
              : `${inr(summary.worst_year_payout ?? 0)} (${summary.worst_year})`}
          </strong>
        </div>
      </div>
    </>
  );
}

function PayoutSheet({ result }: { result: PriceResponse }) {
  const { bands, summary } = result;
  const levels = bands.payouts.length;
  const edges = [bands.trigger, ...bands.boundaries];
  const rows = [
    { level: 0, range: `${kwh(bands.trigger)} or more`, payout: "—" },
    ...bands.payouts.map((payout, index) => {
      const upper = edges[index];
      const lower = edges[index + 1];
      return {
        level: index + 1,
        range: lower === undefined ? `Below ${kwh(upper)}` : `${kwh(lower)} – ${kwh(upper)}`,
        payout: inr(payout),
      };
    }),
  ];

  return (
    <>
      <h3 className="rule spaced">Payout Sheet</h3>
      <div className="table-wrap">
        <table className="sheet">
          <thead>
            <tr>
              <th>Band</th>
              <th>Yearly production</th>
              <th className="num">Payout</th>
              <th className="num">Past years</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.level}>
                <td>
                  <span className="swatch" style={{ background: `var(--level-${row.level})` }} />
                  {levelName(row.level, levels)}
                </td>
                <td>{row.range}</td>
                <td className="num">{row.payout}</td>
                <td className="num">{summary.level_year_counts[String(row.level)] ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="note italic">
        Band edges follow how much sunshine at this location normally changes
        from year to year ({bands.sigma.toFixed(1)} kWh), so every pincode gets
        bands that fit its own weather.
      </p>
    </>
  );
}
