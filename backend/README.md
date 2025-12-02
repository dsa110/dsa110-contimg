# DSA-110 Continuum Imaging Pipeline

## QUICK START (READ THIS FIRST!)

**New to this project? Start here:**

1. **Run the setup script:**

   ```bash
   ./scripts/ops/dev/setup-dev.sh
   ```

   This will:

   - Set up git hooks
   - Install dependencies
   - Verify your environment
   - Check for common issues

2. **Verify your setup:**

   ```bash
   ./scripts/ops/quality/check-environment.sh
   ```

3. **Read the developer guide:**
   - [`docs/guides/development/DEVELOPER_HANDOFF_WARNINGS.md`](docs/guides/development/DEVELOPER_HANDOFF_WARNINGS.md) -
     Critical warnings
   - [`docs/guides/operations/QUICK_REFERENCE_WARNINGS.md`](docs/guides/operations/QUICK_REFERENCE_WARNINGS.md) -
     Quick reference

**CRITICAL:** Always use casa6 Python environment:

```bash
# WRONG
python script.py

# CORRECT
/opt/miniforge/envs/casa6/bin/python script.py
# Or use wrapper:
./scripts/ops/utils/run-python.sh script.py
```

---

Note: Before creating any markdown documentation, see
[`docs/reference/documentation_standards/DOCUMENTATION_QUICK_REFERENCE.md`](docs/reference/documentation_standards/DOCUMENTATION_QUICK_REFERENCE.md).
Do not create markdown files in the repository root - use the `docs/` structure
instead.

---

This repository contains the streaming continuum-imaging pipeline for DSA-110:

- Watches incoming UVH5 subband files and converts them to CASA Measurement Sets
  (MS)
- Calibrates calibrator groups and registers calibration tables
- Applies calibration to targets and produces quick continuum images
- Records products and processing metadata in lightweight SQLite databases
- Exposes a monitoring API with status, products, and QA views

The pipeline can be run via systemd (recommended for the stream worker) or via
Docker Compose (good for API and reproducible deployments). A simple mosaicking
skeleton and housekeeping tool are also included.

Quick look: see `docs/guides/operations/quicklook.md` for a sub-minute
convert-calibrate-image flow using RAM staging, fast calibration, and quick
imaging.

## Data Paths

- **Incoming UVH5 files:** `/data/incoming/` (watched by streaming converter)
  - The streaming worker monitors this directory for new `*_sb??.hdf5` files
  - Files are grouped by time windows and converted to Measurement Sets

## Directory Layout

- `backend/src/dsa110_contimg/`
  - `conversion/`: Streaming and legacy conversion logic
    - `streaming/streaming_converter.py`: Main daemon for monitoring and
      processing
    - `strategies/`: Pluggable processing strategies (orchestrator, direct
      writers)
  - `calibration/`: CASA-based calibration routines
  - `imaging/`: Imaging workers (tclean wrappers)
  - `database/`: Database interaction helpers (registry, products)
  - `api/`: FastAPI application source
  - `qa/`: Quality assurance plotting and metrics
  - `mosaic/`: Mosaic planning and building tools
  - `pipeline/`: Pipeline orchestration framework
  - `pointing/`: Pointing and transit calculations
  - `photometry/`: Photometry analysis tools
  - `catalog/`: Catalog management and cross-matching
- `frontend/`: React dashboard application
- `docs/`: Project documentation
  - `guides/`: How-to guides (development, operations, workflows)
  - `reference/`: API reference, CLI docs, configuration
  - `architecture/`: System design documents
  - `troubleshooting/`: Problem resolution guides
- `ops/`: Operational configuration
  - `systemd/`: Systemd service definitions
  - `docker/`: Docker Compose and environment configuration
  - `scripts/`: Operational scripts (also mirrored in `scripts/ops/`)
- `scripts/`: Utility and operational scripts
  - `ops/`: Operational scripts (dev, quality, utils, monitoring)
  - `archive/`: Archived scripts
  - `generate_structure_diagram.py`: Directory structure visualization tool
- `config/`: Configuration files (docker, editor, hooks, linting, pipeline)
- `state/`: Runtime state (databases, logs, temporary artifacts)
- `products/`: Output data products (images, mosaics, caltables)
- `vendor/`: External dependencies (aocommon, everybeam)

## Development Tools

### Directory Structure Visualization

