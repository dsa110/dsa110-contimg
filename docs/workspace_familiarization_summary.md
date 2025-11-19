# DSA-110 Continuum Imaging Pipeline - Workspace Familiarization Summary

**Generated:** 2025-11-18  
**Purpose:** Quick reference for understanding and operating the DSA-110
pipeline

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Directory Architecture](#directory-architecture)
3. [Pipeline Stages](#pipeline-stages)
4. [Current System Status](#current-system-status)
5. [Running the Pipeline](#running-the-pipeline)
6. [Key Commands](#key-commands)
7. [Important Files](#important-files)
8. [Development Environment](#development-environment)

---

## System Overview

The DSA-110 Continuum Imaging Pipeline is a **streaming radio astronomy data
processing system** that:

- **Ingests** raw visibility data in UVH5/HDF5 format (16 subbands per
  observation)
- **Converts** to CASA Measurement Sets (MS)
- **Calibrates** using reference sources with CASA calibration tasks
- **Images** calibrated data to produce continuum images
- **Cross-matches** sources with reference catalogs (NVSS, VLASS)
- **Performs photometry** on detected sources
- **Monitors** pipeline status via REST API and web dashboard

**Key Technologies:**

- **Python 3.11** in `casa6` conda environment (`/opt/miniforge/envs/casa6`)
- **CASA 6** for radio astronomy tasks (calibration, imaging)
- **pyuvdata** for UVH5 → MS conversion
- **FastAPI** for monitoring API (running on port 8000)
- **SQLite** for state management and data registry
- **Absurd** workflow manager for durable task execution
- **React** frontend for monitoring dashboard

---

## Directory Architecture

### Code Repository: `/data/dsa110-contimg/`

```
/data/dsa110-contimg/
├── src/dsa110_contimg/        # Python package
│   ├── conversion/            # UVH5 → MS conversion
│   ├── calibration/           # CASA calibration (K/BP/G solutions)
│   ├── imaging/               # WSClean/CASA imaging
│   ├── photometry/            # Adaptive photometry
│   ├── catalog/               # Catalog management
│   ├── pipeline/              # Pipeline orchestration framework
│   ├── absurd/                # Absurd workflow integration
│   ├── api/                   # FastAPI monitoring endpoints
│   ├── qa/                    # Quality assurance
│   └── database/              # SQLite helpers
├── state/                     # Persistent SQLite databases
│   ├── ingest.sqlite3         # Queue state (428 KB)
│   ├── products.sqlite3       # Image/MS catalog (792 KB)
│   ├── cal_registry.sqlite3   # Calibration table registry (24 KB)
│   ├── master_sources.sqlite3 # Source catalog (108 MB)
│   └── hdf5.sqlite3           # HDF5 file index (33 MB)
├── ops/                       # Deployment configs
│   ├── systemd/               # systemd service units
│   └── docker/                # Docker Compose setup
├── scripts/                   # Operational scripts
│   ├── absurd/                # Absurd workflow scripts
│   ├── dev/                   # Development setup scripts
│   └── casa/                  # CASA wrapper scripts
├── docs/                      # Documentation
├── tests/                     # Test suite
└── frontend/                  # React monitoring dashboard
```

### Data Storage: `/stage/dsa110-contimg/` (Fast SSD)

```
/stage/dsa110-contimg/
├── incoming/                  # Raw UVH5 files (watched by pipeline)
├── ms/                        # Measurement Sets & calibration tables
│   ├── calibrators/YYYY-MM-DD/  # Calibrator observations
│   ├── science/YYYY-MM-DD/      # Science observations
│   └── failed/YYYY-MM-DD/       # Failed conversions
├── images/                    # Individual image products
├── mosaics/                   # Mosaic images
├── static/                    # Static reference data
│   ├── beam-model/            # DSA-110 beam model (517 MB)
│   └── catalogs/              # Reference catalogs
└── tmp/                       # Transient files
```

### Raw Data Ingest: `/data/incoming/`

- Contains raw UVH5 subband files: `YYYY-MM-DDTHH:MM:SS_sbNN.hdf5`
- Watched by streaming converter
- Files grouped by timestamp (16 subbands per observation)

### Temporary Staging: `/dev/shm/` (tmpfs - 47 GB available)

- Used for fast I/O during MS conversion
- Provides 3-5x speedup over SSD-only writes
- Auto-cleaned after atomic move to final location

---

## Pipeline Stages

The pipeline consists of **9 main stages**, all executable as durable Absurd
tasks:

### 1. **Catalog Setup Stage**

- **Purpose:** Prepare reference catalogs (NVSS, VLASS) for cross-matching
- **Implementation:** `CatalogSetupStage` in `pipeline/stages_impl.py`
- **Outputs:** Catalog databases in `state/`

### 2. **Conversion Stage**

- **Purpose:** Convert UVH5 → Measurement Sets
- **Implementation:** `ConversionStage` using `hdf5_orchestrator`
- **Strategies:**
  - `parallel-subband` (PRODUCTION, 16 subbands)
  - `pyuvdata` (TESTING, ≤2 subbands)
- **Features:** tmpfs staging, parallel processing
- **Output:** `ms/science/YYYY-MM-DD/<timestamp>.ms/`

### 3. **Calibration Solve Stage**

- **Purpose:** Derive calibration solutions from calibrator observations
- **Implementation:** `CalibrationSolveStage`
- **Calibration Types:**
  - K: Delay calibration
  - BP: Bandpass calibration
  - G: Gain calibration (phase + amplitude)
- **Output:** Calibration tables registered in `cal_registry.sqlite3`

### 4. **Calibration Apply Stage**

- **Purpose:** Apply calibration solutions to science targets
- **Implementation:** `CalibrationStage`
- **Output:** MS with `CORRECTED_DATA` column populated

### 5. **Imaging Stage**

- **Purpose:** Generate continuum images from calibrated MS
- **Implementation:** `ImagingStage`
- **Imager:** WSClean (CASA also supported)
- **Modes:** Quick-look (imsize≤512) or Full quality
- **Output:** `images/<timestamp>.img-*.fits`

### 6. **Organization Stage**

- **Purpose:** Organize products and update database indices
- **Implementation:** `OrganizationStage`
- **Actions:** Move files to organized locations, update `ms_index`

### 7. **Validation Stage** _(Optional)_

- **Purpose:** Quality assurance checks on images
- **Implementation:** `ValidationStage`
- **Checks:** Noise levels, beam properties, WCS validity

### 8. **Cross-Match Stage** _(Optional)_

- **Purpose:** Match detected sources with reference catalogs
- **Implementation:** `CrossMatchStage`
- **Catalogs:** NVSS, VLASS, FIRST
- **Output:** Source associations in database

### 9. **Adaptive Photometry Stage** _(Optional)_

- **Purpose:** Measure fluxes of known sources
- **Implementation:** `AdaptivePhotometryStage`
- **Methods:** Aperture photometry, PSF fitting
- **Output:** Photometry database entries

---

## Current System Status

### ✅ **Services Running**

```bash
# API Server (Port 8000)
systemctl status contimg-api.service
# Status: Active (running) since 2025-11-18 03:08:10
# URL: http://localhost:8000
```

**Health Check:**

```json
{
  "status": "healthy",
  "databases": {
    "queue": "accessible",
    "products": "accessible",
    "registry": "accessible"
  },
  "disk": {
    "free_gb": 1089.44,
    "total_gb": 13038.97
  }
}
```

### 📊 **Databases Present**

- ✅ `ingest.sqlite3` (428 KB) - Queue state
- ✅ `products.sqlite3` (792 KB) - Image/MS catalog
- ✅ `cal_registry.sqlite3` (24 KB) - Calibration registry
- ✅ `master_sources.sqlite3` (108 MB) - Source catalog
- ✅ `hdf5.sqlite3` (33 MB) - HDF5 file index

### 📁 **Data Available**

- ✅ Raw UVH5 files in `/data/incoming/`
- ✅ Static beam model (517 MB) in `/stage/dsa110-contimg/static/beam-model/`

### 🔧 **Python Environment**

```bash
$ which python
/opt/miniforge/envs/casa6/bin/python

$ python --version
Python 3.11.13

# Pipeline stages import successfully
$ python -c "from dsa110_contimg.pipeline.stages_impl import *; print('✓')"
✓
```

---

## Running the Pipeline

### Method 1: Using the Orchestrator CLI (Batch Processing)

**Convert UVH5 to MS for a time range:**

```bash
# Navigate to repository
cd /data/dsa110-contimg

# Convert all observations in a time window
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-11-07 00:00:00" \
    "2025-11-07 12:00:00" \
    --writer parallel-subband \
    --stage-to-tmpfs \
    --max-workers 4
```

**Options:**

- `--writer parallel-subband` - Production writer (16 subbands)
- `--stage-to-tmpfs` - Use tmpfs for fast I/O (default: enabled)
- `--max-workers 4` - Parallel subband processing
- `--dry-run` - Preview what would be processed
- `--find-only` - List groups without processing

### Method 2: Using Absurd Workflow Manager (Recommended for Production)

**Start Absurd Worker:**

```bash
# 1. Setup Absurd database (one-time)
./scripts/absurd/setup_absurd_db.sh

# 2. Create queues
./scripts/absurd/create_absurd_queues.sh

# 3. Start worker
python scripts/absurd/start_worker.py
```

**Submit Pipeline Tasks via API:**

```python
import requests

# Submit conversion task
response = requests.post("http://localhost:8000/api/absurd/tasks", json={
    "task_name": "convert-uvh5-to-ms",
    "params": {
        "config": {
            "paths": {
                "incoming": "/data/incoming",
                "staging": "/stage/dsa110-contimg",
                "products": "/data/dsa110-contimg/products"
            }
        },
        "inputs": {
            "input_path": "/data/incoming/2025-11-07T12:10:54_sb*.hdf5",
            "start_time": "2025-11-07T12:10:54",
            "end_time": "2025-11-07T12:15:54"
        }
    }
})

task = response.json()
print(f"Task ID: {task['task_id']}")

# Check task status
status = requests.get(f"http://localhost:8000/api/absurd/tasks/{task['task_id']}")
print(status.json())
```

### Method 3: Using systemd Services (Streaming Mode)

**For continuous operation:**

```bash
# Start streaming worker (watches /data/incoming/)
sudo systemctl start contimg-stream.service

# Monitor logs
journalctl -u contimg-stream.service -f
```

**Configuration:** Edit `/data/dsa110-contimg/ops/systemd/contimg.env`

---

## Key Commands

### Development Setup

```bash
# Setup development environment
./scripts/dev/setup-dev.sh

# Check environment
./scripts/dev/check-environment.sh

# Run tests
pytest tests/
```

### Pipeline Operations

```bash
# List available groups for conversion
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming /stage/dsa110-contimg/ms \
    "2025-11-07 00:00:00" "2025-11-07 23:59:59" \
    --find-only

# Check queue status
sqlite3 state/ingest.sqlite3 "SELECT * FROM ingest_queue ORDER BY start_time DESC LIMIT 10;"

# Check products
sqlite3 state/products.sqlite3 "SELECT path, stage, status FROM ms_index ORDER BY processed_at DESC LIMIT 10;"

# View calibration registry
python -m dsa110_contimg.database.registry_cli list

# Monitor API health
curl http://localhost:8000/api/health | jq

# View recent groups
curl http://localhost:8000/api/status/recent | jq
```

### Monitoring & Debugging

```bash
# Check systemd services
systemctl status contimg-api.service
systemctl status contimg-stream.service

# View logs
journalctl -u contimg-api.service -f
journalctl -u contimg-stream.service -f

# Monitor disk usage
df -h /stage/dsa110-contimg/
df -h /data/dsa110-contimg/
df -h /dev/shm/

# Check tmpfs staging
ls -lah /dev/shm/dsa110-contimg/
```

---

## Important Files

### Configuration Files

- **`ops/systemd/contimg.env`** - Environment variables for services
- **`pyproject.toml`** - Python project configuration
- **`config/ports.yaml`** - Port allocation scheme

### Documentation Entry Points

- **`README.md`** - Main project README with quick start
- **`docs/index.md`** - Documentation hub
- **`docs/how-to/operating_absurd_pipeline.md`** - Absurd workflow guide
- **`docs/how-to/batch_mode_guide.md`** - Batch processing guide
- **`docs/concepts/DIRECTORY_ARCHITECTURE.md`** - Directory structure
- **`docs/concepts/pipeline_workflow_visualization.md`** - Pipeline diagrams
- **`docs/indices/PIPELINE_STAGES_INDEX.md`** - Stage documentation index

### Key Scripts

- **`scripts/absurd/quickstart.sh`** - Absurd quick start
- **`scripts/dev/developer-setup.sh`** - Developer environment setup
- **`scripts/monitor-services.sh`** - Service monitoring

---

## Development Environment

### Python Environment Setup

**CRITICAL:** Always use the `casa6` conda environment:

```bash
# Activate casa6 environment
source /data/dsa110-contimg/scripts/dev/developer-setup.sh

# Or directly use the Python interpreter
/opt/miniforge/envs/casa6/bin/python script.py
```

### Environment Variables (from `contimg.env`)

```bash
# Core paths
CONTIMG_INPUT_DIR=/data/incoming
CONTIMG_OUTPUT_DIR=/stage/dsa110-contimg/ms
CONTIMG_SCRATCH_DIR=/stage/dsa110-contimg

# Databases
CONTIMG_QUEUE_DB=/data/dsa110-contimg/state/ingest.sqlite3
CONTIMG_REGISTRY_DB=/data/dsa110-contimg/state/cal_registry.sqlite3
CONTIMG_PRODUCTS_DB=/data/dsa110-contimg/state/products.sqlite3

# Threading (important for CASA stability)
OMP_NUM_THREADS=4
MKL_NUM_THREADS=4
HDF5_USE_FILE_LOCKING=FALSE

# Temporary files
TMPDIR=/stage/dsa110-contimg/tmp
CASA_TMPDIR=/stage/dsa110-contimg/tmp
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test suite
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest --cov=src/dsa110_contimg tests/
```

---

## Quick Start Example

Here's a complete example workflow:

```bash
# 1. Check system status
curl http://localhost:8000/api/health | jq

# 2. Find available groups
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming /stage/dsa110-contimg/ms \
    "2025-11-07 12:00:00" "2025-11-07 13:00:00" \
    --find-only

# Output example:
# Found 3 complete groups:
#   2025-11-07T12:10:54 (16 subbands)
#   2025-11-07T12:15:59 (16 subbands)
#   2025-11-07T12:21:04 (16 subbands)

# 3. Convert a specific group
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming /stage/dsa110-contimg/ms \
    "2025-11-07 12:10:00" "2025-11-07 12:11:00" \
    --writer parallel-subband \
    --stage-to-tmpfs

# 4. Check conversion results
ls -lh /stage/dsa110-contimg/ms/science/2025-11-07/

# 5. View products database
sqlite3 state/products.sqlite3 \
    "SELECT path, stage, status FROM ms_index WHERE path LIKE '%2025-11-07%';"

# 6. Monitor via API
curl http://localhost:8000/api/status/recent | jq
```

---

## Additional Resources

### API Endpoints

- **Health:** `GET /api/health`
- **Status:** `GET /api/status`
- **Recent Groups:** `GET /api/status/recent`
- **MS Index:** `GET /api/ms_index?stage=&status=&limit=`
- **Products:** `GET /api/products`
- **Absurd Tasks:** `POST /api/absurd/tasks`
- **Absurd Status:** `GET /api/absurd/tasks/{task_id}`

### Web Dashboard

- **URL:** http://localhost:3210 (if running)
- **Development:** http://localhost:5173 (Vite dev server)

### Support & Documentation

- **Issue Tracker:** Check `docs/dev/status/` for status reports
- **How-To Guides:** `docs/how-to/`
- **Concepts:** `docs/concepts/`
- **Reference:** `docs/reference/`
- **Troubleshooting:** `docs/how-to/troubleshooting.md`

---

**Last Updated:** 2025-11-18  
**System Version:** 0.1.0  
**Python Environment:** `/opt/miniforge/envs/casa6` (Python 3.11.13)
