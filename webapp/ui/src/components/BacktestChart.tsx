import { useEffect, useState } from "react";
import type { BacktestRow, Bands } from "../types";
import { levelName } from "../types";

// Columns are anchored at the trigger, not at zero: the question the chart
// answers is "how far below the promised generation did this year fall", and a
// zero baseline would squeeze twenty years of 4,500-4,800 kWh into a sliver.
//
// Severity is ordered, so a single-hue ramp is the textbook choice - but
// stepping one hue three ways put adjacent bands at deltaE 14.4 for normal
// vision, under the 15 floor, and they were genuinely hard to tell apart.
// These are distinct hues that still read as escalating (calm -> warning ->
// alarm), validated as an adjacent set in both modes: worst pair deltaE 20.8
// light, 19.3 dark, and clear of every colour-vision gate.
const LEVEL_RAMP = [
  "var(--level-1)",
  "var(--level-2)",
  "var(--level-3)",
  "var(--level-4)",
  "var(--level-5)",
];

// Two geometries rather than one scaled one. A 900-unit viewBox squeezed into
// a 390px phone renders its 10.5px labels at about 4.5px, which is why the
// narrow layout gets a smaller coordinate space, a thinner left gutter, and no
// right-hand label column at all - the band lines are labelled in place.
const WIDE = { w: 900, h: 340, pad: { top: 18, right: 96, bottom: 34, left: 62 }, font: 10.5 };
const NARROW = { w: 380, h: 300, pad: { top: 24, right: 10, bottom: 30, left: 44 }, font: 9 };

