# DSA-110 Continuum Imaging Pipeline: User Guide

Complete operations documentation for pipeline users.

**Last Updated:** December 1, 2025

---

## Table of Contents

1. [Getting Started](#part-1-getting-started)
2. [Pipeline Operations](#part-2-pipeline-operations)
3. [Dashboard](#part-3-dashboard)
4. [Workflows](#part-4-workflows)
5. [Advanced Features](#part-5-advanced-features)
6. [Reference](#part-6-reference)

---

## Part 1: Getting Started

### 1.1 Prerequisites

| Requirement           | Details                                                       |
| --------------------- | ------------------------------------------------------------- |
| **Conda Environment** | `casa6` with Python 3.11, CASA 6.7, pyuvdata 3.2.4            |
| **Storage**           | `/data/incoming` (raw HDF5), `/stage/dsa110-contimg` (output) |
| **Network Ports**     | 8000 (API), 3210 (Dashboard), 3030 (Grafana)                  |

### 1.2 Environment Setup

```bash
# Activate the casa6 environment
conda activate casa6

# Navigate to project root
cd /data/dsa110-contimg

# Verify installation
python -c "import dsa110_contimg; print('OK')"
```

### 1.3 Configuration

Configuration uses environment variables with Pydantic validation. The primary source is:
`backend/src/dsa110_contimg/pipeline/config.py`

#### Essential Environment Variables

| Variable               | Description                    | Default                    |
| ---------------------- | ------------------------------ | -------------------------- |
| `PIPELINE_INPUT_DIR`   | Input directory for UVH5 files | `/data/incoming`           |
| `PIPELINE_OUTPUT_DIR`  | Output directory for MS files  | `/stage/dsa110-contimg/ms` |
| `PIPELINE_SCRATCH_DIR` | Fast scratch storage           | `/stage/dsa110-contimg`    |
| `PIPELINE_STATE_DIR`   | Database and state directory   | `state`                    |

#### Loading Configuration

```python
from dsa110_contimg.pipeline.config import PipelineConfig

# Load from environment (validates paths by default)
config = PipelineConfig.from_env()

# Load without path validation (for testing)
config = PipelineConfig.from_env(validate_paths=False)
```

#### Conversion Settings

| Variable                     | Description              | Default | Range                      |
| ---------------------------- | ------------------------ | ------- | -------------------------- |
| `PIPELINE_WRITER`            | Writer strategy          | `auto`  | `auto`, `parallel-subband` |
| `PIPELINE_MAX_WORKERS`       | Parallel workers         | `4`     | 1-32                       |
| `PIPELINE_EXPECTED_SUBBANDS` | Subbands per observation | `16`    | 1-32                       |

#### Calibration Settings

| Variable                   | Description            | Default |
| -------------------------- | ---------------------- | ------- |
| `PIPELINE_CAL_BP_MINSNR`   | Bandpass minimum SNR   | `3.0`   |
| `PIPELINE_CAL_GAIN_SOLINT` | Gain solution interval | `inf`   |
| `PIPELINE_DEFAULT_REFANT`  | Reference antenna      | `103`   |

#### Imaging Settings

| Variable                      | Description                 | Default    |
| ----------------------------- | --------------------------- | ---------- |
| `PIPELINE_GRIDDER`            | Gridding algorithm          | `wproject` |
| `PIPELINE_USE_NVSS_MASK`      | Use NVSS mask (2-4x faster) | `true`     |
| `PIPELINE_MASK_RADIUS_ARCSEC` | Mask radius                 | `60.0`     |

### 1.4 Verification

```bash
# Run health check
./scripts/preflight-check.sh

# Check API status
curl http://localhost:8000/api/status

# Check database connectivity
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 "SELECT COUNT(*) FROM ms_index;"
```

---

## Part 2: Pipeline Operations

### 2.1 Service Management

#### Starting Services

**Production (systemd):**

```bash
# Start all services
sudo systemctl start contimg-api contimg-stream dsa110-contimg-dashboard

# Enable on boot
sudo systemctl enable contimg-api contimg-stream dsa110-contimg-dashboard

# Check status
sudo systemctl status contimg-api contimg-stream
```

**Development (manual):**

```bash
# Terminal 1: API
cd /data/dsa110-contimg/backend/src
uvicorn dsa110_contimg.api.app:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd /data/dsa110-contimg/frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

#### Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION SERVICES                       │
├─────────────────────────────────────────────────────────────┤
│  contimg-api.service          → FastAPI backend      :8000  │
│  dsa110-contimg-dashboard     → Frontend (Vite)      :3210  │
│  contimg-stream.service       → Streaming converter         │
│  contimg-docs.service         → MkDocs server        :8001  │
└─────────────────────────────────────────────────────────────┘
```

#### Viewing Logs

```bash
# Follow service logs
journalctl -u contimg-stream -f --no-pager

# Last 100 lines
journalctl -u contimg-api -n 100 --no-pager

# Logs since specific time
journalctl -u contimg-stream --since "1 hour ago"
```

### 2.2 Streaming Conversion

The streaming converter watches `/data/incoming` for new HDF5 files and automatically converts them to Measurement Sets.

#### Starting the Streaming Converter

```bash
# Via systemd (production)
sudo systemctl start contimg-stream

# Via CLI (development)
python -m dsa110_contimg.conversion.streaming.streaming_converter \
    --input-dir /data/incoming \
    --output-dir /stage/dsa110-contimg/ms \
    --scratch-dir /stage/dsa110-contimg \
    --chunk-duration 5.0 \
    --omp-threads 4
```

#### Monitoring the Queue

```bash
# Check queue status via API
curl http://localhost:8000/api/streaming/status

# Direct database query
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT state, COUNT(*) FROM ingest_queue GROUP BY state;"
```

#### Queue States

| State         | Description                                |
| ------------- | ------------------------------------------ |
| `collecting`  | Accumulating subbands (waiting for all 16) |
| `pending`     | Ready for processing                       |
| `in_progress` | Currently being converted                  |
| `completed`   | Successfully converted                     |
| `failed`      | Conversion failed (check logs)             |

### 2.3 Batch Conversion

For processing historical data or specific time ranges:

```bash
# Convert a time window
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-12-01T00:00:00" \
    "2025-12-01T06:00:00"

# Convert by calibrator transit
python -m dsa110_contimg.conversion.cli groups \
    --calibrator "3C286" \
    /data/incoming \
    /stage/dsa110-contimg/ms

# Dry run (preview without converting)
python -m dsa110_contimg.conversion.cli groups --dry-run \
    /data/incoming /stage/dsa110-contimg/ms \
    "2025-12-01T00:00:00" "2025-12-01T01:00:00"
```

#### CLI Options

| Option                             | Description                             |
| ---------------------------------- | --------------------------------------- |
| `--dry-run`                        | Preview without writing files           |
| `--calibrator NAME`                | Auto-find transit time for calibrator   |
| `--find-only`                      | Find groups/transits without converting |
| `--skip-existing`                  | Skip groups with existing MS files      |
| `--no-rename-calibrator-fields`    | Disable auto calibrator detection       |
| `--writer {parallel-subband,auto}` | MS writing strategy                     |

### 2.4 Monitoring Pipeline Health

#### Prometheus Metrics

Access metrics at: `http://localhost:8000/metrics`

Key metrics:

| Metric                          | Description         |
| ------------------------------- | ------------------- |
| `http_requests_total`           | Total HTTP requests |
| `http_request_duration_seconds` | Request latency     |
| `http_requests_in_progress`     | Active requests     |

#### Grafana Dashboard

Access at: `http://localhost:3030`

Recommended panels:

- Request rate by endpoint
- Latency heatmap
- Error rate (4xx/5xx)
- Memory usage
- Active connections

---

## Part 3: Dashboard

### 3.1 Accessing the Dashboard

| Environment | URL                       |
| ----------- | ------------------------- |
| Production  | http://localhost:3210/ui/ |
| Development | http://localhost:5173     |

### 3.2 Main Dashboard

**URL:** `/dashboard`

Features:

- **Pipeline Status Panel**: Queue statistics, active calibrations, recent observations
- **System Health Panel**: CPU, memory, disk usage
- **ESE Candidates Panel**: Real-time variability alerts (5σ threshold)

### 3.3 Observation Timeline

**URL:** `/observations`

Features:

- Interactive timeline of observations
- Filter by time range, calibrator, status
- Quick access to MS and image files

### 3.4 Image Gallery

**URL:** `/images`

Features:

- Grid view of all images
- Filter by time range, source, quality
- Download FITS files
- Quick preview

### 3.5 Mosaic Gallery

**URL:** `/mosaics`

Features:

- Time-range query interface
- Mosaic metadata (source count, noise, image count)
- Create new mosaics from time ranges
- Download options (FITS, PNG)

### 3.6 Control Panel

**URL:** `/control-panel`

Features:

- Manual pipeline execution
- Calibration controls
- Imaging controls
- Service restart buttons

### 3.7 Running Dashboard Persistently

#### Using tmux (Recommended)

```bash
# Start in tmux session
bash /data/dsa110-contimg/scripts/start-dashboard-tmux.sh

# Attach to session
tmux attach -t dsa110-dashboard

# Detach (keeps running): Ctrl+B, then D
```

#### Using systemd (Production)

```bash
# Install and start service
sudo systemctl enable --now dsa110-contimg-dashboard

# Check status
sudo systemctl status dsa110-contimg-dashboard
```

---

## Part 4: Workflows

### 4.1 Calibration

The pipeline performs bandpass (BP) and gain (G) calibration. K-calibration (delay) is skipped by default for DSA-110.

#### Running Calibration

```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /path/to/observation.ms \
  --field 0 \
  --refant 103
```

#### Calibration Options

| Flag            | Description            | Default  |
| --------------- | ---------------------- | -------- |
| `--do-k`        | Enable K-calibration   | Disabled |
| `--skip-bp`     | Skip bandpass          | Enabled  |
| `--skip-g`      | Skip gain              | Enabled  |
| `--bp-minsnr`   | Bandpass min SNR       | 3.0      |
| `--gain-solint` | Gain solution interval | inf      |

#### Applying Existing Calibration

```bash
python -m dsa110_contimg.calibration.cli apply \
  --ms /path/to/observation.ms \
  --caltable /path/to/calibration.bcal
```

### 4.2 Imaging

#### Basic Imaging

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/observation.ms \
    --imagename /path/to/output.img
```

#### Imaging with NVSS Mask (Faster)

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/observation.ms \
    --imagename /path/to/output.img \
    --mask-radius-arcsec 60.0
```

#### Disable Masking

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/observation.ms \
    --imagename /path/to/output.img \
    --no-nvss-mask
```

### 4.3 Mosaicking

#### Create a Single Mosaic

```bash
python -m dsa110_contimg.mosaic.cli plan \
    --products-db state/db/products.sqlite3 \
    --name night_2025_12_01 \
    --since 2025-12-01T00:00:00 \
    --until 2025-12-01T06:00:00

python -m dsa110_contimg.mosaic.cli build \
    --products-db state/db/products.sqlite3 \
    --name night_2025_12_01 \
    --output /stage/dsa110-contimg/mosaics/night_2025_12_01.img
```

#### Create Mosaic Centered on Calibrator

```bash
python scripts/mosaic/create_mosaic_centered.py \
    --calibrator 0834+555 \
    --timespan-minutes 50
```

#### Batch Mosaic Creation

```bash
#!/bin/bash
# Process multiple calibrators
CALIBRATORS=("0834+555" "3C48" "3C147" "3C286")

for cal in "${CALIBRATORS[@]}"; do
    python scripts/mosaic/create_mosaic_centered.py \
        --calibrator "$cal" \
        --timespan-minutes 50
done
```

### 4.4 Source Extraction

#### Photometry CLI

```bash
# Peak photometry
python -m dsa110_contimg.photometry.cli peak \
    --image /path/to/image.fits \
    --output /path/to/photometry.csv

# Adaptive binning
python -m dsa110_contimg.photometry.cli adaptive \
    --image /path/to/image.fits \
    --output /path/to/photometry.csv
```

---

## Part 5: Advanced Features

### 5.1 ABSURD Workflow Manager

ABSURD provides durable, fault-tolerant task execution with PostgreSQL-backed persistence.

#### Starting the Worker

```bash
# Via systemd
sudo systemctl start contimg-absurd-worker

# Via CLI
python -m dsa110_contimg.absurd.worker \
    --database-url postgresql://user:password@localhost:5432/dsa110_absurd \
    --queue dsa110-pipeline \
    --concurrency 4
```

#### Spawning Tasks

```python
from dsa110_contimg.absurd import AbsurdClient
import asyncio

async def spawn_task():
    client = AbsurdClient('postgresql://user:password@localhost:5432/dsa110_absurd')
    await client.connect()

    task_id = await client.spawn_task(
        queue='dsa110-pipeline',
        task_type='mosaic_build',
        payload={'name': 'night_2025_12_01'},
        priority=10
    )

    await client.close()
    return task_id

asyncio.run(spawn_task())
```

#### API Endpoints

| Endpoint                 | Method | Description       |
| ------------------------ | ------ | ----------------- |
| `/api/absurd/metrics`    | GET    | Real-time metrics |
| `/api/absurd/tasks`      | GET    | List tasks        |
| `/api/absurd/tasks`      | POST   | Spawn new task    |
| `/api/absurd/tasks/{id}` | GET    | Task details      |
| `/api/absurd/tasks/{id}` | DELETE | Cancel task       |

### 5.2 CARTA Integration

CARTA provides interactive FITS visualization.

#### Deploy CARTA Backend

```bash
docker run -d \
  --name carta-backend \
  --restart unless-stopped \
  -p 9002:3002 \
  -v /stage/dsa110-contimg:/stage/dsa110-contimg:ro \
  -v /data/dsa110-contimg:/data/dsa110-contimg:ro \
  cartavis/carta:latest
```

#### Configure Dashboard

Create `frontend/.env`:

```bash
VITE_CARTA_BACKEND_URL=http://localhost:9002
VITE_CARTA_FRONTEND_URL=http://localhost:9002
```

#### Access CARTA

1. Navigate to Dashboard → CARTA (`/carta`)
2. Select integration mode (Iframe recommended)
3. Use File Browser to select FITS file
4. View in CARTA Viewer

### 5.3 Scheduling Pipelines

#### Nightly Mosaic Pipeline

The ABSURD framework supports scheduled pipelines:

```python
from dsa110_contimg.pipeline.mosaic import NightlyMosaicPipeline
from dsa110_contimg.absurd.scheduler import CronTrigger

scheduler.register_pipeline(
    NightlyMosaicPipeline,
    trigger=CronTrigger(cron="0 3 * * *"),  # Daily at 03:00 UTC
    enabled=True
)
```

---

## Part 6: Reference

### 6.1 CLI Commands

| Command                                           | Description     |
| ------------------------------------------------- | --------------- |
| `python -m dsa110_contimg.conversion.cli --help`  | Conversion CLI  |
| `python -m dsa110_contimg.calibration.cli --help` | Calibration CLI |
| `python -m dsa110_contimg.imaging.cli --help`     | Imaging CLI     |
| `python -m dsa110_contimg.mosaic.cli --help`      | Mosaic CLI      |
| `python -m dsa110_contimg.photometry.cli --help`  | Photometry CLI  |

### 6.2 API Endpoints

| Endpoint                    | Method | Description            |
| --------------------------- | ------ | ---------------------- |
| `/api/status`               | GET    | Pipeline status        |
| `/api/streaming/status`     | GET    | Streaming queue status |
| `/api/streaming/start`      | POST   | Start streaming        |
| `/api/streaming/stop`       | POST   | Stop streaming         |
| `/api/data/observations`    | GET    | List observations      |
| `/api/data/images`          | GET    | List images            |
| `/api/mosaic/create`        | POST   | Create mosaic          |
| `/api/mosaic/status/{name}` | GET    | Mosaic status          |

### 6.3 Port Assignments

| Port | Service                | Environment |
| ---- | ---------------------- | ----------- |
| 3000 | Vite dev server        | Development |
| 3210 | Dashboard (production) | Production  |
| 6006 | Storybook              | Development |
| 8000 | FastAPI backend        | Both        |
| 8001 | MkDocs                 | Development |
| 3030 | Grafana                | Production  |
| 9090 | Prometheus             | Production  |
| 9002 | CARTA                  | Both        |

### 6.4 File Locations

| Path                               | Description            |
| ---------------------------------- | ---------------------- |
| `/data/incoming/`                  | Raw HDF5 subband files |
| `/stage/dsa110-contimg/ms/`        | Measurement Sets       |
| `/stage/dsa110-contimg/images/`    | FITS images            |
| `/stage/dsa110-contimg/mosaics/`   | Mosaic products        |
| `/data/dsa110-contimg/state/db/`   | SQLite databases       |
| `/data/dsa110-contimg/state/logs/` | Pipeline logs          |

### 6.5 Database Paths

| Database                                 | Purpose                         |
| ---------------------------------------- | ------------------------------- |
| `state/db/pipeline.sqlite3`              | Unified pipeline database       |
| `state/db/ingest.sqlite3`                | Streaming queue                 |
| `state/db/products.sqlite3`              | MS, images, photometry registry |
| `state/catalogs/vla_calibrators.sqlite3` | VLA calibrator catalog          |

---

## Getting Help

- **Local Docs Search**: `python -m dsa110_contimg.docsearch.cli search "your query"`
- **API Docs**: http://localhost:8000/api/docs
- **GitHub Issues**: https://github.com/dsa110/dsa110-contimg/issues
- **Troubleshooting Guide**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
