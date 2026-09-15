import type { Status } from "../App";
import { POLICY } from "../api";

const STAGES = ["Locate", "Read 20 years", "Price"];

export function Progress({
  status,
  tone = "light",
}: {
  status: Extract<Status, { name: "working" }>;
  /** "light" sits on the slate-blue panel, "plain" on a white card. */
  tone?: "light" | "plain";
}) {
  const share = (status.step + (status.step === 1 ? status.progress : 0)) / STAGES.length;
  return (
    <div className={`progress ${tone}`} role="status" aria-live="polite">
      <ol className="progress-steps">
        {STAGES.map((label, index) => (
          <li
            key={label}
            className={index < status.step ? "done" : index === status.step ? "current" : undefined}
          >
            {label}
          </li>
        ))}
      </ol>
      <div className="progress-bar">
        <span style={{ width: `${Math.round(share * 100)}%` }} />
      </div>
      <p>{status.message}</p>
      {status.step === 1 && (
        <p className="progress-note">
          The first look-up for a pincode reads every day of weather since{" "}
          {POLICY.startYear}, so it can take a minute.
        </p>
      )}
    </div>
  );
}