The project includes a tool to automatically generate visual diagrams of
directory structures. This is useful for understanding the organization of any
directory in the project.

**Usage:**

```bash
# Generate diagram for backend
python scripts/generate_structure_diagram.py /data/dsa110-contimg/backend backend_structure.svg

# Generate diagram for frontend
python scripts/generate_structure_diagram.py /data/dsa110-contimg/frontend frontend_structure.svg

# Generate diagram for any directory
python scripts/generate_structure_diagram.py /data/dsa110-contimg/docs docs_structure.svg
```

**Features:**

- Automatically detects Python packages, key files, and directory structure
- Generates Mermaid flowchart diagrams showing module relationships
- Renders to SVG format (ready to use in documentation)
- Detects common pipeline relationships (conversion :arrow_right: calibration
  :arrow_right: imaging, etc.)
- Color-codes different module types for easy identification

**Output:**

The script generates two files:

- `<output>.svg` - Rendered SVG diagram (ready to use)
- `<output>.mmd` - Mermaid source code (for manual editing)

The diagrams can be used in:

- GitHub/GitLab markdown (renders automatically)
- Documentation
- Presentations
- Project onboarding materials

For more details, see `docs/dev/STRUCTURE_DIAGRAM_README.md`.

## Services and Components

- Streaming Worker (core)

  - Watches `/data/incoming/` for `*_sb??.hdf5` files, groups by time, converts
    via strategy orchestrator
  - Calibrator matching (optional); solves calibrator MS and registers caltables
  - Applies active caltables to targets and runs tclean quick images
  - Writes artifacts (CASA images) and updates `ms_index` in products DB
  - Records performance metrics (including WRITER_TYPE)

- Monitoring API (FastAPI)

  - Status of queue, recent groups, calibration sets, system metrics
  - Products and QA thumbnails; group detail view
  - Endpoints:
    - `GET /api/ms_index?stage=&status=&limit=` - filtered `ms_index` rows
    - `POST /api/reprocess/{group_id}` - nudge a group back to `pending`
    - `GET /api/ese/candidates` - ESE candidate viewer
    - `GET /api/status` - pipeline status overview

- Backfill Imaging Worker (optional)

  - One-shot or daemon scan of an MS directory; applies current calibration and
    images anything missed

- Mosaicking (skeleton)

  - `python -m dsa110_contimg.mosaic.cli plan` - record a mosaic plan from
    products DB tiles
  - `python -m dsa110_contimg.mosaic.cli build` - CASA `immath` mean mosaic if
    tiles are co-aligned

- Housekeeping
  - Recover stale `in_progress` groups back to `pending`, mark stale
    `collecting` as `failed`
  - Remove old `stream_*` temporary directories

## Databases

The pipeline uses a **unified SQLite database** for all state management and
product tracking. As of Phase 2 consolidation, all tables are stored in a single
database file.

**Unified Database:**

| Database                    | Purpose                                                                                           |
| --------------------------- | ------------------------------------------------------------------------------------------------- |
| `state/db/pipeline.sqlite3` | All pipeline state: ingest queue, calibration registry, products, HDF5 index, photometry, mosaics |

The unified database contains tables previously spread across multiple files:

- Ingest queue management and performance metrics (`ingest_queue`, `performance_metrics`)
- Calibration table registry with validity windows (`calibration_tables`, `calibration_source_catalog`)
- Product tracking: MS index, images, photometry (`ms_index`, `images`, `photometry_results`)
- HDF5 file index for fast queries (`hdf5_file_index`)
- Mosaic groups and planning (`mosaic_groups`, `mosaic_members`)

> **📖 Full Documentation:** See
> [Database Reference](docs/reference/DATABASE_REFERENCE_INDEX.md) for complete
> schemas, common queries, and Python access examples.

**Removed Legacy Files:**

- ~~`state/ingest.sqlite3`~~ (merged into `pipeline.sqlite3`)
- ~~`state/cal_registry.sqlite3`~~ (merged into `pipeline.sqlite3`)
- ~~`state/products.sqlite3`~~ (merged into `pipeline.sqlite3`)
- ~~`state/hdf5.sqlite3`~~ (merged into `pipeline.sqlite3`)
- ~~`state/streaming_queue.sqlite3`~~ (replaced by `ingest_queue` table)
- ~~`state/products.db`, `state/queue.db`, `state/pipeline_queue.db`~~ (old
  schema, removed)

## Environment Variables

