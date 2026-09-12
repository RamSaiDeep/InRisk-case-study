// The session is remembered between visits.
//
// Everything here is a decision the user made, so losing it on a refresh is
// pure cost. The cached weather data already survives on the server; this is
// the other half. Bumping VERSION discards snapshots written by an older
// shape rather than trying to migrate them.

import type { Inputs, LocationResponse, Unit } from "./types";

const KEY = "pricing-workbench-session";
const VERSION = 1;

export interface Session {
  version: number;
  pincode: string;
  location: LocationResponse | null;
  /** "steps" resumes mid-flow; "workspace" resumes at the result. */
  stage: "entry" | "confirm" | "steps" | "workspace";
  step: number;
  /** True once the flow has been completed at least once. */
  completed: boolean;
  years: { start: number; end: number } | null;
  unit: Unit;
  units: number;
  tariff: number;
  bands: Pick<Inputs, "boundary_sigmas" | "payout_sigmas">;
  loadings: Pick<Inputs, "risk_coeff" | "expense_pct" | "profit_pct">;
}

export function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Session;
    if (parsed.version !== VERSION) return null;
    // A fetch in flight cannot be resumed: job state lives in the server's
    // memory and does not survive a restart, so that stage falls back to the
    // confirmation screen, where the fetch can simply be started again.
    return parsed;
  } catch {
    return null;
  }
}

export function saveSession(session: Omit<Session, "version">): void {
  try {
    localStorage.setItem(KEY, JSON.stringify({ ...session, version: VERSION }));
  } catch {
    // A full or blocked store is not worth interrupting the user for.
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
