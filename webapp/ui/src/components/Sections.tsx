import type { ReactNode } from "react";
import { POLICY } from "../api";
import { capacity, count, inr } from "../format";
import type { PriceResponse } from "../types";
import { Calculator, Chart, MapPin, Sun } from "./Icons";

function SectionHead({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="section-head">
      <h2>{title}</h2>
      <p>{children}</p>
    </div>
  );
}

const UNIT_COUNTS = [1, 100, 1000, 10000];

export function Scale({ result }: { result: PriceResponse }) {
  const { premium, bands, summary } = result;
  // Display only, not a model step: every term is a multiple of capacity, and
  // identical units on one grid square share one reading, so N units cost and
  // pay exactly N times one.
  const money = (value: number) => inr(value, value < 1000 ? 2 : 0);

  return (
    <section className="section" id="scale">
      <SectionHead title="Premium at Scale">
        More units at the same pincode? The price per unit stays the same, so
        the total simply grows with the number of units.
      </SectionHead>

      <div className="scale-grid">
        {UNIT_COUNTS.map((n) => (
          <article key={n} className="scale-card">
            <span className="scale-count">
              {count(n)} {n === 1 ? "unit" : "units"}
            </span>
            <span className="scale-capacity">{capacity(POLICY.inputs.capacity_kw * n)} capacity</span>
            <dl>
              <div>
                <dt>Yearly premium</dt>
                <dd>{money(premium.gross_premium * n)}</dd>
              </div>
              <div>
                <dt>Biggest payout so far</dt>
                <dd>
                  {summary.worst_year_payout === null
                    ? "None"
                    : money(summary.worst_year_payout * n)}
                </dd>
              </div>
              <div>
                <dt>Most it can pay in a year</dt>
                <dd>{money(bands.max_payout * n)}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}

export function HowItWorks() {
  const steps = [
    {
      icon: <MapPin />,
      title: "Find the Location",
      body: "The pincode is matched to the weather grid square, about 11 km across, that covers it.",
    },
    {
      icon: <Sun />,
      title: "Read the Sunshine",
      body: `Daily sunshine data for that square is collected for every year from ${POLICY.startYear} to ${POLICY.endYear}.`,
    },
    {
      icon: <Chart />,
      title: "Check Every Year",
      body: `Each year's production for a ${POLICY.inputs.capacity_kw} kVA unit is estimated and compared with the ${POLICY.inputs.aep50.toLocaleString("en-IN")} kWh trigger.`,
    },
    {
      icon: <Calculator />,
      title: "Set the Premium",
      body: "The premium is the average yearly payout, plus a risk margin, expenses and profit.",
    },
  ];

  return (
    <section className="section" id="how">
      <SectionHead title="How it Works">
        Four steps turn a pincode into a price. The rules are the same for
        every location in India.
      </SectionHead>
      <div className="features">
        {steps.map((step) => (
          <div key={step.title} className="feature">
            <span className="feature-icon">{step.icon}</span>
            <div>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