- CORE
  - `PIPELINE_DB` (e.g., `state/db/pipeline.sqlite3`) - **Primary database path**
  - `PIPELINE_STATE_DIR` (e.g., `state`)
  - `HDF5_USE_FILE_LOCKING=FALSE` (recommended)
  - `OMP_NUM_THREADS`, `MKL_NUM_THREADS` (e.g., 4)
  - Legacy aliases (still supported): `PIPELINE_PRODUCTS_DB`, `CAL_REGISTRY_DB`, `INGEST_DB`, `HDF5_DB`
- PIPELINE FRAMEWORK
  - The pipeline orchestration framework is the default implementation
    - All job execution uses direct function calls (no subprocess overhead)
    - Declarative pipeline with dependency resolution, retry policies, and
      improved error handling
    - See `backend/src/dsa110_contimg/pipeline/` for the framework
      implementation
- STREAMING
  - `PIPELINE_POINTING_DEC_DEG`, `VLA_CATALOG`, `CAL_MATCH_RADIUS_DEG`,
    `CAL_MATCH_TOPN` (optional calibrator matching)
  - Note: `VLA_CATALOG` can point to SQLite database (preferred) or CSV file.
    System automatically prefers SQLite at
    `state/catalogs/vla_calibrators.sqlite3` if available.
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

- `ops/systemd/contimg-stream.service` runs the streaming worker with
  orchestrator writer (subprocess path for stability)
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
  - `dashboard`: production frontend build (serves static files on port 3210)
  - `dashboard-dev`: development frontend with hot reloading (mapped to
    port 3210)

Image:

- `ops/docker/Dockerfile` creates a `contimg` conda env (`casa6`, casacore,
  pyuvdata, FastAPI)
- Code is mounted from the host repo (`PYTHONPATH=/app/src`)

## CLI Reference

- Streaming worker (manual):
  - `python -m dsa110_contimg.conversion.streaming.streaming_converter --input-dir /data/incoming --output-dir /stage/dsa110-contimg/ms --scratch-dir /stage/dsa110-contimg --log-level INFO --use-subprocess --expected-subbands 16 --chunk-duration 5 --monitoring`
  - Uses `PIPELINE_DB` environment variable (default: `state/db/pipeline.sqlite3`)
- Backfill imaging worker:
  - Scan:
    `python -m dsa110_contimg.imaging.worker scan --ms-dir /data/ms --out-dir /data/ms --log-level INFO`
  - Uses `PIPELINE_DB` environment variable for registry and products
- Standalone converter (legacy/utility):
  - `python -m dsa110_contimg.conversion.uvh5_to_ms --help`
- Orchestrator writer (preferred):
  - `python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator --help`
- Registry CLI:
  - `python -m dsa110_contimg.database.registry_cli --help`
- Mosaic CLI:
  - Plan:
    `python -m dsa110_contimg.mosaic.cli plan --name night_YYYYMMDD --since <epoch> --until <epoch>`
  - Build:
    `python -m dsa110_contimg.mosaic.cli build --name night_YYYYMMDD --output /data/ms/mosaics/night_YYYYMMDD.img`
  - Uses `PIPELINE_DB` environment variable for products database
- Housekeeping:
  - `python ops/pipeline/housekeeping.py --scratch-dir /stage/dsa110-contimg --in-progress-timeout 3600 --collecting-timeout 86400 --temp-age 86400`
  - Uses `PIPELINE_DB` environment variable for queue database

## Nightly Mosaic and Housekeeping

- Docker Compose scheduler (optional):

  - Enabled by the `scheduler` service in `ops/docker/docker-compose.yml`
  - Configure with env in `ops/docker/.env` (SCHED\_\* variables)
    - Runs housekeeping every `SCHED_HOUSEKEEP_INTERVAL_SEC`
    - Runs a nightly mosaic after `SCHED_MOSAIC_HOUR_UTC` for the previous UTC
      day
  - Start with the other services: `docker compose up -d scheduler`

- Cron snippets (alternative to scheduler service):
  - Nightly mosaic at 03:15 UTC for previous day, and hourly housekeeping:

