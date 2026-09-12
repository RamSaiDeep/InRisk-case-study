# Solar Shortfall Cover — Function Design Reference

Everything designed so far, organized by layer. No implementation —
this is the contract each function is expected to honor once built.

---

## 1. Data Layer

The only layer that touches the network (bharatlas + Google Earth
Engine). Split into two speeds: resolving *where* a pincode is
(fast, seconds) and pulling *20 years of weather data* for it (slow,
tens of seconds to minutes) — kept as separate paths throughout.

### Location resolution (fast path)

| Function | In | Out | Purpose |
|---|---|---|---|
| `get_pincode_centroid` | pincode | (lon, lat) | Looks up the pincode's boundary polygon (bharatlas, queried remotely without downloading the full dataset) and returns its centroid. |
| `snap_to_era5_pixel` | (lon, lat) | (lon, lat) | Snaps any coordinate to the center of the ERA5-Land grid cell containing it. |
| `resolve_location` | pincode | centroid + pixel coords | Orchestrator. Chains the two above; checks cache first so a repeat call for the same pincode is free. Cached independently of whether a full data fetch ever happens. |

### Data pull (slow path)

| Function | In | Out | Purpose |
|---|---|---|---|
| `download_ssrd_year` | pixel (lat, lon), year | one year of daily readings | Pulls a single year. Isolated so progress can be reported year-by-year and a failed year doesn't force re-pulling the whole range. |
| `download_ssrd` | pixel, start_year, end_year, progress callback | full daily series | Loops the per-year function across the requested range, reporting progress as it goes. |
| `get_or_fetch_ssrd` | pincode, start_year, end_year | daily series | **The one entry point everything else should call.** Checks cache coverage first; only touches bharatlas/GEE if the range isn't already cached. |

### Cache store

| Function | In | Out | Purpose |
|---|---|---|---|
| `load_metadata` / `save_metadata` | — / metadata dict | metadata dict / — | Read/write the small index tracking which pincodes are cached and what year range each covers. |
| `get_cache_entry` | pincode | metadata entry or none | Look up one pincode's cache status. |
| `covers_range` | pincode, start_year, end_year | true/false | Answers "do I need to fetch anything?" without opening the actual data file. |
| `read_cached_df` | pincode | daily series or none | Reads the cached daily data for one pincode. |
| `write_cache` | pincode, daily series, resolved location, year range | — | Persists a successful fetch: the data file plus its metadata entry. |
| `save_resolved_location` | pincode, centroid, pixel | — | Persists just the location resolution, independent of whether data has been fetched yet. |

### Background job manager

| Function | In | Out | Purpose |
|---|---|---|---|
| `start_fetch_job` | pincode, year range | job_id | Kicks off a background fetch (via `get_or_fetch_ssrd`) on a worker thread, so the slow GEE pull never blocks a request. |
| `get_status` | job_id | status (pending/running/done/error), progress, message | Pollable status for the frontend's loading indicator. |

**Settled scope decisions:** no partial-year handling — the app never
requests or ingests an incomplete calendar year in the first place.
No deduplication of concurrent fetch requests for the same pincode.
Single-process, single-instance only (in-memory job state, file-based
cache) — deliberately not designed for multiple backend instances
running at once, since that would need shared state (e.g. a real
database) that this sample app doesn't need.

---

## 2. Pricing Engine

Pure functions only — no file reads, no network, no cache lookups.
Everything takes data in, returns data out, which is what makes it
recomputable on every slider change at effectively zero cost.

### Step 1 — Annual index

| Function | In | Out | Purpose |
|---|---|---|---|
| `group_by_year` | daily series | one row per year: day count, raw summed irradiance | Pure grouping, no judgment calls. |
| `normalize_year` | one year's sum, day count | one normalized index value | The 365-day leap-year correction — the one methodology decision in this step. Scalar, so it's directly checkable against a known report value. |
| `compute_annual_index` | daily series | full annual table (year, days, sum, index) | Orchestrator — the only function anything downstream calls. |

### Step 2 — Modelled generation

| Function | In | Out | Purpose |
|---|---|---|---|
| `model_year_generation` | one year's index, PR, capacity | one generation value (kWh) | The physical formula: `index × PR × capacity`. The entire methodology decision from the submitted report lives in this one function. |
| `apply_generation` | annual index table, PR, capacity | table with generation column added | Orchestrator. |

