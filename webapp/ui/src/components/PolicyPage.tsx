import type { Status } from "../App";
import { POLICY } from "../api";
import { Sun } from "./Icons";
import { PolicyDetails, placeName } from "./Policy";
import { Progress } from "./Progress";
import { HowItWorks, Scale } from "./Sections";
import { COMPANY, PRODUCT } from "./Shell";

/** Page two: the policy for one pincode, its premium at scale, and how the
 *  price was reached. Opened directly from a link, it prices on arrival. */
export function PolicyPage({
  pincode,
  status,
  onBack,
}: {
  pincode: string;
  status: Status;
  onBack: () => void;
}) {
  const ready = status.name === "ready";

  return (
    <>
      <nav className="crumbs" aria-label="Breadcrumb">
        <a
          href="./"
          onClick={(event) => {
            event.preventDefault();
            onBack();
          }}
        >
          ← {PRODUCT}
        </a>
        <span aria-hidden>/</span>
        <span>Pincode {pincode}</span>
      </nav>

      <section className="product-card" id="policy">
        <div className="policy-banner">
          <div>
            <span className="eyebrow">
              {COMPANY} · {PRODUCT}
            </span>
            <h1>Your Policy</h1>
            <p>
              {ready
                ? `One ${POLICY.inputs.capacity_kw} kVA solar unit at ${placeName(status.location)}, priced on ${POLICY.startYear}–${POLICY.endYear} weather.`
                : `Preparing the policy for pincode ${pincode}.`}
            </p>
          </div>
          <div className="banner-side">
            <div className="banner-pin">
              <span className="index-label">Pincode</span>
              <strong>{pincode}</strong>
            </div>
            <div className="index-tile">
              <span className="index-icon">
                <Sun size={30} />
              </span>
              <span className="index-label">Solar irradiance</span>
            </div>
          </div>
        </div>

        {status.name === "working" && (
          <div className="col">
            <Progress status={status} tone="plain" />
          </div>
        )}
        {status.name === "error" && (
          <div className="col">
            <div className="alert plain" role="alert">
              <p>{status.message}</p>
              <button type="button" onClick={onBack}>
                Check another pincode
              </button>
            </div>
          </div>
        )}
        {ready && <PolicyDetails location={status.location} result={status.result} />}
      </section>

      {ready && <Scale result={status.result} />}
      <HowItWorks />
    </>
  );
}
