import type { Status } from "../App";
import { ArrowCircle, Sun } from "./Icons";
import { Progress } from "./Progress";
import { COMPANY, PRODUCT } from "./Shell";

const EXAMPLES = [
  { pincode: "380006", city: "Ahmedabad" },
  { pincode: "302001", city: "Jaipur" },
  { pincode: "110001", city: "New Delhi" },
  // Not 400001: Mumbai's Fort sits on a sea cell of the land-only grid.
  { pincode: "400051", city: "Mumbai" },
  { pincode: "560001", city: "Bengaluru" },
  { pincode: "700001", city: "Kolkata" },
];

/** Page one: what the cover is, and the one input it takes. */
export function InputPage({
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

  return (
    <section className="product-card" id="solution">
      <div className="product-hero">
        <div className="product-art" aria-hidden>
          <SolarScene />
        </div>

        <div className="product-panel">
          <span className="eyebrow">{COMPANY}</span>
          <h1>{PRODUCT}</h1>
          <p className="product-lede">
            Pays solar power owners automatically when a year's sunshine at
            their pincode falls short - no site visit, no claim forms.
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
            <button
              type="submit"
              className="btn-primary"
              disabled={draft.length !== 6 || (working && draft === active)}
            >
              <ArrowCircle size={20} />
              {working && draft === active ? "Pricing…" : "Get Premium"}
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

          {/* One slot below the input, so the card keeps its height - and
              the page its single screen - whatever state it is in. */}
          <div className="panel-slot">
            {status.name === "working" ? (
              <Progress status={status} />
            ) : status.name === "error" ? (
              <div className="alert" role="alert">
                <p>{status.message}</p>
                {status.retryable && active === draft && (
                  <button type="button" onClick={() => onSubmit(draft)}>
                    Try again
                  </button>
                )}
              </div>
            ) : (
              <div className="index-tile">
                <span className="index-icon">
                  <Sun size={30} />
                </span>
                <span className="index-label">Solar irradiance</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

/** A drawn stand-in for a photograph: sky, clouds, and a panel array rising
 *  across the frame. */
function SolarScene() {
  const W = 640;
  const H = 780;
  // The array's top edge runs from (0, topLeft) to (W, topRight).
  const topLeft = 600;
  const topRight = 430;
  const rows = 9;
  const cols = 11;
  const rowLines = Array.from({ length: rows }, (_, i) => {
    const t = (i + 1) / rows;
    return { y1: topLeft + (H - topLeft) * t, y2: topRight + (H - topRight) * t };
  });
  const colLines = Array.from({ length: cols }, (_, i) => {
    const x = ((i + 1) / (cols + 1)) * W;
    const yTop = topLeft + (topRight - topLeft) * (x / W);
    return { x1: x, y1: yTop, x2: x - 70 - i * 10, y2: H };
  });
  const cloud = (cx: number, cy: number, s: number, key: string) => (
    <g key={key} transform={`translate(${cx} ${cy}) scale(${s})`} filter="url(#soft)">
      <ellipse cx="0" cy="18" rx="92" ry="30" fill="#f4f1e4" />
      <circle cx="-44" cy="4" r="34" fill="#faf8ef" />
      <circle cx="0" cy="-18" r="46" fill="#ffffff" />
      <circle cx="46" cy="0" r="36" fill="#fbfaf2" />
      <ellipse cx="0" cy="34" rx="90" ry="14" fill="#dfe3dc" opacity="0.55" />
    </g>
  );

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid slice" className="scene">
      <defs>
        <filter id="soft" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="4" />
        </filter>
        <linearGradient id="sky" x1="0" y1="0" x2="0.35" y2="1">
          <stop offset="0" stopColor="#3f74b5" />
          <stop offset="0.45" stopColor="#7ea6cf" />
          <stop offset="1" stopColor="#d7e5ef" />
        </linearGradient>
        <linearGradient id="array" x1="0" y1="0" x2="0.25" y2="1">
          <stop offset="0" stopColor="#5d86c2" />
          <stop offset="0.45" stopColor="#2c56a0" />
          <stop offset="1" stopColor="#163a78" />
        </linearGradient>
        <linearGradient id="sheen" x1="0" y1="0" x2="1" y2="0.5">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.05" />
          <stop offset="0.5" stopColor="#ffffff" stopOpacity="0.3" />
          <stop offset="0.75" stopColor="#ffffff" stopOpacity="0" />
        </linearGradient>
      </defs>

      <rect width={W} height={H} fill="url(#sky)" />
      {cloud(470, 150, 1.05, "c1")}
      {cloud(150, 330, 1.25, "c2")}
      {cloud(560, 430, 0.9, "c3")}
      {cloud(290, 520, 0.7, "c4")}

      <polygon points={`0,${topLeft} ${W},${topRight} ${W},${H} 0,${H}`} fill="url(#array)" />
      <g stroke="#e2ecf7" strokeOpacity="0.6" strokeWidth="1.3">
        {rowLines.map((line, i) => (
          <line key={`r${i}`} x1={0} y1={line.y1} x2={W} y2={line.y2} />
        ))}
        {colLines.map((line, i) => (
          <line key={`c${i}`} {...line} />
        ))}
      </g>
      <line x1={0} y1={topLeft + 100} x2={W} y2={topRight + 60} stroke="#1c1c1c" strokeWidth="5" />
      <polygon points={`0,${topLeft} ${W},${topRight} ${W},${H} 0,${H}`} fill="url(#sheen)" />
      <line x1={0} y1={topLeft} x2={W} y2={topRight} stroke="#f1f5fa" strokeWidth="3" />
    </svg>
  );
}
