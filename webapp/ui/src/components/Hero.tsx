import type { Status } from "../App";
import { PINCODE_COUNT, POLICY } from "../api";
import { count } from "../format";

const EXAMPLES = [
  { pincode: "380006", city: "Ahmedabad" },
  { pincode: "302001", city: "Jaipur" },
  { pincode: "110001", city: "New Delhi" },
  { pincode: "400001", city: "Mumbai" },
  { pincode: "560001", city: "Bengaluru" },
  { pincode: "700001", city: "Kolkata" },
];

const STAGES = ["Locate", "Pull 20 years", "Price"];

export function Hero({
  draft,
  onDraft,
  onSubmit,
  status,
  active,
}: {
  draft: string;
  onDraft: (value: string) => void;
  onSubmit: (pincode: string) => void;
  status: Status;
  active: string | null;
}) {
  const working = status.name === "working";
  const years = POLICY.endYear - POLICY.startYear + 1;

  return (
    <section className="hero" id="price">
      <div className="hero-art" aria-hidden>
        <SolarScene />
        <div className="hero-art-caption">
          <span className="eyebrow light">Solar irradiance index</span>
          <span>One contract · every pincode in India</span>
        </div>
      </div>

      <div className="hero-panel">
        <span className="eyebrow light">Parametric insurance</span>
        <h1>Solar Generation Shortfall Cover</h1>
        <p className="hero-lede">
          A rooftop owner is promised a year of sunshine. When the satellite
          record says it fell short, the policy pays - no site visit, no proof
          of loss. Enter any Indian pincode to see its policy priced.
        </p>

        <form
          className="pin-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (draft.length === 6) onSubmit(draft);
          }}
        >
          <label htmlFor="pincode" className="sr-only">
            Pincode
          </label>
          <input
            id="pincode"
            type="text"
            inputMode="numeric"
            autoComplete="postal-code"
            placeholder="Enter a 6-digit pincode"
            value={draft}
            maxLength={6}
            onChange={(event) => onDraft(event.target.value.replace(/\D/g, ""))}
          />
          <button type="submit" disabled={draft.length !== 6 || (working && draft === active)}>
            <ArrowIcon />
            {working && draft === active ? "Pricing…" : "Get my premium"}
          </button>
        </form>

        <div className="examples">
          <span>Try</span>
          {EXAMPLES.map((example) => (
            <button
              key={example.pincode}
              type="button"
              className={example.pincode === active ? "chip active" : "chip"}
              onClick={() => onSubmit(example.pincode)}
            >
              {example.pincode} <em>{example.city}</em>
            </button>
          ))}
        </div>

        {status.name === "working" && (
          <div className="progress" role="status" aria-live="polite">
            <ol className="progress-steps">
              {STAGES.map((label, index) => (
                <li
                  key={label}
                  className={
                    index < status.step ? "done" : index === status.step ? "current" : undefined
                  }
                >
                  {label}
                </li>
              ))}
            </ol>
            <div className="progress-bar">
              <span
                style={{
                  width: `${Math.round(((status.step + (status.step === 1 ? status.progress : 0)) / 3) * 100)}%`,
                }}
              />
            </div>
            <p>{status.message}</p>
            {status.step === 1 && (
              <p className="progress-note">
                The first request for a pincode pulls every day since{" "}
                {POLICY.startYear} from ERA5-Land, so it can take a minute.
              </p>
            )}
          </div>
        )}

        {status.name === "error" && (
          <div className="alert" role="alert">
            <p>{status.message}</p>
            {status.retryable && active === draft && (
              <button type="button" onClick={() => onSubmit(draft)}>
                Try again
              </button>
            )}
          </div>
        )}

        <div className="scale-list">
          <h2>Built to scale</h2>
          <ul>
            <li>
              <strong>{count(PINCODE_COUNT)}</strong> pincodes priceable
            </li>
            <li>
              <strong>{years} years</strong> of daily irradiance each
            </li>
            <li>
              <strong>0.1°</strong> ERA5-Land settlement cells
            </li>
            <li>
              <strong>1 → 10,000</strong> rooftops per location
            </li>
          </ul>
        </div>
      </div>
    </section>
  );
}

function ArrowIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden>
      <circle cx="10" cy="10" r="8.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M6.5 10h6.5M10.5 7l3 3-3 3"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** A drawn stand-in for a photograph: sky, sun, a panel array in perspective,
 *  and the faint reanalysis grid the whole contract settles on. */
