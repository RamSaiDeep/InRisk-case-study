# Deploying the workbench

One container: the FastAPI service, the built frontend, and the headless
browser the PDF export renders through. Nothing survives a restart.

## What it stores

Nothing on a durable disk. With `EPHEMERAL_CACHE=1` (set in the Dockerfile)
the weather cache lives in a temp directory created at start and removed when
the process stops. A deployed instance therefore holds:

| | Where | Survives a restart |
|---|---|---|
| Pincode centroid index (~7 MB) | temp dir | no |
| Fetched daily series, per pincode | temp dir | no |
| Job state | process memory | no |
| The visitor's own inputs | their browser's `localStorage` | yes, on their device only |

The last row is the only thing that persists anywhere, and it never reaches
the server — it is what lets someone reload the page without redoing the
wizard. Setting `localStorage` aside, a restarted instance is a blank one.

The cost of that is honest and worth knowing before you demo: **the first
pincode on a cold instance takes roughly a minute** — about 12s to pull the
bharatlas boundary file and build the centroid index, then ~50s for a 20-year
Earth Engine fetch. Every later change for that pincode is instant, until the
instance sleeps.

The centroid index is already baked into the image at build time
(`PREBUILT_CENTROID_INDEX`), which removes the 12s and, more importantly,
keeps the 19,312-polygon build off a small runtime instance. It is public
reference data - every Indian pincode's centroid and outline - so shipping it
stores nothing about anyone. The ~50s Earth Engine fetch per new pincode
remains.

## Earth Engine access

**Do not ship your personal credentials.** `~/.config/earthengine/credentials`
is a user OAuth token; in an image it is a leaked credential.

A deployed instance authenticates as a **service account**:

1. In the Google Cloud project, create a service account.
2. Register it with Earth Engine at
   <https://console.cloud.google.com/earth-engine> — the account needs Earth
   Engine access in its own right, and the project must be registered for
   commercial or non-commercial use.
3. Create a JSON key and give it to the host as `EE_SERVICE_ACCOUNT_JSON` —
   either the JSON itself or a path to a mounted file.
4. Set `GEE_PROJECT` if it differs from the default in `data_layer/config.py`.

On Cloud Run you can skip the key file: attach the service account to the
service and it is picked up automatically.

## Run one instance

Fetch jobs are tracked in **process memory**, so a second worker or a second
instance would not recognise a job id the first one handed out, and the
fetching screen would poll forever. Until that state moves to a shared store:

- `--workers 1` (already in the Dockerfile)
- max instances **1**, or session affinity if the host offers it

That is fine for a demo and is the documented limit of the design, not an
oversight.

## Where to put it

| Host | Fit | Notes |
|---|---|---|
| **Google Cloud Run** | best | Same cloud as Earth Engine, so the service account attaches natively with no key file. `/tmp` is a tmpfs, matching the no-storage requirement exactly. Scales to zero, so an idle demo costs nothing — at the price of a cold start. Set **max instances 1**. |
| **Fly.io** | good | Docker-native, one small machine, scale to zero. Needs the JSON key as a secret. |
| **Render** | good, and simplest from GitHub | `render.yaml` is in the repo: New -> Blueprint -> pick the repo -> paste the Earth Engine key. The free tier has 512 MB and sleeps after 15 minutes, so the first visitor pays a cold start plus the fetch. Workable because the pincode index is prebuilt; without that it would likely run out of memory. |
| **Railway** | good | Same shape as Render, simpler dashboard, no free tier now. |
| **Hugging Face Spaces (Docker)** | most generous free tier | 2 vCPU and 16 GB free - 20x the CPU and 32x the memory of Render's free tier, and more CPU than Render's $25 plan. Sleeps after 48 hours rather than 15 minutes, so a warmed cache actually survives a demo. Two costs: the free tier is US-hosted, which adds roughly 150 ms of round trip from India on every interaction, and Spaces have no GitHub integration, so the code is pushed to the Space's own git repo as well. |
| Vercel / Netlify | **no** | Serverless functions cannot hold job state between requests, have short execution limits, and cannot run Chromium. They are fine for the frontend alone, but the backend does not fit. |

### Hugging Face Spaces, end to end

The Space repo's root has to be the Dockerfile's directory, so `webapp/` is
pushed as the root using a subtree:

```bash
git remote add space https://huggingface.co/spaces/ramasaideepv/parametric-solar-cover
git subtree push --prefix=webapp space main
```

`README.md` already carries the Space frontmatter (`sdk: docker`,
`app_port: 8080`). Set `EE_SERVICE_ACCOUNT_JSON` under Settings -> Variables
and secrets, as a **secret**, not a variable.

### Cloud Run, end to end

```bash
gcloud run deploy solar-pricing \
  --source . \
  --region asia-south1 \
  --service-account ee-runner@development-hruday.iam.gserviceaccount.com \
  --max-instances 1 \
  --memory 1Gi \
  --timeout 300 \
  --allow-unauthenticated
```

`--memory 1Gi` because the centroid index and a year of readings sit in memory
at the same time; `--timeout 300` because a 20-year fetch runs past the 60s
default.

## Before you show it to anyone

- **Quota.** Earth Engine quota is per project, and a public URL invites a new
  pincode per visitor, each costing a full fetch. Watch it, or keep the link
  private.
- **The 60-second first click.** Consider fetching one or two pincodes
  yourself right after a deploy so the demo opens warm.
- **Cost.** Cloud Run scale-to-zero and Fly's stopped machines cost nothing
  idle. Render's paid tier bills whether or not anyone visits.