```bash
# /etc/cron.d/contimg
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Unified database path (Phase 2 consolidation)
PIPELINE_DB=/data/dsa110-contimg/state/db/pipeline.sqlite3

# Housekeeping hourly
0 * * * * ubuntu cd /data/dsa110-contimg && \
  PIPELINE_DB=${PIPELINE_DB} CONTIMG_SCRATCH_DIR=/data/scratch \
  /data/dsa110-contimg/scripts/ops/utils/run_casa_cmd.sh /usr/bin/python3 ops/pipeline/housekeeping.py >> state/logs/housekeeping.log 2>&1

# Nightly mosaic at 03:15 UTC for previous day
15 3 * * * ubuntu cd /data/dsa110-contimg && \
  PIPELINE_DB=${PIPELINE_DB} \
  /data/dsa110-contimg/scripts/ops/utils/run_casa_cmd.sh /usr/bin/python3 -m dsa110_contimg.mosaic.cli plan --products-db ${PIPELINE_DB} \
  --name night_$(date -u -d 'yesterday' +\%Y_\%m_\%d) --since $(date -u -d 'yesterday 00:00:00' +\%s) \
  --until $(date -u -d 'today 00:00:00 - 1 sec' +\%s) && \
  /data/dsa110-contimg/scripts/ops/utils/run_casa_cmd.sh /usr/bin/python3 -m dsa110_contimg.mosaic.cli build --products-db ${PIPELINE_DB} \
  --name night_$(date -u -d 'yesterday' +\%Y_\%m_\%d) --output /data/ms/mosaics/night_$(date -u -d 'yesterday' +\%Y_\%m_\%d).img \
  >> state/logs/mosaic_nightly.log 2>&1
```

## Development Notes

- Strategy orchestrator is primary in streaming paths (`direct-subband` writer)
  - Emits `WRITER_TYPE:` to stdout, recorded in `performance_metrics`
  - In-process path also aligned to orchestrator for consistency
- Products DB helpers (`database/products.py`)
  - Centralizes `ms_index`/`images` schema, upserts, and indices
  - Used by streaming worker and imaging worker to avoid schema drift
- Stability and CASA best practices
  - Initialize `MODEL_DATA`/`CORRECTED_DATA` and `WEIGHT_SPECTRUM` as needed
  - Set antenna mounts to `ALT-AZ` and fix antenna positions/diameters
  - Constrain thread pools (OMP/MKL) and disable HDF5 file locking
- Legacy and historical
  - dask-ms writing path exists historically but is avoided for CASA workflows
  - Older imports from `dsa110_contimg.core.conversion.*` are deprecated; use
    `dsa110_contimg.conversion.*`

### Frontend Development

#### Option 1: Local Development (Recommended)

If you brought up the API container on a different port (e.g., 8010 via
`ops/docker/.env` - `CONTIMG_API_PORT=8010`), point the frontend at it during
development:

- Quick run with env var (recommended):
  - `cd frontend && conda run -n casa6 VITE_API_URL=http://localhost:8010 npm run dev`
- Or set a persistent override:
  - Edit `frontend/.env.local` and set: `VITE_API_URL=http://localhost:8010`
- Or use the Vite proxy:
  - Edit `frontend/vite.config.ts` and set
    `server.proxy['/api'].target = 'http://localhost:8010'`

**Notes:**

- Vite requires Node.js 20.19+ or 22.12+; use the provided casa6 environment as
  in `frontend/README.md`.
- Verify API availability: `curl http://localhost:8010/api/ese/candidates`
  should return JSON.
- After switching, the Dashboard's ESE panel and other enhanced endpoints will
  populate.

#### Option 2: Docker Development (Hot Reloading)

For development with hot reloading in Docker (no rebuilds needed), use the root
`docker-compose.yml`:

```bash
# From repository root
# Use 'docker compose' (v2, recommended) - newer Docker CLI plugin
# Note: If you only have 'docker-compose' (v1), upgrade Docker or use: docker compose up

# Build and start API service (builds from ops/docker/Dockerfile)
docker compose up api

# Start the dev frontend container (builds from frontend/Dockerfile.dev)
docker compose up dashboard-dev

# Or start both together
docker compose up api dashboard-dev

# Or run in background
docker compose up -d api dashboard-dev

# View logs
docker compose logs -f dashboard-dev
docker compose logs -f api

# Stop
docker compose stop dashboard-dev api
```

**Features:**

- **Backend (API)**: Builds locally from `ops/docker/Dockerfile`, code mounted
  via volumes
- **Frontend (dashboard-dev)**: Hot module replacement (HMR) - code changes
  reflect immediately
