import { useEffect, useState } from "react";

// Typed entry that gets out of the way while you type.
//
// The earlier version validated on every keystroke and rewrote the field from
// the clamped number, which made whole values unreachable: clearing the box
// snapped it back, and "0.501" was rounded away at "0.5" before the rest could
// be typed. So the field now holds exactly what you typed, publishes a value
// upward only while it is inside the limits, and checks properly when you
// leave the field or press Enter.
//
// It is a text input rather than type="number" on purpose: a number input
// reports an empty string for a partially typed value like "0." , which is the
// other half of the same problem.

export interface Bound {
  value: number;
  /** Shown when a committed value is refused. Says the limit and why. */
  reason: string;
}

const NUMERIC = /^-?\d*\.?\d*$/;

export function NumberField({
  label,
  note,
  value,
  onChange,
  suffix,
  step = 1,
  lower,
  upper,
  asPercent = false,
  width = 116,
}: {
  label: string;
  note?: string;
  value: number;
  onChange: (next: number) => void;
  suffix?: string;
  step?: number;
  lower?: Bound;
  upper?: Bound;
  asPercent?: boolean;
  width?: number;
}) {
  const toText = (n: number) => {
    const shown = asPercent ? n * 100 : n;
    // Trims binary-float artefacts (20.000000000000004) without rounding away
    // anything the user actually typed.
    return String(Number(shown.toPrecision(12)));
  };
  const toValue = (text: string) => {
    const parsed = Number(text);
    return asPercent ? parsed / 100 : parsed;
  };

  const [draft, setDraft] = useState(() => toText(value));
  const [editing, setEditing] = useState(false);
  const [refused, setRefused] = useState<string | null>(null);

  // Follow the value when it changes elsewhere - a reset, or a neighbouring
  // band moving - but never while the field is being typed into.
  useEffect(() => {
    if (!editing) setDraft(toText(value));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, editing, asPercent]);

  const type = (text: string) => {
    if (text !== "" && !NUMERIC.test(text)) return;
    setDraft(text);
    setRefused(null);
    if (text === "" || text === "-" || text === "." || text === "-.") return;
    const next = toValue(text);
    if (!Number.isFinite(next)) return;
    // Publish only what is already legal. Anything outside the limits stays in
    // the box until the edit is finished, so a value can be typed through.
    if (lower && next < lower.value) return;
    if (upper && next > upper.value) return;
    onChange(next);
  };

  const commit = () => {
    setEditing(false);
    const text = draft.trim();
    const next = toValue(text);
    if (text === "" || !Number.isFinite(next)) {
      setDraft(toText(value));
      setRefused(null);
      return;
    }
    if (lower && next < lower.value) {
      onChange(lower.value);
      setDraft(toText(lower.value));
      setRefused(lower.reason);
      return;
    }
    if (upper && next > upper.value) {
      onChange(upper.value);
      setDraft(toText(upper.value));
      setRefused(upper.reason);
      return;
    }
    onChange(next);
    setDraft(toText(next));
    setRefused(null);
  };

  const nudge = (direction: 1 | -1) => {
    const base = Number.isFinite(toValue(draft)) && draft !== "" ? toValue(draft) : value;
    const moved = Number((base + direction * step).toPrecision(12));
    const clamped =
      lower && moved < lower.value
        ? lower.value
        : upper && moved > upper.value
          ? upper.value
          : moved;
    setDraft(toText(clamped));
    setRefused(null);
    onChange(clamped);
  };

  return (
    <div className={refused ? "field refused" : "field"}>
      <label className="field-label">
        {label}
        {note && <span className="field-note">{note}</span>}
        {refused && <span className="field-refused">{refused}</span>}
      </label>
      <span className="field-entry">
        <input
          type="text"
          inputMode="decimal"
          autoComplete="off"
          value={draft}
          style={{ width }}
          onFocus={() => setEditing(true)}
          onChange={(event) => type(event.target.value)}
          onBlur={commit}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              commit();
              (event.target as HTMLInputElement).blur();
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              nudge(1);
            } else if (event.key === "ArrowDown") {
              event.preventDefault();
              nudge(-1);
            }
          }}
        />
        <span className="field-suffix">{asPercent ? "%" : (suffix ?? "")}</span>
      </span>
    </div>
  );
}
