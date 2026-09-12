# The workbench

Prices a parametric insurance contract against a below-normal year of
sunshine, for any Indian pincode, from twenty years of ERA5-Land irradiance.

The repository root [`README.md`](../README.md) covers the product and the
case study it came from; this file is about the code.

Generalised from a case study that priced one 3 kVA rooftop installation in
Ahmedabad (pincode 380006); at those reference parameters this app reproduces
the submitted numbers exactly — σ 84.65 kWh, bands at 4,557.67 / 4,515.35 kWh,
payouts ₹121.69 / ₹365.06 / ₹608.43, burn cost ₹73.01, gross premium ₹137.48.

## How it works

1. **Find the cell** — the pincode boundary gives a centroid, which snaps to
   the ERA5-Land grid cell that settles every claim.
2. **Pull the record** — daily surface solar radiation, one year at a time,
   cached for the life of the process.
3. **Shape the contract** — units, tariff, severity bands, what each pays. The
   backtest re-runs on every change.
4. **Price and export** — burn cost, risk margin and loadings, out to a
   live-formula workbook or a policy report.

## Layers

| | |
|---|---|
| `pricing_engine/` | Pure functions, standard library only. No file reads, no network — which is what makes it cheap enough to re-run on every input change. |
| `data_layer/` | The only layer that touches the network: bharatlas for boundaries, Earth Engine for irradiance, a parquet cache, an in-memory job manager. |
| `api/` | Thin HTTP wrappers, one call each, plus the xlsx and PDF exports. |
| `ui/` | React + TypeScript. Guided input flow, then a dashboard. |

## Running it locally

```bash
uv run uvicorn api.main:app --port 8000
```

```bash
cd ui && npm run dev
```

Then open http://localhost:5173. Earth Engine access is needed for anything
beyond the cached pincodes: `earthengine authenticate` locally, or
`EE_SERVICE_ACCOUNT_JSON` when deployed.

Tests: `uv run pytest` for the 84 offline tests, `uv run pytest -m live` for
the six that hit Earth Engine and bharatlas for real.

## What it stores

Nothing durable. With `EPHEMERAL_CACHE=1` the weather cache lives in a temp
directory that is discarded when the process stops. The only thing that
persists anywhere is the visitor's own inputs, in their browser's
`localStorage`, which never reaches the server.

See [DEPLOY.md](DEPLOY.md) for hosting, Earth Engine service accounts, and the
single-instance constraint.
