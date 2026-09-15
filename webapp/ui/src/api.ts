// The only module that talks to the backend. Every error arrives in the same
// {detail, kind} shape, so callers branch on `kind`, never on a status code.

import type {
  DataResponse,
  Inputs,
  JobResponse,
  LocationResponse,
  PriceResponse,
} from "./types";

export class ApiError extends Error {
  constructor(
    readonly kind: string,
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  if (!response.ok) {
    let kind = "unknown";
    let detail = `HTTP ${response.status}`;
    try {
      const parsed = await response.json();
      kind = parsed.kind ?? kind;
      detail = parsed.detail ?? detail;
    } catch {
      // A non-JSON body means something other than our app answered.
    }
    throw new ApiError(kind, detail, response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  resolveLocation: (pincode: string) =>
    request<LocationResponse>("/api/location", { pincode }),

  requestData: (pincode: string, start_year: number, end_year: number) =>
    request<DataResponse>("/api/data", { pincode, start_year, end_year }),

  jobStatus: (jobId: string) => request<JobResponse>(`/api/jobs/${jobId}`),

  price: (
    pincode: string,
    start_year: number,
    end_year: number,
    inputs: Inputs,
    signal?: AbortSignal,
  ) =>
    request<PriceResponse>(
      "/api/price",
      { pincode, start_year, end_year, inputs },
      signal,
    ),
};

/** The contract, fixed. These are the submitted workbook's terms - one 3 kVA
 *  rooftop at 380006 prices to exactly its ₹137.48 - and the only thing a
 *  visitor changes is where the rooftop is. */
export const POLICY = {
  startYear: 2005,
  endYear: 2024,
  inputs: {
    capacity_kw: 3.0,
    pr: 0.8,
    aep50: 4600,
    tariff: 5.75,
    boundary_sigmas: [0.5, 1.0],
    payout_sigmas: [0.25, 0.75, 1.25],
    risk_coeff: 0.2,
    expense_pct: 0.2,
    profit_pct: 0.075,
  } satisfies Inputs,
};

/** Bundled with the pincode boundary index the backend resolves against. */
export const PINCODE_COUNT = 19312;