*(AEP50 does not enter this step at all — it's taken directly as a user input and flows straight through as the trigger value for the next step, never derived or compared against modelled generation.)*

### Step 3 — Bands and payouts (generalized to N user-defined levels)

| Function | In | Out | Purpose |
|---|---|---|---|
| `compute_sigma` | generation series | one number | Standard deviation of modelled generation. Computed once, shared by both boundaries and payouts below — never recomputed independently in two places. |
| `compute_level_boundaries` | trigger, σ, list of N−1 boundary σ-multiples | N−1 kWh boundaries | Must validate the σ-multiples are strictly increasing — an out-of-order list would silently create overlapping/inverted bands. |
| `compute_level_payouts` | σ, tariff, list of N payout σ-points | N fixed ₹ amounts | One per level. No ordering constraint — a user may deliberately want a non-increasing payout curve. |
| `assign_year_level_payout` | one year's generation, trigger, boundaries, payouts | (level, payout) for that year | Scalar. Walks boundaries least-severe to most-severe; this is the function you'd test directly against a known boundary value to confirm which side of a cliff-edge a year falls on. |
| `apply_bands` | generation table, trigger, tariff, boundary list, payout list | full table with level + payout columns | Orchestrator — calls `compute_sigma` once and threads it into both boundary and payout computation. |

### Step 4 — Premium

| Function | In | Out | Purpose |
|---|---|---|---|
| `compute_burn_cost` | payout series | one number | Mean payout across all years — the "honest, no-margin cost of the risk." |
| `compute_payout_sigma` | payout series | one number | Standard deviation of payout, feeds the risk margin only. |
| `compute_risk_margin` | payout σ, risk coefficient | one ₹ number | Standard-deviation premium principle. |
| `gross_up` | burn cost, risk margin, expense %, profit % | technical premium, gross premium | Must validate expense % + profit % < 1. Returns both intermediate and final numbers so a premium waterfall can render every step. |
| `compute_premium` | payout series, risk coefficient, expense %, profit % | full premium breakdown | Orchestrator. |

### Step 5 — Summary stats (kept separate from premium on purpose)

| Function | In | Out | Purpose |
|---|---|---|---|
| `compute_summary_stats` | full backtest table | years triggering, frequency, average payout when paying, worst year, per-level year counts | Answers "how often and how badly does this pay" — a different question from "what should this cost," even though both read the same payout series. |

### Top-level orchestrator

| Function | In | Out | Purpose |
|---|---|---|---|
| `price` | daily series, full input contract | one bundled result: backtest table, boundaries, payouts, premium breakdown, summary stats | The single entry point the API calls. Owns only sequencing — no formula lives here. |

**The input contract** this all runs on: `capacity_kw`, `pr`, `aep50`
(trigger, taken as given), `tariff`, `boundary_sigmas` (list, length
N−1), `payout_sigmas` (list, length N), `risk_coeff`, `expense_pct`,
`profit_pct`.

---

## 3. API Layer

Thin wrappers only — every route calls exactly one thing from the
layers above and translates its result or error into HTTP. No
business logic should live here.

| Endpoint | Calls | Purpose |
|---|---|---|
| `POST /api/location` | `resolve_location` | Fast confirmation step — shows the resolved pixel before committing to a slow fetch. |
| `POST /api/data` | cache check, then `start_fetch_job` if needed | Returns immediately with either "ready" or a job_id to poll. |
| `GET /api/jobs/{job_id}` | `get_status` | Pollable progress for the fetching screen. |
| `POST /api/price` | `price` | The endpoint that fires on every input change. Never touches bharatlas/GEE — fails clearly if the pincode isn't cached yet, rather than fetching on the fly. |
| `GET /api/export/xlsx`, `GET /api/export/report` | `price`, then a formatter | Same result object as `/api/price`, rendered to a file instead of a screen. |

**Error mapping**, the one HTTP-specific responsibility this layer
owns: pincode not found → 404; upstream schema changed → 502; server
misconfigured → 500; priced before data was fetched → 409; invalid
input (bad slider state) → 422.

---

## A short note on how pricing workbenches like this tend to look

Across actuarial rating engines, derivatives pricing terminals, and
SaaS pricing calculators, a few patterns recur consistently:

- **Levers on one side, live output on the other** — inputs and
  results kept in visually separate zones that update together. Close
  to universal in this category.
- **Nothing requires a "run" button** — modern tools recalculate the
  instant a lever moves, rather than requiring an explicit
  calculate step.
- **A distinction between exploring and committing** — dragging
  sliders is cheap and reversible, but there's usually a separate,
  deliberate action (saving a scenario, locking a quote) that marks
  one particular configuration as "the one." Worth deciding whether
  export alone serves that role here, or whether a separate "save
  this scenario" action is warranted later.

Three patterns common in the category that go beyond what we've
designed, worth knowing about even if not building them now:
**scenario comparison** (holding two or three named parameter sets
side by side — maps naturally onto this product, since the submitted
report already thinks in named variants); a **sensitivity/tornado
view** (automating what the report's sensitivity section did by
hand — which input moves the premium most); and **saved presets**
for the judgment-call inputs (risk coefficient, band placement)
separate from the fixed contract facts (capacity, tariff).

What doesn't transfer well: most enterprise pricing workbenches exist
to serve many analysts pricing many deals over months, which is why
they accumulate scenario libraries, audit trails, and permissions.
This app prices one policy at one location end-to-end, data pull
included — closer to a case-study tool than a production rating
engine — so most of that heavier machinery would be borrowed
complexity rather than something this app actually needs.
