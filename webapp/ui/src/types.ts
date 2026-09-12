// Mirrors api/schemas.py. The backend is the single source of these numbers -
// nothing here recomputes any part of the model.

export interface Coordinate {
  lat: number;
  lon: number;
}

export interface LocationResponse {
  pincode: string;
  centroid: Coordinate;
  pixel: Coordinate;
  /** Outer ring as [lon, lat] pairs, simplified for drawing only. */
  outline: [number, number][];
  /** ERA5-Land grid step in degrees, for drawing the cell around the pixel. */
  cell_deg: number;
  attributes: Record<string, string>;
  cached: boolean;
}

export interface SeriesYear {
  year: number;
  days: number;
  sunlight_sum: number;
}

export interface SeriesResponse {
  pincode: string;
  rows: number;
  first_day: string;
  last_day: string;
  years: SeriesYear[];
  daily: { date: string; ssrd_j_m2: number; ssrd_kwh_m2: number }[];
  offset: number;
  limit: number;
}

/** One panel installation. The policy insures a number of identical units;
 *  capacity and expected generation scale with the count, the performance
 *  ratio does not. */
export interface Unit {
  capacity_kw: number;
  pr: number;
  aep50: number;
}

export interface DataResponse {
  status: "ready" | "fetching";
  pincode: string;
  job_id: string | null;
  rows: number | null;
}

export interface JobResponse {
  job_id: string;
  pincode: string;
  start_year: number;
  end_year: number;
  status: "pending" | "running" | "done" | "error";
  progress: number;
  message: string;
  rows: number | null;
  error: string | null;
}

/** The engine's input contract, one field for one field. */
export interface Inputs {
  capacity_kw: number;
  pr: number;
  aep50: number;
  tariff: number;
  boundary_sigmas: number[];
  payout_sigmas: number[];
  risk_coeff: number;
  expense_pct: number;
  profit_pct: number;
}

export interface BacktestRow {
  year: number;
  days: number;
  sunlight_sum: number;
  index: number;
  generation: number;
  level: number;
  payout: number;
  nearest_edge: number;
  distance_to_edge: number;
}

export interface Bands {
  sigma: number;
  trigger: number;
  boundaries: number[];
  payouts: number[];
  exit_level: number;
  max_payout: number;
}

export interface Premium {
  burn_cost: number;
  payout_sigma: number;
  risk_margin: number;
  technical_premium: number;
  gross_premium: number;
}

export interface Summary {
  years: number;
  years_triggering: number;
  trigger_frequency: number;
  average_payout_when_paying: number | null;
  worst_year: number | null;
  worst_year_payout: number | null;
  level_year_counts: Record<string, number>;
  mean_generation: number;
  mean_generation_vs_trigger: number;
  mean_generation_sigmas_from_trigger: number;
  closest_call_year: number | null;
  closest_call_distance: number | null;
}

export interface PriceResponse {
  pincode: string;
  start_year: number;
  end_year: number;
  backtest: BacktestRow[];
  bands: Bands;
  premium: Premium;
  summary: Summary;
}

export interface ApiErrorBody {
  detail: string;
  kind: string;
}

/** Labels for the N paying levels. Level 0 is "no payout". */
export const LEVEL_NAMES = ["None", "Mild", "Moderate", "Severe"] as const;

export function levelName(level: number, levels: number): string {
  if (level === 0) return "None";
  if (levels === 3) return LEVEL_NAMES[level] ?? `Level ${level}`;
  return `Level ${level}`;
}