function SolarScene() {
  const W = 640;
  const H = 720;
  // The array's top edge runs from (0, topLeft) to (W, topRight).
  const topLeft = 470;
  const topRight = 340;
  const rows = 7;
  const cols = 9;
  const rowLines = Array.from({ length: rows }, (_, i) => {
    const t = (i + 1) / rows;
    return { y1: topLeft + (H - topLeft) * t, y2: topRight + (H - topRight) * t * 1.02 };
  });
  const colLines = Array.from({ length: cols }, (_, i) => {
    const x = ((i + 1) / (cols + 1)) * W;
    const yTop = topLeft + (topRight - topLeft) * (x / W);
    return { x1: x, y1: yTop, x2: x - 90 - i * 18, y2: H };
  });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid slice" className="scene">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8fb3d1" />
          <stop offset="0.55" stopColor="#c9dcea" />
          <stop offset="1" stopColor="#eef4f8" />
        </linearGradient>
        <radialGradient id="glow" cx="0.72" cy="0.2" r="0.45">
          <stop offset="0" stopColor="#fff6d8" stopOpacity="0.95" />
          <stop offset="0.35" stopColor="#ffe9a8" stopOpacity="0.45" />
          <stop offset="1" stopColor="#ffe9a8" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="array" x1="0" y1="0" x2="0.3" y2="1">
          <stop offset="0" stopColor="#3a6fb8" />
          <stop offset="0.5" stopColor="#1d4f9c" />
          <stop offset="1" stopColor="#0c2d66" />
        </linearGradient>
        <linearGradient id="sheen" x1="0" y1="0" x2="1" y2="0.4">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0" />
          <stop offset="0.55" stopColor="#ffffff" stopOpacity="0.28" />
          <stop offset="0.7" stopColor="#ffffff" stopOpacity="0" />
        </linearGradient>
      </defs>

      <rect width={W} height={H} fill="url(#sky)" />
      <rect width={W} height={H} fill="url(#glow)" />

      {/* The reanalysis grid, drawn faintly across the sky. */}
      <g stroke="#ffffff" strokeOpacity="0.28" strokeWidth="1">
        {Array.from({ length: 8 }, (_, i) => (
          <line key={`v${i}`} x1={i * 90 + 20} y1={0} x2={i * 90 + 20} y2={topRight + 40} />
        ))}
        {Array.from({ length: 5 }, (_, i) => (
          <line key={`h${i}`} x1={0} y1={i * 90 + 30} x2={W} y2={i * 90 + 30} />
        ))}
      </g>
      <rect
        x={380}
        y={120}
        width={90}
        height={90}
        fill="#ffffff"
        fillOpacity="0.16"
        stroke="#ffffff"
        strokeOpacity="0.75"
        strokeDasharray="4 4"
      />

      <circle cx={460} cy={145} r={46} fill="#fff3c4" />
      <circle cx={460} cy={145} r={34} fill="#ffe28a" />

      <g fill="#ffffff">
        <ellipse cx={120} cy={170} rx={95} ry={30} opacity="0.85" />
        <ellipse cx={180} cy={150} rx={60} ry={34} opacity="0.9" />
        <ellipse cx={560} cy={270} rx={80} ry={22} opacity="0.7" />
        <ellipse cx={600} cy={255} rx={48} ry={24} opacity="0.75" />
      </g>

      <polygon points={`0,${topLeft} ${W},${topRight} ${W},${H} 0,${H}`} fill="url(#array)" />
      <g stroke="#c9dcf2" strokeOpacity="0.55" strokeWidth="1.4">
        {rowLines.map((line, i) => (
          <line key={`r${i}`} x1={0} y1={line.y1} x2={W} y2={line.y2} />
        ))}
        {colLines.map((line, i) => (
          <line key={`c${i}`} {...line} />
        ))}
      </g>
      <polygon points={`0,${topLeft} ${W},${topRight} ${W},${H} 0,${H}`} fill="url(#sheen)" />
      <line x1={0} y1={topLeft} x2={W} y2={topRight} stroke="#e8f0fa" strokeWidth="3" />
    </svg>
  );
}

export function HowItWorks() {
  const steps = [
    {
      n: "01",
      title: "Locate",
      body: "The pincode's India Post boundary gives a centroid, which snaps to the ERA5-Land grid cell that settles every claim.",
    },
    {
      n: "02",
      title: "Read twenty years",
      body: "Daily surface solar radiation for that cell since 2005, turned into the annual generation of a 3 kVA rooftop.",
    },
    {
      n: "03",
      title: "Price",
      body: "Each year runs through the same three-band contract; the average payout plus a risk margin and loadings is the premium.",
    },
  ];
  return (
    <section className="card how" id="how">
      <div className="card-body">
        <span className="eyebrow">Method</span>
        <h2 className="section-title">How it works</h2>
        <p className="section-lede">
          Nothing about the contract is tuned per location. The same terms are
          applied to whichever pincode is entered, which is what lets one
          policy design scale across the country.
        </p>
        <div className="how-grid">
          {steps.map((step) => (
            <article key={step.n} className="how-step">
              <span className="how-number">{step.n}</span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
