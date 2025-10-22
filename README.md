# DSA-110 Continuum Imaging Pipeline

This repository contains the streaming continuum-imaging pipeline for DSA-110:
- Watches incoming UVH5 subband files and converts them to CASA Measurement Sets (MS)
- Calibrates calibrator groups and registers calibration tables
- Applies calibration to targets and produces quick continuum images
- Records products and processing metadata in lightweight SQLite databases
- Exposes a monitoring API with status, products, and QA views

The pipeline can be run via systemd (recommended for the stream worker) or via Docker Compose (good for API and reproducible deployments). A simple mosaicking skeleton and housekeeping tool are also included.

Quick look: see `docs/quicklook.md` for a sub-minute convert→calibrate→image flow using RAM staging, fast calibration, and quick imaging.
Visual overview: see `docs/pipeline.md` for diagrams of the end-to-end pipeline and its sub-stages.


## Directory Layout

- `src/dsa110_contimg/`
  - `conversion/`
    - `streaming_converter.py`: stream daemon (ingest → convert → calibrate/apply → image)
    - `uvh5_to_ms.py`: standalone converter (legacy/utility)
    - `strategies/`: Strategy orchestrator and writer plugins
      - `uvh5_to_ms_converter.py`: orchestrator CLI (primary entry for conversion)
      - `direct_subband.py`: parallel per-subband writer, robust for CASA
      - `pyuvdata_monolithic.py`: single-shot writer via `UVData.write_ms`
    - `helpers.py`: antenna positions, meridian phasing, model/weights, etc.
  - `calibration/`: CASA-based solving (K/BA/BP/GA/GP/2G), applycal, selection
  - `imaging/`: tclean CLI and a backfill imaging worker
  - `database/`: SQLite helpers
    - `registry.py`: calibration table registry (apply order + validity)
    - `products.py`: products DB helpers (ms_index + images) and indices
  - `api/`: FastAPI application (monitoring/status/products/QA)
  - `qa/`: fast plots and helpers
  - `mosaic/`: (new) mosaic planner/builder CLI
- `ops/systemd/`: systemd unit files (+ shared env)
- `ops/docker/`: Dockerfile, environment.yml, compose, and .env template
- `ops/pipeline/housekeeping.py`: cleanup and queue recovery utility
- `scripts/`: operational scripts (`run_conversion.sh`, etc.)
- `state/`: default location for pipeline DBs and QA artifacts (configurable)


## Services and Components

- Streaming Worker (core)
  - Watches `*_sb??.hdf5`, groups by time, converts via strategy orchestrator
  - Calibrator matching (optional); solves calibrator MS and registers caltables
  - Applies active caltables to targets and runs tclean quick images
  - Writes artifacts (CASA images) and updates `ms_index` in products DB
  - Records performance metrics (including WRITER_TYPE)

- Monitoring API
  - Status of queue, recent groups, calibration sets, system metrics
  - Products and QA thumbnails; group detail view
  - New endpoints:
    - `GET /api/ms_index?stage=&status=&limit=` → filtered `ms_index` rows
    - `POST /api/reprocess/{group_id}` → nudge a group back to `pending`

- Backfill Imaging Worker (optional)
  - One-shot or daemon scan of an MS directory; applies current calibration and images anything missed

- Mosaicking (skeleton)
  - `python -m dsa110_contimg.mosaic.cli plan` → record a mosaic plan from products DB tiles
  - `python -m dsa110_contimg.mosaic.cli build` → CASA `immath` mean mosaic if tiles are co-aligned

- Housekeeping
  - Recover stale `in_progress` groups back to `pending`, mark stale `collecting` as `failed`
  - Remove old `stream_*` temporary directories


## Databases

- Queue DB (SQLite): `state/ingest.sqlite3`
  - `ingest_queue` (group state), `subband_files` (arrivals), `performance_metrics` (writer_type, timings)
- Calibration Registry DB (SQLite): `state/cal_registry.sqlite3`
  - `caltables` with logical set names, apply order, validity windows
- Products DB (SQLite): `state/products.sqlite3`
  - `ms_index(path PRIMARY KEY, start_mjd, end_mjd, mid_mjd, processed_at, status, stage, stage_updated_at, cal_applied, imagename)`
  - `images(id, path, ms_path, created_at, type, beam_major_arcsec, noise_jy, pbcor)`
  - Indices:
    - `idx_images_ms_path ON images(ms_path)`
    - `idx_ms_index_stage_path ON ms_index(stage, path)`
    - `idx_ms_index_status ON ms_index(status)`