- Volume-mounted source code - no image rebuilds needed after initial build
- Frontend available at `http://localhost:3210` (Docker) or
  `http://localhost:3000` (local dev)
- Backend available at `http://localhost:8000`
- Services connect via Docker network

**Requirements:**

- Both services build from local Dockerfiles (no external image pulls needed)
- Frontend code changes in `frontend/src/` will trigger automatic reloads
- Backend code changes in `backend/src/` are mounted and will reload (if using
  uvicorn reload)
- Uses `docker-compose.yml` in repository root (not
  `ops/docker/docker-compose.yml`)

**Note:** Docker maps the frontend to port 3210 externally. Local dev server
uses port 3000. Both can run simultaneously if using different ports.

## Performance Benchmarking

The pipeline includes statistical performance benchmarks using
[airspeed-velocity (asv)](https://asv.readthedocs.io/) to track performance
across commits and detect regressions.

### Quick Start

```bash
conda activate casa6

# Quick check (~5 minutes, single iteration)
make bench-quick

# Full run with statistics (~30 minutes)
make bench

# Generate HTML report
make bench-report && make bench-preview
```

### CLI Alternative

```bash
dsa110-benchmark quick              # Quick check
dsa110-benchmark run                # Full run
dsa110-benchmark report --open      # Generate and view report
dsa110-benchmark compare HEAD~1 HEAD  # Regression check
```

### Benchmark Categories

| Category    | Command                    | Measures                                       |
| ----------- | -------------------------- | ---------------------------------------------- |
| Conversion  | `make bench-conversion`    | HDF5 :arrow_right: MS conversion (SSD staging) |
| Calibration | `make bench-calibration`   | Bandpass, gain, applycal                       |
| Flagging    | (included in `make bench`) | Flag reset, zero flagging                      |
| Imaging     | (disabled by default)      | WSClean imaging                                |

### Reference Results (lxd110h17)

| Benchmark                    | Time  |
| ---------------------------- | ----- |
| `time_convert_subband_group` | 4.05m |
| `time_bandpass_single_field` | 31.1s |
| `time_gaincal_single_field`  | 10.3s |
| `time_flag_zeros`            | 18.2s |

**Full documentation**: See `docs/guides/benchmarking.md` or
`benchmarks/README.md`.

## Troubleshooting

- `casatools` errors opening MS
  - Use orchestrator `direct-subband` writer; ensure imaging columns exist
- `.fuse_hidden*` files consuming disk
  - Typically from interrupted large writes on FUSE filesystems; clean after
    ensuring no process holds descriptors
- High queue depth or stale groups
  - Use housekeeping tool or API `/api/status` to analyze; recover or reprocess
- Performance
  - Tune `--max-workers` for writer, thread env vars, and ensure scratch/data
    are on performant storage

## Contributing

- Keep changes minimal and focused; prefer using the shared DB helpers
- Add tests where practical; synthetic data tools are in `simulation/`
- Follow existing logging styles and module structure

## Git Hook: Commit Summaries (internal tooling)

This repository can optionally use a lightweight, non‑blocking post‑commit hook
to record commit summaries for internal tools. See internal documentation for
setup and details.

## TODO

### Application-Level Authentication

The current setup uses ngrok's built-in GitHub OAuth which requires any GitHub
account to access the API. For proper access control with email filtering (e.g.,
only `@caltech.edu` emails), implement application-level authentication:

**Components needed:**

1. **GitHub OAuth App** - Create at GitHub Settings :arrow_right: Developer
   settings :arrow_right: OAuth Apps
   - Callback URL:
     `https://code.deepsynoptic.org/dsa110-contimg/dashboard/callback`
2. **Backend auth endpoints** (`/api/auth/*`):

   - `POST /api/auth/github` - Exchange GitHub code for session token
   - `GET /api/auth/me` - Return current user info
   - `POST /api/auth/logout` - Clear session
   - Middleware to validate JWT on all `/api/*` requests
   - Email allowlist: `jakobtfaber@gmail.com`, `*@caltech.edu`

3. **Frontend auth flow**:
   - `<LoginPage />` - "Login with GitHub" button
   - `<ProtectedRoute />` - Redirect to login if not authenticated
   - `<AuthProvider />` - Context managing auth state
   - JWT storage in `localStorage` or `httpOnly` cookie

**Reference:** This would replace reliance on ngrok OAuth and work with any
tunnel provider.
