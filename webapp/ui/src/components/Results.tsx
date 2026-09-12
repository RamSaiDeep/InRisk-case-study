import type { PriceResponse } from "../types";
import { levelName } from "../types";
import { BacktestChart } from "./BacktestChart";

const inr = (value: number) =>
  `₹${value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const kwh = (value: number) =>
  `${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })} kWh`;

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

export function Results({ result, stale }: { result: PriceResponse; stale: boolean }) {
  const { bands, premium, summary, backtest } = result;
  const levels = bands.payouts.length;

  return (
    <div className={stale ? "results stale" : "results"}>
      <div className="results-row">
        <div className="card">
          <h3>Premium</h3>
          <div className="hero">{inr(premium.gross_premium)}</div>
          <div className="hero-note">per policy per year</div>
          <dl className="waterfall" style={{ marginTop: 10 }}>
            <Stat label="Burn cost" value={inr(premium.burn_cost)} />
            <Stat label="Risk margin" value={inr(premium.risk_margin)} />
            <Stat label="Technical premium" value={inr(premium.technical_premium)} />
            <div className="stat total">
              <dt>Gross premium</dt>
              <dd>{inr(premium.gross_premium)}</dd>
            </div>
          </dl>
        </div>

        <div className="card">
          <h3>How often it pays</h3>
          <div className="hero">
            {summary.years_triggering}
            <span style={{ fontSize: 17, color: "var(--ink-secondary)" }}>
              {" "}
              of {summary.years}
            </span>
          </div>
          <div className="hero-note">
            {(summary.trigger_frequency * 100).toFixed(0)}% of years on record
          </div>
          <dl style={{ marginTop: 10 }}>
            <Stat
              label="Average when paying"
              value={
                summary.average_payout_when_paying === null
                  ? "—"
                  : inr(summary.average_payout_when_paying)
              }
            />
            <Stat
              label="Worst year"
              value={
                summary.worst_year === null
                  ? "—"
                  : `${summary.worst_year} · ${inr(summary.worst_year_payout ?? 0)}`
              }
            />
            <Stat label="Sum insured" value={inr(bands.max_payout)} />
          </dl>
        </div>

        <div className="card">
          <h3>Contract geometry</h3>
          <dl>
            <Stat label="Trigger" value={kwh(bands.trigger)} />
            {bands.boundaries.map((boundary, index) => (
              <Stat
                key={boundary}
                label={`${levelName(index + 1, levels)} / ${levelName(index + 2, levels)}`}
                value={kwh(boundary)}
              />
            ))}
            <Stat label="σ of generation" value={`${bands.sigma.toFixed(2)} kWh`} />
            <Stat
              label="Mean generation"
              value={`${kwh(summary.mean_generation)} (${summary.mean_generation_vs_trigger >= 0 ? "+" : ""}${(summary.mean_generation_vs_trigger * 100).toFixed(2)}%)`}
            />
            <Stat
              label="Mean vs trigger"
              value={`${summary.mean_generation_sigmas_from_trigger >= 0 ? "+" : ""}${summary.mean_generation_sigmas_from_trigger.toFixed(2)}σ`}
            />
          </dl>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <h2>Backtest, {result.start_year}–{result.end_year}</h2>
          <span className="muted" style={{ fontSize: 12 }}>
            Each year run through the same contract
          </span>
        </div>
        <BacktestChart backtest={backtest} bands={bands} levels={levels} />
      </div>

      <div className="card">
        <div className="card-head">
          <h2>Year by year</h2>
          <span className="muted" style={{ fontSize: 12 }}>
            {Array.from({ length: levels + 1 }, (_, level) => {
              const count = summary.level_year_counts[String(level)] ?? 0;
              return `${levelName(level, levels)} ${count}`;
            }).join(" · ")}
          </span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Year</th>
                <th>Days</th>
                <th>Index kWh/m²</th>
                <th>Generation kWh</th>
                <th>Band</th>
                <th>Payout</th>
              </tr>
            </thead>
            <tbody>
              {backtest.map((row) => (
                <tr key={row.year} className={row.payout > 0 ? "paying" : undefined}>
                  <td>{row.year}</td>
                  <td>{row.days}</td>
                  <td>{row.index.toFixed(2)}</td>
                  <td>{row.generation.toFixed(2)}</td>
                  <td>{levelName(row.level, levels)}</td>
                  <td>{row.payout === 0 ? "—" : inr(row.payout)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