## Environment Variables

- CORE
  - `PIPELINE_PRODUCTS_DB` (e.g., `state/products.sqlite3`)
  - `PIPELINE_STATE_DIR` (e.g., `state`)
  - `HDF5_USE_FILE_LOCKING=FALSE` (recommended)
  - `OMP_NUM_THREADS`, `MKL_NUM_THREADS` (e.g., 4)
- STREAMING
  - `PIPELINE_POINTING_DEC_DEG`, `VLA_CALIBRATOR_CSV`, `CAL_MATCH_RADIUS_DEG`, `CAL_MATCH_TOPN` (optional calibrator matching)
- IMAGING
  - `IMG_IMSIZE`, `IMG_ROBUST`, `IMG_NITER`, `IMG_THRESHOLD`


## Running with systemd (recommended for streaming worker)

- Edit `/data/dsa110-contimg/ops/systemd/contimg.env` to set paths and env
- Create logs dir: `mkdir -p /data/dsa110-contimg/state/logs`
- Install units and start:
  - `sudo cp ops/systemd/*.service /etc/systemd/system/`
  - `sudo systemctl daemon-reload`
  - `sudo systemctl enable --now contimg-stream.service contimg-api.service`

Units:
- `ops/systemd/contimg-stream.service` runs the streaming worker with orchestrator writer (subprocess path for stability)
- `ops/systemd/contimg-api.service` runs the API via uvicorn


## Running with Docker Compose

- Copy and edit env:
  - `cp ops/docker/.env.example ops/docker/.env`
  - Set absolute host paths for `REPO_ROOT`, `CONTIMG_*`, and `UID`/`GID`
- Build and start:
  - `cd ops/docker`
  - `docker compose build`
  - `docker compose up -d`
- Services:
  - `stream`: streaming worker with orchestrator (bind mounts to host paths)
  - `api`: uvicorn exposing `${CONTIMG_API_PORT}`
  - `scheduler`: optional nightly mosaic + periodic housekeeping

Image:
- `ops/docker/Dockerfile` creates a `contimg` conda env (`casa6`, casacore, pyuvdata, FastAPI)
- Code is mounted from the host repo (`PYTHONPATH=/app/src`)


## CLI Reference

- Streaming worker (manual):
  - `python -m dsa110_contimg.conversion.streaming_converter --input-dir /data/ingest --output-dir /data/ms --queue-db state/ingest.sqlite3 --registry-db state/cal_registry.sqlite3 --scratch-dir /data/scratch --log-level INFO --use-subprocess --expected-subbands 16 --chunk-duration 5 --monitoring`
- Backfill imaging worker:
  - Scan: `python -m dsa110_contimg.imaging.worker scan --ms-dir /data/ms --out-dir /data/ms --registry-db state/cal_registry.sqlite3 --products-db state/products.sqlite3 --log-level INFO`
- Standalone converter (legacy/utility):
  - `python -m dsa110_contimg.conversion.uvh5_to_ms --help`
- Orchestrator writer (preferred):
  - `python -m dsa110_contimg.conversion.strategies.uvh5_to_ms_converter --help`
- Registry CLI:
  - `python -m dsa110_contimg.database.registry_cli --help`
- Mosaic CLI (new):
  - Plan: `python -m dsa110_contimg.mosaic.cli plan --products-db state/products.sqlite3 --name night_YYYYMMDD --since <epoch> --until <epoch>`
  - Build: `python -m dsa110_contimg.mosaic.cli build --products-db state/products.sqlite3 --name night_YYYYMMDD --output /data/ms/mosaics/night_YYYYMMDD.img`
- Housekeeping:
  - `python ops/pipeline/housekeeping.py --queue-db state/ingest.sqlite3 --scratch-dir /data/scratch --in-progress-timeout 3600 --collecting-timeout 86400 --temp-age 86400`

## Nightly Mosaic and Housekeeping

