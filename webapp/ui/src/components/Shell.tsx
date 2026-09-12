import type { ReactNode } from "react";

// The frame every screen sits in. A masthead that always says what this is
// and where you are, and a footer that credits the two datasets the whole
// product depends on - both are licence conditions as much as decoration.

export function Mark() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden className="mark">
      <circle cx="13" cy="13" r="5.5" fill="var(--accent)" />
      {Array.from({ length: 8 }, (_, i) => {
        const angle = (i * Math.PI) / 4;
        return (
          <line
            key={i}
            x1={13 + Math.cos(angle) * 8}
            y1={13 + Math.sin(angle) * 8}
            x2={13 + Math.cos(angle) * 11}
            y2={13 + Math.sin(angle) * 11}
            stroke="var(--accent)"
            strokeWidth="2"
            strokeLinecap="round"
            opacity={0.55}
          />
        );
      })}
    </svg>
  );
}

export function Shell({
  context,
  actions,
  children,
}: {
  /** Where the user is, shown in the masthead once a pincode is resolved. */
  context?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="shell">
      <header className="masthead">
        <div className="masthead-inner">
          <div className="brand">
            <Mark />
            <div>
              <div className="brand-name">Parametric Solar Cover</div>
              <div className="brand-sub">Weather-index pricing workbench</div>
            </div>
          </div>
          {context && <div className="masthead-context">{context}</div>}
          {actions && <div className="masthead-actions">{actions}</div>}
        </div>
      </header>

      <main className="shell-main">{children}</main>

      <footer className="foot">
        <div className="foot-inner">
          <div>
            <strong>Weather data</strong>
            <p>
              ERA5-Land daily aggregates, Copernicus Climate Change Service,
              via Google Earth Engine. Settlement reads the grid cell, not the
              roof.
            </p>
          </div>
          <div>
            <strong>Boundaries</strong>
            <p>
              India Post pincode areas from data.gov.in via bharatlas
              (GODL-India). Voronoi approximations, not surveyed.
            </p>
          </div>
          <div>
            <strong>Method</strong>
            <p>
              Burn cost over the years you select, plus a standard-deviation
              risk margin, grossed up for expenses and profit.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export function LocationChip({
  pincode,
  office,
  lat,
  lon,
}: {
  pincode: string;
  office?: string;
  lat: number;
  lon: number;
}) {
  return (
    <div className="chip">
      <span className="chip-dot" />
      <span>
        <strong>{pincode}</strong>
        {office ? ` · ${office}` : ""}
      </span>
      <span className="chip-coords">
        {lat.toFixed(3)}°N, {lon.toFixed(3)}°E
      </span>
    </div>
  );
}
