# DSA-110 Workspace Quick Reference

**Last Updated**: 2025-11-18

---

## TL;DR

**What**: Radio astronomy continuum imaging pipeline for DSA-110 telescope  
**Language**: Python 3.11.13 (CASA 6.7 required)  
**Architecture**: 9-stage pipeline with SQLite state management  
**Modes**: Streaming (continuous) or Batch (explicit jobs)  
**Status**: Production-ready

---

## Essential Paths

```
Code:           /data/dsa110-contimg/src/
Docs:           /data/dsa110-contimg/docs/
State DBs:      /data/dsa110-contimg/state/
Incoming Data:  /data/incoming/
Staging (SSD):  /stage/dsa110-contimg/  (1 TB)
Products (HDD): /data/dsa110-contimg/products/  (13 TB)
```

---

## Quick Start

### 1. Setup Environment

```bash
source /data/dsa110-contimg/scripts/dev/developer-setup.sh
# Activates: /opt/miniforge/envs/casa6 (Python 3.11.13)
```

### 2. Start Pipeline (Streaming Mode)

```bash
# Terminal 1: HDF5 → MS conversion
cd /data/dsa110-contimg/src
dsa110-contimg-convert-stream \
  --input-dir /data/incoming/ \
  --output-dir /stage/dsa110-contimg/ms/

# Terminal 2: Mosaic orchestration
dsa110-contimg-streaming-mosaic --loop

# Terminal 3 (optional): API server
uvicorn dsa110_contimg.api.routes:app --host 0.0.0.0 --port 8000
```

---

## Core Modules

| Module         | Purpose                  | Key Files                           |
| -------------- | ------------------------ | ----------------------------------- |
| `conversion/`  | HDF5 → MS                | `uvh5_to_ms.py`, `cli.py`           |
| `calibration/` | CASA calibration         | `cli.py`, `calibration.py`          |
| `imaging/`     | CASA imaging             | `cli.py`, `spw_imaging.py`          |
| `mosaic/`      | Mosaic creation          | `orchestrator.py`, `cli.py`         |
| `database/`    | SQLite state             | `products.py`, `registry.py`        |
| `api/`         | REST API                 | `routes.py`, `routers/`             |
| `pipeline/`    | Multi-stage orchestrator | `orchestrator.py`, `stages_impl.py` |
| `absurd/`      | Workflow manager         | `client.py`, `worker.py`            |

---

## Database Files (state/)

| Database                 | Purpose                    |
| ------------------------ | -------------------------- |
| `products.sqlite3`       | MS index, images, mosaics  |
| `ingest.sqlite3`         | HDF5 ingestion queue       |
| `hdf5.sqlite3`           | HDF5 file index            |
| `cal_registry.sqlite3`   | Calibration table registry |
| `calibrators.sqlite3`    | Calibrator catalog         |
| `data_registry.sqlite3`  | Data publishing tracker    |
| `master_sources.sqlite3` | Cross-matched sources      |

---

## CLI Commands

### Conversion

```bash
dsa110-convert single --input file.uvh5 --output file.ms
dsa110-convert groups --input-dir /data/incoming --output-dir /stage/ms
```

### Calibration

```bash
dsa110-calibrate calibrate --ms cal.ms --field calibrator --refant ea01
dsa110-calibrate apply --ms science.ms --tables kcal bpcal gpcal
```

### Imaging

```bash
dsa110-image tclean --ms science.ms --output science.image
```

### Mosaic

```bash
dsa110-mosaic plan --name test --since 1700000000 --until 1700100000
dsa110-mosaic build --name test --output mosaic.image
```

### Registry

```bash
dsa110-registry discover --scan-dir /stage/dsa110-contimg/ms
```

### QA

```bash
python -m dsa110_contimg.qa.cli calibration --ms-path obs.ms
python -m dsa110_contimg.qa.cli image --image-path image.fits
python -m dsa110_contimg.qa.cli mosaic --mosaic-id mosaic_2025-11-12
```

---

## Pipeline Stages

1. **File Ingestion** - Detect & register HDF5 files
2. **MS Conversion** - HDF5 → MeasurementSet
3. **Group Formation** - Group 10 MS files
4. **Calibration Solving** - Derive BP/gain solutions
5. **Calibration Application** - Apply corrections
6. **Imaging** - Create individual images
7. **Mosaic Creation** - Combine images
8. **Cross-Matching** - Match to catalogs (optional)
9. **Publishing** - Move to products directory

---

## Key Configuration

### Environment Variables

```bash
export PIPELINE_STATE_DIR="/data/dsa110-contimg/state"
export PYTHONPATH="/data/dsa110-contimg:$PYTHONPATH"

# Optional
export ABSURD_ENABLED="true"
export ABSURD_DATABASE_URL="postgresql://postgres@localhost/dsa110_absurd"
export CAL_REGISTRY_DB="/data/dsa110-contimg/state/cal_registry.sqlite3"
```

### Calibration Frequency (Streaming)

- **Bandpass**: Every 24 hours
- **Gain**: Every hour

### Default Imaging Parameters

- Image size: 1024×1024 pixels
- Weighting: Briggs (robust=0.5)
- Deconvolver: Hogbom
- Iterations: 1000

---

## API Endpoints

**Base URL**: `http://localhost:8000/api/`

| Endpoint             | Method | Purpose           |
| -------------------- | ------ | ----------------- |
| `/status`            | GET    | Pipeline health   |
| `/jobs/`             | POST   | Submit batch job  |
| `/jobs/`             | GET    | List jobs         |
| `/mosaics/`          | GET    | List mosaics      |
| `/images/{id}`       | GET    | Image metadata    |
| `/catalogs/sources`  | GET    | Query sources     |
| `/absurd/tasks`      | POST   | Spawn Absurd task |
| `/absurd/tasks/{id}` | GET    | Task status       |

