import type { ReactNode } from "react";
import { POLICY } from "../api";
import { capacity, coords, count, inr, kwh } from "../format";
import type { LocationResponse, PriceResponse } from "../types";
import { levelName } from "../types";
import { BacktestChart } from "./BacktestChart";
import { PincodeMap } from "./PincodeMap";

const PORTFOLIO_SIZES = [1, 100, 1000, 10000];

export function Policy({
  location,
  result,
}: {
  location: LocationResponse;
  result: PriceResponse;
}) {
  const place = placeName(location);
  return (
    <div className="policy">
      <PremiumCard location={location} result={result} place={place} />
      <CoverageTerms location={location} result={result} place={place} />
      <PayoutSheet result={result} />
      <Portfolio result={result} />
    </div>
  );
}

function placeName(location: LocationResponse): string {
  const { Office_Name, Division, Circle } = location.attributes;
  const office = Office_Name?.replace(/\s+(S\.?O|B\.?O|H\.?O|G\.?P\.?O)\.?$/i, "");
  return [office, Division, Circle].filter(Boolean).join(", ") || `Pincode ${location.pincode}`;
}

function Section({
  eyebrow,
  title,
  lede,
  children,
}: {
  eyebrow: string;
  title: ReactNode;
  lede?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="card">
      <div className="card-body">
        <span className="eyebrow">{eyebrow}</span>
        <h2 className="section-title">{title}</h2>
        {lede && <p className="section-lede">{lede}</p>}
      </div>
      {children}
    </section>
  );
}

function PremiumCard({
  location,
  result,
  place,
}: {
  location: LocationResponse;
  result: PriceResponse;
  place: string;
}) {
  const { premium, summary, bands } = result;
  const loading = premium.gross_premium - premium.technical_premium;
  const parts = [
    { key: "burn", label: "Expected payout (burn cost)", value: premium.burn_cost },
    { key: "risk", label: "Risk margin", value: premium.risk_margin },
    { key: "load", label: "Expenses & profit", value: loading },
  ];
  const total = premium.gross_premium || 1;

  return (
    <Section
      eyebrow={`Policy · Pincode ${location.pincode}`}
      title={place}
      lede={`One ${POLICY.inputs.capacity_kw} kVA rooftop, priced on ${POLICY.startYear}–${POLICY.endYear} ERA5-Land irradiance.`}
    >
      <div className="split">
        <div className="card-body premium">
          <h3 className="rule">Annual premium</h3>
          <div className="premium-figure">{inr(premium.gross_premium)}</div>
          <div className="premium-note">per rooftop, per year</div>

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
            <div className="total">
              <dt>Gross premium</dt>
              <dd>{inr(premium.gross_premium)}</dd>
            </div>
          </dl>
        </div>

        <div className="card-body">
          <h3 className="rule">At a glance</h3>
          <div className="kpis">
            <Kpi label="Sum insured" value={inr(bands.max_payout)} note="the Severe-band payout" />
            <Kpi
              label="Years that paid"
              value={`${summary.years_triggering} of ${summary.years}`}
              note={`${(summary.trigger_frequency * 100).toFixed(0)}% of the record`}
            />
            <Kpi
              label="Average claim"
              value={
                summary.average_payout_when_paying === null
                  ? "—"
                  : inr(summary.average_payout_when_paying)
              }
              note="in a year that pays"
            />
            <Kpi
              label="Worst year"
              value={summary.worst_year === null ? "None" : String(summary.worst_year)}
              note={
                summary.worst_year_payout === null
                  ? "no year fell below the trigger"
                  : `paid ${inr(summary.worst_year_payout)}`
              }
            />
            <Kpi
              label="Typical generation"
              value={kwh(summary.mean_generation)}
              note={`${summary.mean_generation_vs_trigger >= 0 ? "+" : ""}${(summary.mean_generation_vs_trigger * 100).toFixed(1)}% vs the ${kwh(bands.trigger)} promise`}
            />
            <Kpi
              label="Year-to-year σ"
              value={`${bands.sigma.toFixed(1)} kWh`}
              note="sets where every band sits"
            />
          </div>
        </div>
      </div>
    </Section>
  );
}

function Kpi({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="kpi">
      <span className="label">{label}</span>
      <span className="kpi-value">{value}</span>
      <span className="kpi-note">{note}</span>
    </div>
  );
}