- Docker Compose scheduler (optional):
  - Enabled by the `scheduler` service in `ops/docker/docker-compose.yml`
  - Configure with env in `ops/docker/.env` (SCHED_* variables)
    - Runs housekeeping every `SCHED_HOUSEKEEP_INTERVAL_SEC`
    - Runs a nightly mosaic after `SCHED_MOSAIC_HOUR_UTC` for the previous UTC day
  - Start with the other services: `docker compose up -d scheduler`

- Cron snippets (alternative to scheduler service):
  - Nightly mosaic at 03:15 UTC for previous day, and hourly housekeeping:
```
# /etc/cron.d/contimg
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Housekeeping hourly
0 * * * * ubuntu cd /data/dsa110-contimg && \
  PIPELINE_QUEUE_DB=state/ingest.sqlite3 CONTIMG_SCRATCH_DIR=/data/scratch \
  /usr/bin/python3 ops/pipeline/housekeeping.py >> state/logs/housekeeping.log 2>&1

# Nightly mosaic at 03:15 UTC for previous day
15 3 * * * ubuntu cd /data/dsa110-contimg && \
  PIPELINE_PRODUCTS_DB=state/products.sqlite3 \
  /usr/bin/python3 -m dsa110_contimg.mosaic.cli plan --products-db state/products.sqlite3 \
  --name night_$(date -u -d 'yesterday' +\%Y_\%m_\%d) --since $(date -u -d 'yesterday 00:00:00' +\%s) \
  --until $(date -u -d 'today 00:00:00 - 1 sec' +\%s) && \
  /usr/bin/python3 -m dsa110_contimg.mosaic.cli build --products-db state/products.sqlite3 \
  --name night_$(date -u -d 'yesterday' +\%Y_\%m_\%d) --output /data/ms/mosaics/night_$(date -u -d 'yesterday' +\%Y_\%m_\%d).img \
  >> state/logs/mosaic_nightly.log 2>&1
```


## Development Notes and Recent Changes

- Strategy orchestrator is now primary in streaming paths (`direct-subband` writer)
  - Emits `WRITER_TYPE:` to stdout, recorded in `performance_metrics`
  - In-process path also aligned to orchestrator for consistency
- Products DB helpers added (`database/products.py`)
  - Centralizes `ms_index`/`images` schema, upserts, and indices
  - Used by streaming worker and imaging worker to avoid schema drift
- API enhancements
  - `/api/ms_index` filtering endpoint and `/api/reprocess/{group_id}` added
- Stability and CASA best practices
  - Initialize `MODEL_DATA`/`CORRECTED_DATA` and `WEIGHT_SPECTRUM` as needed
  - Set antenna mounts to `ALT-AZ` and fix antenna positions/diameters
  - Constrain thread pools (OMP/MKL) and disable HDF5 file locking
- Legacy and historical
  - dask-ms writing path exists historically but is avoided for CASA workflows
  - Older imports from `dsa110_contimg.core.conversion.*` are deprecated; use `dsa110_contimg.conversion.*`


## Troubleshooting

- `casatools` errors opening MS
  - Use orchestrator `direct-subband` writer; ensure imaging columns exist
- `.fuse_hidden*` files consuming disk
  - Typically from interrupted large writes on FUSE filesystems; clean after ensuring no process holds descriptors
- High queue depth or stale groups
  - Use housekeeping tool or API `/api/status` to analyze; recover or reprocess
- Performance
  - Tune `--max-workers` for writer, thread env vars, and ensure scratch/data are on performant storage


## Contributing

- Keep changes minimal and focused; prefer using the shared DB helpers
- Add tests where practical; synthetic data tools are in `simulation/`
- Follow existing logging styles and module structure
## Git Hook: Commit Summaries to Knowledge Graph

This repository includes a lightweight, non‑blocking Git post‑commit hook that records each commit as a short episode in the Graphiti knowledge graph (group_id `dsa110-contimg`). It helps long‑term recall of changes and decisions during development.

- Hook location: `.githooks/post-commit`
- Activation (already configured): `git config core.hooksPath .githooks`
- Behavior: runs in the background after every `git commit`; failures never block your commit.
- What it stores: commit short hash, branch, and commit message.
- Where it goes: the `graphiti-memory` MCP server (Vertex/Gemini) via the Graphiti client.

Disable later:

```
git config --unset core.hooksPath
```

Re‑enable:

```
git config core.hooksPath .githooks
```

If you need to customize the target group or episode format, edit `.githooks/post-commit`.