function useNarrow(): boolean {
  const query = "(max-width: 760px)";
  const [narrow, setNarrow] = useState(
    () => typeof window !== "undefined" && window.matchMedia(query).matches,
  );
  useEffect(() => {
    const media = window.matchMedia(query);
    const update = () => setNarrow(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return narrow;
}

function levelColor(level: number): string {
  if (level === 0) return "var(--level-0)";
  return LEVEL_RAMP[Math.min(level - 1, LEVEL_RAMP.length - 1)];
}

export function BacktestChart({
  backtest,
  bands,
  levels,
}: {
  backtest: BacktestRow[];
  bands: Bands;
  levels: number;
}) {
  const [hover, setHover] = useState<BacktestRow | null>(null);
  const narrow = useNarrow();
  const { w: W, h: H, pad: PAD, font: FONT } = narrow ? NARROW : WIDE;

  if (backtest.length === 0) return null;

  const edges = [bands.trigger, ...bands.boundaries];
  const values = backtest.map((r) => r.generation);
  const lowest = Math.min(...values, ...edges);
  const highest = Math.max(...values, bands.trigger);
  const span = highest - lowest || 1;
  const yMin = lowest - span * 0.12;
  const yMax = highest + span * 0.12;

  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const y = (v: number) => PAD.top + ((yMax - v) / (yMax - yMin)) * plotH;
  const step = plotW / backtest.length;
  const colW = Math.min(narrow ? 14 : 26, step * 0.55);
  const x = (i: number) => PAD.left + step * (i + 0.5);

  // A cliff-edge year: closer to a band edge than a tenth of a standard
  // deviation, i.e. a near-identical year would have been paid differently.
  const nearThreshold = bands.sigma * 0.1;
  const triggerY = y(bands.trigger);

  // Band regions, least severe first, drawn as faint washes so the columns
  // stay the loudest thing on the plot.
  const regions = edges.map((top, index) => {
    const bottom = index + 1 < edges.length ? edges[index + 1] : yMin;
    return { top, bottom, level: index + 1 };
  });

  const ticks = 4;
  const tickValues = Array.from(
    { length: ticks + 1 },
    (_, i) => yMin + ((yMax - yMin) * i) / ticks,
  );

  return (
    <div className="chart-wrap">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-label={`Modelled generation by year against the trigger of ${bands.trigger.toFixed(0)} kWh`}
        style={{ display: "block", overflow: "visible" }}
      >
        {regions.map((region) => (
          <rect
            key={region.level}
            x={PAD.left}
            y={y(region.top)}
            width={plotW}
            height={Math.max(0, y(region.bottom) - y(region.top))}
            fill={levelColor(region.level)}
            opacity={0.07}
          />
        ))}

        {tickValues.map((value) => (
          <g key={value}>
            <line
              x1={PAD.left}
              x2={PAD.left + plotW}
              y1={y(value)}
              y2={y(value)}
              stroke="var(--gridline)"
              strokeWidth={1}
            />
            <text
              x={PAD.left - 8}
              y={y(value) + 3.5}
              textAnchor="end"
              fontSize={FONT}
              fill="var(--ink-muted)"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {value.toFixed(0)}
            </text>
          </g>
        ))}

        {edges.map((edge, index) => (
          <g key={edge}>
            <line
              x1={PAD.left}
              x2={PAD.left + plotW}
              y1={y(edge)}
              y2={y(edge)}
              stroke={index === 0 ? "var(--ink-secondary)" : "var(--baseline)"}
              strokeWidth={index === 0 ? 1.5 : 1}
            />
            <text
              x={narrow ? PAD.left + 3 : PAD.left + plotW + 8}
              y={narrow ? y(edge) - 3 : y(edge) + 3.5}
              fontSize={FONT}
              fill="var(--ink-secondary)"
              // Inside the plot these labels can land on a column, so they
              // carry a surface-coloured halo rather than a background box.
              stroke={narrow ? "var(--surface-1)" : undefined}
              strokeWidth={narrow ? 3 : undefined}
              style={narrow ? { paintOrder: "stroke" } : undefined}
            >
              {index === 0
                ? `Trigger ${edge.toFixed(0)}`
                : index === edges.length - 1
                  ? `Exit ${edge.toFixed(0)}`
                  : `${edge.toFixed(0)}`}
            </text>
          </g>
        ))}

        {backtest.map((row, index) => {
          const top = Math.min(y(row.generation), triggerY);
          const height = Math.abs(y(row.generation) - triggerY);
          const near = row.distance_to_edge < nearThreshold;
          const active = hover?.year === row.year;
          return (
            <g key={row.year}>
              {/* Hit area: wider than the column so hovering is forgiving. */}
              <rect
                x={x(index) - step / 2}
                y={PAD.top}
                width={step}
                height={plotH}
                fill="transparent"
                onMouseEnter={() => setHover(row)}
                onMouseLeave={() => setHover(null)}
                tabIndex={0}
                onFocus={() => setHover(row)}
                onBlur={() => setHover(null)}
              />
              <rect
                x={x(index) - colW / 2}
                y={top}
                width={colW}
                height={Math.max(height, 1.5)}
                rx={3}
                fill={levelColor(row.level)}
                opacity={active ? 1 : 0.92}
              />
              {near && (
                <circle
                  cx={x(index)}
                  cy={y(row.generation)}
                  r={narrow ? 3.5 : 4.5}
                  fill={levelColor(row.level)}
                  stroke="var(--surface-1)"
                  strokeWidth={2}
                />
              )}
              {(!narrow || index % 2 === 0 || active) && (
                <text
                  x={x(index)}
                  y={H - PAD.bottom + 13}
                  textAnchor="middle"
                  fontSize={narrow ? 8.5 : 10}
                  fill={active ? "var(--ink-primary)" : "var(--ink-muted)"}
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {`'${String(row.year).slice(2)}`}
                </text>
              )}
            </g>
          );
        })}

        {/* One selective direct label: the year that came closest to an edge.
            Dropped on a phone, where it would collide with the band lines. */}
        {!narrow && (() => {
          const closest = backtest.reduce((a, b) =>
            a.distance_to_edge <= b.distance_to_edge ? a : b,
          );
          const index = backtest.indexOf(closest);
          const above = closest.generation >= closest.nearest_edge;
          // Near the right edge the label would run into the threshold
          // gutter, so it flips to sit left of its column instead.
          const nearRightEdge = index > backtest.length - 4;
          return (
            <text
              x={x(index) + (nearRightEdge ? -colW : 0)}
              y={y(closest.generation) + (above ? -12 : 20)}
              textAnchor={nearRightEdge ? "end" : "middle"}
              fontSize={10.5}
              fill="var(--ink-secondary)"
              stroke="var(--surface-1)"
              strokeWidth={4}
              style={{ paintOrder: "stroke" }}
            >
              {closest.distance_to_edge.toFixed(0)} kWh from the next band
            </text>
          );
        })()}
      </svg>

      {hover && (
        <div
          className="chart-tooltip"
          style={{
            left: `${((x(backtest.indexOf(hover)) + 14) / W) * 100}%`,
            top: 10,
          }}
        >
          <strong>{hover.year}</strong>
          <dl>
            <div className="stat">
              <dt>Generation</dt>
              <dd>{hover.generation.toFixed(0)} kWh</dd>
            </div>
            <div className="stat">
              <dt>Band</dt>
              <dd>{levelName(hover.level, levels)}</dd>
            </div>
            <div className="stat">
              <dt>Payout</dt>
              <dd>{hover.payout === 0 ? "—" : `₹${hover.payout.toFixed(2)}`}</dd>
            </div>
            <div className="stat">
              <dt>To next band</dt>
              <dd>{hover.distance_to_edge.toFixed(0)} kWh away</dd>
            </div>
          </dl>
        </div>
      )}

      <div className="legend" style={{ marginTop: 10 }}>
        {Array.from({ length: levels + 1 }, (_, level) => (
          <span className="legend-item" key={level}>
            <span className="swatch" style={{ background: levelColor(level) }} />
            {levelName(level, levels)}
          </span>
        ))}
        <span className="legend-item">
          <svg width={12} height={12} aria-hidden>
            <circle
              cx={6}
              cy={6}
              r={4}
              fill="var(--ink-muted)"
              stroke="var(--surface-1)"
              strokeWidth={2}
            />
          </svg>
          close to a band boundary
        </span>
      </div>
    </div>
  );
}