function CoverageTerms({
  location,
  result,
  place,
}: {
  location: LocationResponse;
  result: PriceResponse;
  place: string;
}) {
  const { bands } = result;
  const { inputs } = POLICY;
  const terms: [string, ReactNode][] = [
    ["Policyholder", `Rooftop solar owner · ${inputs.capacity_kw} kVA grid-connected PV`],
    ["Location", `${place} · ${location.pincode}`],
    [
      "Data source",
      `Surface solar radiation downwards, ERA5-Land (Geo Reference: ${coords(location.pixel.lat, location.pixel.lon)})`,
    ],
    [
      "Payout based on",
      `Modelled annual generation: yearly irradiance × ${inputs.pr * 100}% performance ratio × ${inputs.capacity_kw} kW`,
    ],
    ["Coverage period", "1st January to 31st December (annual settlement)"],
    ["Trigger level", `${kwh(bands.trigger)} — the expected annual generation`],
    [
      "Payout calculation",
      `Fixed amount per severity band, worth the shortfall at ${inputs.tariff.toFixed(2)} ₹/kWh`,
    ],
    ["Maximum payout", `${inr(bands.max_payout)} per year (Severe band)`],
  ];

  return (
    <Section
      eyebrow="Solar irradiance"
      title="Coverage terms"
      lede="The same terms for every pincode. Only the weather record behind them changes."
    >
      <div className="split">
        <div className="card-body">
          <h3 className="rule">Terms</h3>
          <dl className="terms">
            {terms.map(([label, value]) => (
              <div key={label}>
                <dt className="label">{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div className="card-body">
          <h3 className="rule">Settlement cell</h3>
          <p className="muted small">
            Claims settle on the grid cell's reading, not the roof's own output.
            The cell is drawn to scale against the pincode boundary.
          </p>
          <PincodeMap location={location} />
        </div>
      </div>
    </Section>
  );
}

function PayoutSheet({ result }: { result: PriceResponse }) {
  const { bands, summary, backtest } = result;
  const levels = bands.payouts.length;
  const edges = [bands.trigger, ...bands.boundaries];
  const sigmas = [0, ...POLICY.inputs.boundary_sigmas];

  const rows = [
    {
      level: 0,
      range: `${kwh(bands.trigger)} or more`,
      shortfall: "At or above trigger",
      payout: "—",
    },
    ...bands.payouts.map((payout, index) => {
      const level = index + 1;
      const upper = edges[index];
      const lower = edges[index + 1];
      return {
        level,
        range:
          lower === undefined ? `Below ${kwh(upper)}` : `${kwh(lower)} to ${kwh(upper)}`,
        shortfall:
          lower === undefined
            ? `More than ${sigmas[index]}σ`
            : `${sigmas[index]}σ – ${sigmas[index + 1]}σ`,
        payout: inr(payout),
      };
    }),
  ];

  return (
    <Section
      eyebrow="Payout sheet"
      title={`${result.start_year}–${result.end_year}, through the contract`}
      lede="Bands are measured in standard deviations of this location's own generation, so they follow how much the local sunshine actually varies."
    >
      <div className="card-body flush-top">
        <div className="table-wrap">
          <table className="sheet">
            <thead>
              <tr>
                <th>Band</th>
                <th>Annual generation</th>
                <th>Shortfall</th>
                <th className="num">Payout</th>
                <th className="num">Years on record</th>
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
                  <td>{row.shortfall}</td>
                  <td className="num">{row.payout}</td>
                  <td className="num">{summary.level_year_counts[String(row.level)] ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="rule chart-title">Modelled generation by year</h3>
        <BacktestChart backtest={backtest} bands={bands} levels={levels} />

        <details className="record">
          <summary>Year-by-year record</summary>
          <div className="table-wrap">
            <table className="sheet compact">
              <thead>
                <tr>
                  <th>Year</th>
                  <th className="num">Irradiance kWh/m²</th>
                  <th className="num">Generation kWh</th>
                  <th>Band</th>
                  <th className="num">Payout</th>
                </tr>
              </thead>
              <tbody>
                {backtest.map((row) => (
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
    </Section>
  );
}

function Portfolio({ result }: { result: PriceResponse }) {
  const { premium, bands, summary } = result;
  // Display only, not a model step: every term is a multiple of capacity, and
  // identical rooftops on one cell share one index reading, so N of them cost
  // and pay exactly N times one.
  return (
    <Section
      eyebrow="Scale"
      title="From one roof to a portfolio"
      lede={
        <>
          Every rooftop in this pincode settles on the same grid cell, so their
          claims arrive together and the book scales one-for-one. Spreading the
          same book across pincodes is what diversifies it — and the same
          engine prices all of them.
        </>
      }
    >
      <div className="card-body flush-top">
        <div className="table-wrap">
          <table className="sheet scale">
            <thead>
              <tr>
                <th>Rooftops</th>
                <th className="num">Installed capacity</th>
                <th className="num">Annual premium</th>
                <th className="num">Worst year on record</th>
                <th className="num">Maximum annual payout</th>
              </tr>
            </thead>
            <tbody>
              {PORTFOLIO_SIZES.map((n) => (
                <tr key={n}>
                  <td>
                    <strong>{count(n)}</strong>
                  </td>
                  <td className="num">{capacity(POLICY.inputs.capacity_kw * n)}</td>
                  <td className="num">{inr(premium.gross_premium * n, n === 1 ? 2 : 0)}</td>
                  <td className="num">
                    {summary.worst_year_payout === null
                      ? "No claim"
                      : inr(summary.worst_year_payout * n, n === 1 ? 2 : 0)}
                  </td>
                  <td className="num">{inr(bands.max_payout * n, n === 1 ? 2 : 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Section>
  );
}
