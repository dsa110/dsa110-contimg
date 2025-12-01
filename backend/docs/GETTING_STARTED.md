# Getting Started - Developer Guide

Welcome to the DSA-110 Continuum Imaging Pipeline backend. This guide will help
you understand the codebase and start contributing.

## What This Project Does

The DSA-110 is a radio telescope array that produces **visibility data** (raw
correlator output) in HDF5 format. This pipeline:

1. **Converts** UVH5 files → CASA Measurement Sets (MS)
2. **Calibrates** the data using reference calibrators
3. **Images** the calibrated data to produce FITS images
4. **Catalogs** detected sources with photometry
5. **Serves** results via a REST API and web dashboard

```
UVH5 files → Conversion → MS files → Calibration → Imaging → FITS → Catalog
     ↓                                                              ↓
  /data/incoming                                              /stage/products
```

## Environment Setup

**Required**: The `casa6` conda environment with CASA 6.7, pyuvdata, and dependencies.

```bash
# Activate the environment (required for ALL operations)
conda activate casa6

# Verify
python -c "import casatools; print('CASA OK')"
python -c "import pyuvdata; print('pyuvdata OK')"
```

See `ops/docker/environment.yml` for the full dependency list.

## Architecture Overview

![Backend Architecture](backend_architecture.svg)

_Visual diagram of module dependencies and data flow._

## Project Layout

```text
backend/
├── src/dsa110_contimg/     # Main Python package
│   ├── api/                # REST API (FastAPI)
│   ├── conversion/         # UVH5 → MS conversion
│   ├── calibration/        # Calibration routines
│   ├── imaging/            # WSClean/CASA imaging wrappers
│   ├── pipeline/           # Stage-based processing
│   ├── database/           # SQLite helpers
│   ├── catalog/            # Source catalogs (NVSS, FIRST)
│   ├── photometry/         # Source extraction & measurement
│   ├── simulation/         # Synthetic test data generation
│   ├── docsearch/          # Documentation search
│   └── utils/              # Shared utilities
├── tests/                  # Unit and integration tests
├── scripts/                # Utility scripts
└── docs/                   # Documentation
```

## Key Entry Points

### 1. API Server (`api/`)

Start here if you're working on the web interface or REST endpoints.

```bash
# Run the API
python -m uvicorn dsa110_contimg.api.app:app --reload --port 8000

# View interactive docs
open http://localhost:8000/api/docs
```

**Key files:**

- `api/app.py` - FastAPI application factory
- `api/routes/` - Endpoint handlers (images, sources, jobs, etc.)
- `api/repositories.py` - Data access layer
- `api/schemas.py` - Request/response models

### 2. Conversion Pipeline (`conversion/`)

Start here if you're working on data ingestion.

```bash
# Convert a time range of observations
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming /stage/dsa110-contimg/ms \
    "2025-01-01T00:00:00" "2025-01-01T01:00:00"
```

**Key files:**

- `conversion/cli.py` - Command-line interface
- `conversion/strategies/hdf5_orchestrator.py` - Batch conversion logic
- `conversion/streaming/streaming_converter.py` - Real-time daemon
- `conversion/strategies/writers.py` - MS writing strategies

### 3. Pipeline Stages (`pipeline/`)

Start here if you're working on the processing workflow.

**Key files:**

- `pipeline/stages.py` - Stage definitions
- `pipeline/stages_impl.py` - Stage implementations
- `pipeline/coordinator.py` - Pipeline orchestration

### 4. Calibration (`calibration/`)

Start here if you're working on data calibration.

**Key files:**

- `calibration/bandpass.py` - Bandpass calibration
- `calibration/field_naming.py` - Calibrator field detection
- `calibration/calibrator_registry.py` - Known calibrators database

## Running Tests

```bash
cd /data/dsa110-contimg/backend
conda activate casa6

# Unit tests (fast, no CASA required for most)
python -m pytest tests/unit/ -v

# Specific test file
python -m pytest tests/unit/api/test_query_batch.py -v

# Integration tests (requires CASA)
python -m pytest tests/integration/ -v
```

## Common Development Tasks

### Adding a New API Endpoint

1. Define the Pydantic schema in `api/schemas.py`
2. Add the route handler in `api/routes/{resource}.py`
3. Add repository method in `api/repositories.py` if needed
4. Write tests in `tests/unit/api/`

### Adding a New Pipeline Stage

1. Define the stage in `pipeline/stages.py`
2. Implement in `pipeline/stages_impl.py`
3. Register in the coordinator

### Modifying Conversion Logic

1. Make changes in `conversion/` module
2. Test with synthetic data:

   ```bash
   python -m dsa110_contimg.simulation.generate_uvh5 --output-dir /tmp/test
   ```

3. Run conversion on test data

## Database Configuration

The backend supports SQLite (default) and PostgreSQL.

```bash
# Check current backend
echo $DSA110_DB_BACKEND

# Use PostgreSQL (production)
source .env  # Sets DSA110_DB_BACKEND=postgresql
```

See `docs/postgresql-deployment.md` for PostgreSQL setup.

## Debugging Tips

### Check logs

```bash
tail -f /data/dsa110-contimg/state/logs/conversion.log
```

### Run with verbose output

```bash
python -m dsa110_contimg.conversion.cli groups --dry-run ...
```

### Interactive exploration

```python
from dsa110_contimg.utils import FastMeta

with FastMeta("/path/to/file.hdf5") as meta:
    print(meta.time_array)
    print(meta.freq_array)
```

## Next Steps

1. **Read the architecture docs**: `docs/ARCHITECTURE.md`
2. **Explore the API**: Run the server and browse `/api/docs`
3. **Run the tests**: Get familiar with the test patterns
4. **Pick an issue**: Check `TODO.md` or GitHub issues

## Getting Help

- **Documentation search**: `python -m dsa110_contimg.docsearch.cli search "topic"`
- **Project docs**: `/data/dsa110-contimg/docs/`
- **Module docstrings**: Most functions have detailed docstrings
