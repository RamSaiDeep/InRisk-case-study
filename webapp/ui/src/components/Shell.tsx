import { ArrowCircle } from "./Icons";

// The frame every page sits in, and a footer crediting the two datasets the
// product depends on - licence conditions as much as decoration.

export const COMPANY = "InRisk Labs";
export const PRODUCT = "Solar Yield Cover Solution";

function Brand({ onHome }: { onHome?: () => void }) {
  return (
    <a
      className="brand"
      href="./"
      aria-label={`${COMPANY} ${PRODUCT} home`}
      onClick={(event) => {
        if (!onHome) return;
        event.preventDefault();
        onHome();
      }}
    >
      <span className="brand-text">
        <span className="brand-name">{COMPANY}</span>
        <span className="brand-product">{PRODUCT}</span>
      </span>
    </a>
  );
}

export function Header({
  page,
  onHome,
}: {
  page: "input" | "policy";
  onHome: () => void;
}) {
  return (
    <header className="masthead">
      <div className="container masthead-inner">
        <Brand onHome={onHome} />
        {page === "policy" && (
          <nav className="nav" aria-label="Sections">
            <a href="#policy">Your Policy</a>
            <a href="#scale">Scale</a>
            <a href="#how">How it Works</a>
          </nav>
        )}
        {page === "policy" ? (
          <button type="button" className="btn-primary" onClick={onHome}>
            <ArrowCircle size={20} />
            Check Another Pincode
          </button>
        ) : (
          <button
            type="button"
            className="btn-primary"
            onClick={() => document.getElementById("pincode")?.focus()}
          >
            <ArrowCircle size={20} />
            Get Your Premium
          </button>
        )}
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="foot">
      <div className="container">
        <div className="foot-top">
          <div className="foot-brand">
            <Brand />
            <p>
              Parametric protection for solar power production, priced for
              any pincode in India.
            </p>
          </div>
          <div>
            <strong>Weather data</strong>
            <p>
              ERA5-Land daily aggregates, Copernicus Climate Change Service,
              via Google Earth Engine.
            </p>
          </div>
          <div>
            <strong>Pincode boundaries</strong>
            <p>
              India Post pincode areas from data.gov.in via bharatlas
              (GODL-India).
            </p>
          </div>
        </div>
        <div className="foot-bottom">
          <span>
            {COMPANY} · {PRODUCT} - case study prototype
          </span>
          <span>Illustrative pricing - not an offer of insurance.</span>
        </div>
      </div>
    </footer>
  );
}