---

## Monitoring

### Database Queries

```bash
# Check ingest queue
sqlite3 state/ingest.sqlite3 \
  "SELECT COUNT(*) FROM ingest_queue WHERE state='pending'"

# MS status
sqlite3 state/products.sqlite3 \
  "SELECT status, COUNT(*) FROM ms_index GROUP BY status"

# Mosaic groups
sqlite3 state/products.sqlite3 \
  "SELECT status, COUNT(*) FROM mosaic_groups GROUP BY status"
```

### API Monitoring

```bash
curl http://localhost:8000/api/status
curl http://localhost:8000/api/jobs/
curl http://localhost:8000/api/queue/stats
```

---

## Common Tasks

### Publish Mosaic Manually

```bash
python -m dsa110_contimg.database.cli publish \
  --db state/products.sqlite3 \
  --data-id mosaic_2025-11-12_10-00-00
```

### Organize CASA Logs

```bash
./scripts/organize_casa_logs.sh
./scripts/cleanup_casa_logs.py --days 7
```

### Check Job Status

```bash
./scripts/check_job_status.sh
```

---

## Troubleshooting

### Wrong Python Version

```
CRITICAL ERROR: Wrong Python Version
Required: Python 3.11.13 (casa6)
```

**Fix**: Source developer setup

```bash
source /data/dsa110-contimg/scripts/dev/developer-setup.sh
```

### Database Locked

```
sqlite3.OperationalError: database is locked
```

**Fix**: Check for hanging processes, wait for WAL checkpoint

### Phase Centers Incoherent

```
Phase centers are incoherent... Maximum separation: 2000 arcsec
```

**This is EXPECTED** - Time-dependent phasing (meridian-tracking)

### Missing Calibration Tables

```
No active calibration tables found for time window
```

**Fix**: Run calibration or check `cal_registry.sqlite3`

---

## Documentation Map

| Topic                | Document                                             |
| -------------------- | ---------------------------------------------------- |
| Pipeline overview    | `README_PIPELINE_DOCUMENTATION.md`                   |
| Workflow details     | `WORKFLOW_THOUGHT_EXPERIMENT.md`                     |
| Default parameters   | `DEFAULTS_AND_MINIMAL_INPUT.md`                      |
| Execution modes      | `EXECUTION_THEMES.md`                                |
| Conversion guide     | `conversion/README.md`                               |
| Semi-complete groups | `conversion/SEMI_COMPLETE_SUBBAND_GROUPS.md`         |
| Calibration guide    | `calibration/README.md`                              |
| Absurd integration   | `absurd/README.md`                                   |
| Directory layout     | `docs/concepts/DIRECTORY_ARCHITECTURE.md`            |
| Comprehensive study  | `docs/dev/analysis/workspace_comprehensive_study.md` |

---

## Testing

### Run Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Specific marker
pytest -m unit
pytest -m integration
pytest -m casa
```

### Test Markers

- `unit` - Fast, isolated
- `integration` - Require external resources
- `casa` - Require CASA environment
- `slow` - Long-running
- `synthetic` - Use synthetic data
- `science` - Science validation

---

## Dependencies

### Core Runtime

- CASA 6.7 (casatools, casatasks, casacore)
- Python 3.11.13
- Astropy, NumPy, SciPy, Pandas
- PyUVData (HDF5 reading)
- FastAPI, Uvicorn
- Pydantic, Click
- asyncpg (Absurd integration)

### Optional

- ragavi (QA visualization)
- healpy (HEALPix maps)
- pygdsm (Global Sky Model)

### Install

```bash
# Activate casa6 environment
conda activate casa6

# Install package
cd /data/dsa110-contimg
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

---

## Project Entry Points

Defined in `pyproject.toml` under `[project.scripts]`:

```
dsa110-convert
dsa110-calibrate
dsa110-image
dsa110-mosaic
dsa110-photometry
dsa110-registry
dsa110-contimg-convert-stream
dsa110-contimg-streaming-mosaic
```

---

## Useful Scripts

| Script                                | Purpose               |
| ------------------------------------- | --------------------- |
| `scripts/dev/developer-setup.sh`      | Setup environment     |
| `scripts/setup_absurd.sh`             | Setup Absurd database |
| `scripts/organize_casa_logs.sh`       | Organize CASA logs    |
| `scripts/cleanup_casa_logs.py`        | Clean old logs        |
| `scripts/check_job_status.sh`         | Check job status      |
| `scripts/python_environment_audit.py` | Audit Python env      |

---

## Architecture Highlights

### Idempotent Operations

All stages check database state before reprocessing:

- MS conversion checks if MS exists
- Calibration checks if already applied
- Imaging checks if image exists
- Mosaic checks if already created

### Database-Backed State

- WAL mode enabled (concurrent access)
- Atomic transactions
- Path validation before file operations
- Retry logic for transient failures

### Auto-Publishing

Criteria:

- `auto_publish_enabled=1`
- `qa_status='passed'`
- `validation_status='validated'`
- `finalization_status='finalized'`
- Photometry completed (if enabled)

### Time-Dependent Phasing

Phase centers track LST throughout observation:

- **Expected**: Phase center separations of 100s-1000s arcsec
- **Normal**: Separation ≈ LST change × 15°/hour
- **Not a bug**: This is correct meridian-tracking behavior

---

## Contacts & Resources

**Project**: DSA-110 Continuum Imaging Pipeline  
**Institution**: Caltech/OVRO  
**Repository**: `dsa110/dsa110-contimg`  
**Primary Documentation**: `/data/dsa110-contimg/docs/`

---

**Quick Reference Version**: 1.0  
**See Also**: `workspace_comprehensive_study.md` for full details
