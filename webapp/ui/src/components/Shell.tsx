// The frame every screen sits in: who built it, what it is, and a footer that
// credits the two datasets the product depends on - licence conditions as
// much as decoration.

export const PRODUCT = "HelioCover";
export const OWNER = "Ram Sai Deep Vinjamuri";

export function Mark({ size = 34 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden className="mark">
      <defs>
        <linearGradient id="mark-sun" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#f7c948" />
          <stop offset="1" stopColor="#f08c2e" />
        </linearGradient>
        <linearGradient id="mark-panel" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1f5fbf" />
          <stop offset="1" stopColor="#003a8c" />
        </linearGradient>
      </defs>
      <circle cx="20" cy="20" r="19" fill="#eef4fa" />
      <circle cx="24" cy="15" r="6.5" fill="url(#mark-sun)" />
      <path d="M6 30 L16 21 H34 L26 30 Z" fill="url(#mark-panel)" />
      <path d="M11 25.5 H30 M21 21 L16 30" stroke="#eef4fa" strokeWidth="1.1" />
    </svg>
  );
}

export function Header() {
  return (
    <header className="masthead">
      <div className="container masthead-inner">
        <a className="brand" href="./" aria-label={`${PRODUCT} home`}>
          <Mark />
          <span className="brand-text">
            <span className="brand-name">{PRODUCT}</span>
            <span className="brand-owner">by {OWNER}</span>
          </span>
        </a>
        <nav className="nav" aria-label="Sections">
          <a href="#how">How it works</a>
          <a
            className="cta"
            href="#price"
            onClick={() => document.getElementById("pincode")?.focus({ preventScroll: true })}
          >
            Price a pincode
          </a>
        </nav>
      </div>
    </header>
  );
}

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="foot">
      <div className="container">
        <div className="foot-top">
          <div className="foot-brand">
            <div className="brand">
              <Mark size={30} />
              <span className="brand-text">
                <span className="brand-name">{PRODUCT}</span>
                <span className="brand-owner">by {OWNER}</span>
              </span>
            </div>
            <p>
              A weather-index cover against a below-normal year of sunshine,
              priced for any Indian pincode from public satellite-era data.
            </p>
          </div>
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
        </div>
        <div className="foot-bottom">
          <span>
            © {year} {OWNER}. {PRODUCT} is designed, modelled and built by{" "}
            {OWNER}. All rights reserved.
          </span>
          <span>Illustrative pricing - not an offer of insurance.</span>
        </div>
      </div>
    </footer>
  );
}
