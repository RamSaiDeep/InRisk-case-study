# One image: the API, the built frontend, and the headless browser the PDF
# export renders through.
#
# Nothing is written to a path that outlives the container. EPHEMERAL_CACHE
# puts the weather cache in a temp directory that is discarded when the
# process stops, so a deployed instance holds no data between restarts.

# --- stage 1: build the frontend -----------------------------------------
FROM node:22-slim AS ui

WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build


# --- stage 2: the service -------------------------------------------------
FROM python:3.13-slim

# Chromium is here only for the report export: markdown -> HTML -> PDF. Drop
# this block and the export returns a clear 500 instead; everything else works.
RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_PATH=/usr/bin/chromium \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    EPHEMERAL_CACHE=1

WORKDIR /app

# uv resolves from the lockfile, so the image gets the versions that were tested.
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY pricing_engine/ ./pricing_engine/
COPY data_layer/ ./data_layer/
COPY api/ ./api/
RUN uv sync --frozen --no-dev

# Build the pincode index here rather than on the first request: it needs all
# 19,312 polygons in memory at once, which a 512 MB instance may not have.
ENV PREBUILT_CENTROID_INDEX=/app/reference/pincode_centroids.parquet
RUN mkdir -p /app/reference     && uv run --no-dev python -c "from data_layer.location import build_centroid_index; build_centroid_index()"

COPY --from=ui /ui/dist ./ui/dist

# Cloud Run and most PaaS hosts hand the port in as $PORT.
ENV PORT=8080
EXPOSE 8080

# One worker on purpose: fetch jobs are tracked in memory, so a second worker
# would not see a job the first one started. See DEPLOY.md.
CMD ["sh", "-c", "uv run --no-dev uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
