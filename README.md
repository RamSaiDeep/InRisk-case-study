# Parametric Insurance for Rooftop Solar Generation Shortfall

InRisk Labs quantitative analyst case study — and a working pricing workbench
built from it.

**Live app → https://solar-pricing-workbench.onrender.com**

---

## The product

A parametric cover against a below-normal year of sunshine. A rooftop solar
customer is promised a certain annual generation; when the weather falls short
of it, the policy pays — on a public weather index, with no site visit and no
proof of physical loss.

The case study priced one installation: a 3 kVA rooftop system at pincode
380006, Ahmedabad.

| | |
|---|---|
| Weather index | ERA5-Land Surface Solar Radiation Downwards (SSRD), daily, 2005–2024 |
| Settlement area | The ERA5-Land grid cell at 22.9997°N, 72.6012°E (~9 km across) |
| Index | Modelled Generation = annual normalised SSRD × performance ratio × capacity |
| Trigger | 4,600 kWh (the promised annual generation) |
| Structure | Three severity bands, each paying a fixed amount |
| Sum insured | ₹608.43 |
| **Premium** | **₹137.48 per policy per year** |

Bands and payouts are set in standard deviations of modelled generation
(σ = 84.65 kWh), not round percentages, so they follow how much this
particular location actually varies. Six of the twenty years backtested would
have paid; none reached the most severe band.

## The app

The **InRisk Labs Solar Yield Cover Solution** prototype takes that one
contract to **any Indian pincode**. A
visitor enters a pincode and nothing else: the 3 kVA unit, tariff, bands, loadings and 2005–2024 pricing window are the workbook's terms,
held fixed. What changes on screen is only the location, which is the point.
It shows that the same policy design scales across the country.

At 380006 it reproduces the submitted ₹137.48 exactly, which is the regression
test the whole thing is built around.

1. **Locate** — the pincode boundary gives a centroid, which snaps to the
   ERA5-Land grid cell that settles every claim. The policy page draws both,
   to scale: the cell is far larger than most pincodes, which is the basis
   risk made visible.
2. **Pull the record** — daily SSRD from Google Earth Engine, a year at a
   time, with progress reported as it goes.
3. **Price** — the premium and its build-up, coverage terms, a payout sheet
   with the twenty-year backtest, and the premium for 1 to 10,000 units.

It is two pages: `/` takes the pincode, and `/?pincode=380006` is that
pincode's policy, so a policy link can be shared directly.
The API still accepts any contract (and serves the workbook export). The UI
just doesn't expose any of it.

### How it is put together

| Layer | Responsibility |
|---|---|
| `webapp/pricing_engine/` | The model. Pure functions, standard library only — no file reads, no network, nothing to mock. This is what makes re-pricing on every keystroke cost about 5 ms. |
| `webapp/data_layer/` | The only layer that touches the network: bharatlas for pincode boundaries, Earth Engine for irradiance, a parquet cache, an in-memory job manager for the slow fetch. |
| `webapp/api/` | Thin HTTP wrappers — one call each — plus the workbook and report formatters. |
| `webapp/ui/` | React + TypeScript. One pincode input, then a read-only policy page. |

The engine knows nothing about HTTP, the API contains no formulas, and the
data layer is the only thing that can fail because someone else's server is
down. Errors map to status codes in exactly one place: pincode not found 404,
upstream changed 502, server misconfigured 500, priced before fetching 409,
bad input 422.

## Repository layout

```
README.md            this file
render.yaml          deployment blueprint (must live at the root)
notebooks/           the original exploration: boundary selection, data pull
raw/                 the boundary files and the three ERA5-Land series
webapp/              the application
  ├── pricing_engine/  the model
  ├── data_layer/      bharatlas, Earth Engine, cache, jobs
  ├── api/             FastAPI service, xlsx and PDF exports
  ├── ui/              React frontend
  ├── tests/           87 offline, 6 live
  ├── Dockerfile       one image: API, frontend, headless browser
  └── DEPLOY.md        hosting, Earth Engine service accounts, constraints
```

The submitted `Report.pdf` and `Solar_Parametric_Workings.xlsx` are not in the
repository; `notebooks/` and `raw/` hold the work they were built from.

## Running it

Needs Python 3.13 with [uv](https://docs.astral.sh/uv/), Node 22, and Earth
Engine access (`earthengine authenticate`).

```bash
cd webapp && uv run uvicorn api.main:app --port 8000
```

```bash
cd webapp/ui && npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to the backend,
so the app is same-origin and needs no CORS configuration.

```bash
cd webapp && uv run pytest          # 87 tests, no network
cd webapp && uv run pytest -m live  # 6 more, against Earth Engine and bharatlas
```

The offline suite includes the case study as a regression: if a change moves
σ, a band, or the premium off the submitted figures, it fails.

## Data

- **ERA5-Land** daily aggregates, Copernicus Climate Change Service, read
  through Google Earth Engine. A reanalysis, not a ground measurement.
- **Pincode boundaries** from data.gov.in via
  [bharatlas](https://bharatlas.com) (GODL-India). Voronoi approximations of
  delivery post office areas, not surveyed boundaries.

## Known limits

Stated plainly, because they bear on how the numbers should be read:

- **Twenty years is short.** Enough to estimate a typical year; not enough to
  say much about an extreme one. The most severe band has no historical year
  in it at the reference parameters, so its payout is an extrapolation.
- **The index is the weather, not the plant.** Soiling, shading, inverter
  faults and grid outages all cut real generation without moving the index.
  Ahmedabad is a high-soiling location, and a 5% soiling loss exceeds the
  mild-band payout.
- **Fixed payouts have cliff edges.** Two near-identical years on opposite
  sides of a boundary are paid differently — in the reference backtest, 2024
  sits 1.7 kWh from a boundary, a 0.04% difference in annual irradiance
  separating ₹121.69 from ₹365.06.
- **Settlement reads a ~9 km cell**, not the roof. Any difference in
  *variability*, not just average level, between the two is unmeasured.
- **One instance only.** Fetch jobs are tracked in process memory, so the
  service does not scale horizontally as written. See `webapp/DEPLOY.md`.

## Deployment

Deployed on Render from `render.yaml`; nothing is stored on a durable disk,
and the weather cache lives only as long as the process. The report export is
switched off there because headless Chrome needs more CPU than the free plan
provides — `ENABLE_REPORT_EXPORT=1` brings it back on a larger instance.

See [`webapp/DEPLOY.md`](webapp/DEPLOY.md) for hosting options, the Earth
Engine service-account setup, and why it runs as a single instance.
