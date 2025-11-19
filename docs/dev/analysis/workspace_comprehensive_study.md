# DSA-110 Continuum Imaging Pipeline: Comprehensive Workspace Study

**Generated**: 2025-11-18  
**Purpose**: Complete architectural and organizational overview of the
dsa110-contimg workspace

---

## Executive Summary

The **DSA-110 Continuum Imaging Pipeline** is a production-ready, radio
astronomy data processing system designed for continuous observation processing
at the Deep Synoptic Array (DSA-110) telescope. The pipeline processes raw
visibility data (HDF5/UVH5 format) through a 9-stage workflow culminating in
calibrated, science-ready continuum images and mosaics.

### Key Characteristics

- **Technology Stack**: Python 3.11.13, CASA 6.7, FastAPI, SQLite, asyncpg
  (Absurd integration)
- **Operational Modes**: Streaming (daemon) and Batch (explicit job submission)
- **Architecture**: Multi-stage pipeline with database-backed state persistence
- **Scale**: Processes ~16 subbands per observation, creates 10-MS mosaics every
  ~50 minutes
- **Status**: Production-ready (all 24 identified "icebergs" fixed)

---

## 1. Workspace Organization

### 1.1 Root Structure

```
/data/dsa110-contimg/
├── src/                          # Main source code
├── docs/                         # Comprehensive documentation
├── state/                        # SQLite databases and cached state
├── pyproject.toml                # Project configuration
└── bindings/                     # External language bindings (EveryBeam)

/data/incoming/                   # Streaming HDF5 input data
/stage/dsa110-contimg/            # SSD staging (1 TB)
└── ms/                           # Converted Measurement Sets
└── images/                       # Individual images
└── mosaics/                      # Staged mosaics

/data/dsa110-contimg/products/    # HDD published products (13 TB)
└── mosaics/                      # Published mosaics
└── images/                       # Published images
```

### 1.2 Source Code Structure

```
src/dsa110_contimg/
├── conversion/          # HDF5 → MS conversion
├── calibration/         # Bandpass & gain calibration (CASA-based)
├── imaging/             # CASA imaging (tclean/wsclean)
├── mosaic/              # Mosaic creation & validation
├── photometry/          # Source detection & photometry
├── pipeline/            # Generic multi-stage orchestrator
├── database/            # SQLite state management
├── api/                 # FastAPI REST API & UI backend
├── absurd/              # Durable workflow manager integration
├── catalog/             # Astronomical catalog management
├── pointing/            # Telescope pointing tracking
├── qa/                  # Quality assurance tools
├── simulation/          # Synthetic data generation
├── utils/               # Shared utilities
└── frontend/            # React-based web UI
```

---

## 2. Pipeline Architecture

### 2.1 The Nine Processing Stages

1. **File Ingestion** - HDF5 files detected and registered in database
2. **MS Conversion** - HDF5 → CASA MeasurementSet with phasing
3. **Group Formation** - 10 MS files grouped chronologically
4. **Calibration Solving** - Bandpass & gain solutions derived
5. **Calibration Application** - Corrections applied to all MS files
6. **Imaging** - Individual images created from each MS
7. **Mosaic Creation** - Images combined into single mosaic
8. **Cross-Matching** - (Optional) Sources matched to catalogs
9. **Registration & Publishing** - Mosaic registered and moved to products

### 2.2 State Management

#### SQLite Databases (in `/data/dsa110-contimg/state/`)

- **`products.sqlite3`** - MS index, images, mosaics, mosaic_groups
- **`ingest.sqlite3`** - HDF5 ingestion queue, subband files
- **`hdf5.sqlite3`** - HDF5 file index for fast queries
- **`cal_registry.sqlite3`** - Calibration table validity windows
- **`calibrators.sqlite3`** - Calibrator source catalog
- **`data_registry.sqlite3`** - Data publishing & QA status tracking
- **`ingest_queue.sqlite3`** - Conversion worker queue
- **`master_sources.sqlite3`** - Cross-matched source catalog

#### Database Features

- **WAL Mode**: Enabled for concurrent read/write access
- **Idempotent Operations**: All stages check database before reprocessing
- **Atomic Transactions**: State changes are transactional
- **Path Validation**: File existence verified before processing

### 2.3 Execution Themes

#### Theme 1: Continuous Streaming (Production)

Long-running daemons that automatically process incoming data:

```bash
# Terminal 1: HDF5 conversion
dsa110-contimg-convert-stream \
  --input-dir /data/incoming/ \
  --output-dir /stage/dsa110-contimg/ms/

# Terminal 2: Mosaic orchestration
dsa110-contimg-streaming-mosaic --loop
```

- **Use Case**: Production observatory with continuous observations
- **Characteristics**: Hands-off, automatic, eventually consistent
- **Polling**: Checks every 5-60 seconds for new data

#### Theme 2: Explicit Batch Processing (Research)

User-submitted jobs via CLI or REST API:

```bash
# Create mosaic for specific time window
dsa110-contimg-mosaic plan \
  --name analysis \
  --since 1700000000 \
  --until 1700100000

dsa110-contimg-mosaic build \
  --name analysis \
  --output /data/output.image
```

- **Use Case**: Research analysis, reprocessing, custom parameters
- **Characteristics**: Deterministic, fine-grained control, explicit submission

---

## 3. Key Technologies & Dependencies

### 3.1 Core Dependencies

- **CASA 6.7**: Radio interferometry calibration & imaging
  - `casatools`, `casatasks`, `casacore`
  - Python 3.11.13 (casa6 conda environment)
- **PyUVData**: UVH5 file reading/writing
- **Astropy**: Astronomical calculations, FITS handling, coordinates
- **NumPy/SciPy**: Numerical computations
- **FastAPI/Uvicorn**: REST API server
- **Pydantic**: Data validation & settings management
- **Click**: CLI framework
- **asyncpg**: PostgreSQL async driver (for Absurd)

### 3.2 Environment

**CRITICAL**: Pipeline MUST run in casa6 conda environment:

```bash
source /data/dsa110-contimg/scripts/dev/developer-setup.sh
# Activates: /opt/miniforge/envs/casa6 (Python 3.11.13)
```

Package enforces this at import time via `__init__.py` version guard.

### 3.3 CLI Entry Points

Defined in `pyproject.toml`:

- `dsa110-convert` - HDF5 to MS conversion
- `dsa110-calibrate` - Calibration CLI
- `dsa110-image` - Imaging CLI
- `dsa110-mosaic` - Mosaic creation & planning
- `dsa110-photometry` - Source detection & photometry
- `dsa110-registry` - Data registry management
- `dsa110-contimg-convert-stream` - Streaming converter daemon
- `dsa110-contimg-streaming-mosaic` - Streaming mosaic daemon

---

## 4. Data Flow & Processing

### 4.1 UVH5 → MS Conversion

**Key Features**:

- **Time-dependent phasing**: Phase centers track LST (meridian-tracking)
- **Semi-complete group support**: Accepts 12-16 subbands (was 16/16 only)
- **Synthetic subband generation**: Missing subbands filled with flagged data
- **Phase center incoherence**: Expected behavior (not a bug!)

**Writer Strategies**:

- **Monolithic**: Single MS with all subbands (≤2 subbands)
- **Direct-subband**: Per-subband MS, then concat (>2 subbands)
- **Auto**: Selects strategy based on subband count

**Staging Options**:

- **tmpfs staging**: Fast conversion via `/dev/shm` (configurable)
- **Direct write**: Write directly to final location

### 4.2 Calibration

**Frequency Guidelines (Streaming)**:

- **Bandpass**: Once per 24 hours (stable)
- **Gain**: Every hour (time-variable)

**Solution Types**:

- **K-calibration**: Delay corrections
- **Bandpass**: Frequency-dependent solutions
- **Gain**: Time & antenna-dependent corrections
- **Fast mode**: Phase-only, reduced time/frequency averaging

**Registry System**:

- Solutions stored with validity windows (MJD range)
- Workers query registry for active solutions
- Path validation before application

### 4.3 Imaging

**Default Parameters**:

- Image size: 1024×1024 pixels
- Weighting: Briggs (robust parameter configurable)
- Deconvolver: Hogbom
- Iterations: 1000

**Quick Mode**:

- Reduced `imsize` and `niter`
- Optional FITS export skipping (`--skip-fits`)
- NVSS skymodel seeding (10 mJy threshold)

**Output Products**:

- `.image` - Restored image (CASA format)
- `.pbcor` - Primary beam corrected
- `.pbcor.fits` - FITS export (optional)

### 4.4 Mosaic Creation

**Combination Methods**:

- **Mean stacking** (default)
- **Median stacking**
- **Weighted mean**

**Validation**:

- Tile consistency checks
- Coordinate system validation
- Beam size verification
- Post-creation validation

**Metadata Tracking**:

- Group ID, time range, calibrator name
- Number of images, PB response statistics
- Validation status, QA metrics

### 4.5 Publishing & Data Registry

**Publishing Flow**:

1. Register mosaic in `data_registry` (status='staging')
2. Set QA status (`qa_status='passed'`)
3. Set validation status (`validation_status='validated'`)
4. Finalize data → triggers auto-publish
5. Move from `/stage/` to `/data/` (products)
6. Update `data_registry` (status='published')

**Auto-Publish Criteria**:

- `auto_publish_enabled=1`
- `qa_status='passed'`
- `validation_status='validated'`
- `finalization_status='finalized'`
- Photometry completed (if enabled)

---

## 5. API & Web Interface

### 5.1 REST API

**Base URL**: `http://localhost:8000/api/`

**Router Modules** (`dsa110_contimg/api/routers/`):

- `catalogs.py` - Catalog queries & management
- `images.py` - Image metadata & access
- `mosaics.py` - Mosaic metadata & creation
- `photometry.py` - Source detection & photometry
- `pipeline.py` - Pipeline control & status
- `products.py` - Published product access
- `tasks.py` - Job queue management
- `monitoring.py` - System monitoring & metrics
- `absurd.py` - Absurd workflow integration (NEW)

**Common Endpoints**:

- `GET /api/status` - Pipeline health & statistics
- `POST /api/jobs/` - Submit batch job
- `GET /api/mosaics/` - List mosaics
- `GET /api/images/{image_id}` - Get image metadata
- `GET /api/catalogs/sources` - Query source catalog

### 5.2 Frontend

**Technology**: React-based SPA

**Key Features**:

- Real-time pipeline monitoring
- Image visualization (JS9 integration)
- Source search & catalog browsing
- Job submission & management
- QA report generation

**Location**: `src/dsa110_contimg/frontend/`

---

## 6. Absurd Integration (NEW)

### 6.1 Overview

**Absurd**: Durable, fault-tolerant workflow manager (PostgreSQL-backed)

**Status**: Phase 1 complete (infrastructure ready)

**Components**:

- `absurd/client.py` - Async client for task operations
- `absurd/worker.py` - Worker harness for task execution
- `absurd/config.py` - Configuration dataclass
- `absurd/adapter.py` - (TODO) Pipeline-specific executor

### 6.2 Setup

```bash
# 1. Setup database
./scripts/setup_absurd.sh

# 2. Configure
export ABSURD_ENABLED=true
export ABSURD_DATABASE_URL="postgresql://postgres@localhost/dsa110_absurd"
export ABSURD_QUEUE_NAME="dsa110-pipeline"

# 3. Test
python scripts/test_absurd_basic.py
```

### 6.3 Features

- **Fault tolerance**: Tasks survive worker crashes
- **Retries**: Configurable retry limits
- **Durability**: State persisted in PostgreSQL
- **Observability**: Query task status & history
- **Concurrency**: Multi-worker execution

**Next Steps**: Phase 2 (pipeline integration), Phase 3 (UI & testing)

---

## 7. Testing & Quality Assurance

### 7.1 Test Structure

```
tests/
├── unit/                # Fast, isolated tests
│   ├── catalog/
│   ├── mosaic/
│   └── test_safeguards.py
└── integration/         # Require external resources
    ├── catalog/
    ├── test_new_structure.py
    └── test_pipeline_new_structure.py
```

### 7.2 Test Markers

- `@pytest.mark.unit` - Unit tests (fast)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.casa` - Require CASA environment
- `@pytest.mark.synthetic` - Use synthetic data
- `@pytest.mark.science` - Science validation

### 7.3 QA Tools

**Modules**:

- `qa/calibration_qa.py` - Calibration validation
- `qa/image_qa.py` - Image quality metrics
- `qa/mosaic_qa.py` - Mosaic validation
- `qa/fast_plots.py` - Quick visualization

**CLI**:

```bash
# Calibration QA
python -m dsa110_contimg.qa.cli calibration \
  --ms-path /stage/ms/observation.ms

# Image QA
python -m dsa110_contimg.qa.cli image \
  --image-path /stage/images/image.fits

# Mosaic QA
python -m dsa110_contimg.qa.cli mosaic \
  --mosaic-id mosaic_2025-11-12_10-00-00
```

---

## 8. Documentation Organization

### 8.1 Documentation Structure

```
docs/
├── how-to/              # Step-by-step procedures
├── concepts/            # Concept explanations
│   └── DIRECTORY_ARCHITECTURE.md  # Organizational layout
├── reference/           # API/CLI reference
├── tutorials/           # Learning guides
├── operations/          # Operational procedures
├── dev/                 # Developer notes & analysis
│   ├── status/          # Status updates (YYYY-MM/)
│   ├── analysis/        # Investigations & studies
│   └── notes/           # Agent notes
└── archive/             # Historical documentation
```

### 8.2 Key Documentation Files

**Pipeline Core**:

- `README_PIPELINE_DOCUMENTATION.md` - Documentation index
- `WORKFLOW_THOUGHT_EXPERIMENT.md` - 9-stage workflow trace
- `FINAL_WORKFLOW_VERIFICATION.md` - Verification of fixes
- `DEFAULTS_AND_MINIMAL_INPUT.md` - Default parameters
- `EXECUTION_THEMES.md` - Streaming vs Batch modes

**Module-Specific**:

- `conversion/README.md` - UVH5 conversion guide
- `conversion/SEMI_COMPLETE_SUBBAND_GROUPS.md` - Semi-complete protocol
- `calibration/README.md` - Calibration guide
- `absurd/README.md` - Absurd integration
- `absurd/ABSURD_QUICK_START.md` - Quick start guide

**Operations**:

- `docs/concepts/DIRECTORY_ARCHITECTURE.md` - Filesystem layout
- `docs/DOCUMENTATION_QUICK_REFERENCE.md` - Where to put docs

### 8.3 Documentation Rules

**Naming Convention**: `lowercase_with_underscores.md`

**Location Decision Tree**:

- End-user procedures → `docs/how-to/`
- Concept explanations → `docs/concepts/`
- API/CLI reference → `docs/reference/`
- Status updates → `docs/dev/status/YYYY-MM/`
- Investigations → `docs/dev/analysis/`
- Historical → `docs/archive/`

---

## 9. Operational Procedures

### 9.1 Starting the Pipeline (Production)

```bash
# 1. Ensure casa6 environment
source /data/dsa110-contimg/scripts/dev/developer-setup.sh

# 2. Start converter (Terminal 1)
cd /data/dsa110-contimg/src
dsa110-contimg-convert-stream \
  --input-dir /data/incoming/ \
  --output-dir /stage/dsa110-contimg/ms/

# 3. Start mosaic daemon (Terminal 2)
dsa110-contimg-streaming-mosaic --loop

# 4. (Optional) Start API server (Terminal 3)
cd /data/dsa110-contimg/src
uvicorn dsa110_contimg.api.routes:app --host 0.0.0.0 --port 8000
```

### 9.2 Monitoring

**Database Queries**:

```bash
# Check ingest queue
sqlite3 state/ingest.sqlite3 "SELECT COUNT(*) FROM ingest_queue WHERE state='pending'"

# Check MS index
sqlite3 state/products.sqlite3 "SELECT COUNT(*), status FROM ms_index GROUP BY status"

# Check mosaic groups
sqlite3 state/products.sqlite3 "SELECT status, COUNT(*) FROM mosaic_groups GROUP BY status"
```

**API Monitoring**:

```bash
# Pipeline status
curl http://localhost:8000/api/status

# Recent jobs
curl http://localhost:8000/api/jobs/

# Queue statistics
curl http://localhost:8000/api/queue/stats
```

### 9.3 Common Maintenance Tasks

**Calibration Table Management**:

```bash
# List active calibration tables
python -m dsa110_contimg.calibration.cli list-tables \
  --cal-registry-db state/cal_registry.sqlite3

# Retire old calibration table
python -m dsa110_contimg.calibration.cli retire-table \
  --cal-registry-db state/cal_registry.sqlite3 \
  --set-name bp_20250101
```

**Data Publishing**:

```bash
# Publish mosaic manually
python -m dsa110_contimg.database.cli publish \
  --db state/products.sqlite3 \
  --data-id mosaic_2025-11-12_10-00-00

# Check publish status
python -m dsa110_contimg.database.cli status \
  --db state/products.sqlite3 \
  --data-id mosaic_2025-11-12_10-00-00
```

**CASA Log Management**:

```bash
# Organize CASA logs
./scripts/organize_casa_logs.sh

# Clean up old CASA logs
./scripts/cleanup_casa_logs.py --days 7
```

---

## 10. Development Guidelines

### 10.1 Code Organization

**Module Principles**:

- One clear responsibility per module
- Database interactions in `database/` module
- CLI interfaces in `cli.py` files
- Shared utilities in `utils/`

**Naming Conventions**:

- Files: `lowercase_with_underscores.py`
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `UPPER_CASE`

### 10.2 Database Access Patterns

**Connection Management**:

```python
from dsa110_contimg.database.products import ensure_products_db

# Open connection
conn = ensure_products_db(Path("state/products.sqlite3"))

# Use connection
cursor = conn.cursor()
cursor.execute("SELECT * FROM ms_index WHERE status='converted'")

# Close when done
conn.close()
```

**State Updates**:

```python
# Always use transactions for state changes
conn.execute("BEGIN TRANSACTION")
try:
    # Update database
    conn.execute("UPDATE ms_index SET status='calibrated' WHERE path=?", (ms_path,))
    # Verify filesystem
    if not Path(ms_path).exists():
        raise FileNotFoundError(f"MS not found: {ms_path}")
    conn.commit()
except Exception as e:
    conn.rollback()
    raise
```

### 10.3 Error Handling

**Idempotent Operations**:

```python
def create_mosaic(group_id: str, output_path: Path):
    """Create mosaic (idempotent)."""
    # Check if already done
    conn = ensure_products_db(products_db)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT mosaic_path FROM mosaic_groups WHERE group_id=?",
        (group_id,)
    )
    row = cursor.fetchone()

    if row and Path(row[0]).exists():
        logger.info(f"Mosaic already exists: {row[0]}")
        return row[0]

    # Create mosaic
    # ... mosaic creation logic ...
```

**Path Validation**:

```python
def validate_stage_path(path: Path) -> bool:
    """Validate path is within staging directory."""
    stage_root = Path("/stage/dsa110-contimg")
    try:
        path.resolve().relative_to(stage_root.resolve())
        return True
    except ValueError:
        return False
```

### 10.4 Python Version Enforcement

**CRITICAL**: Pipeline enforces Python 3.11.13 (casa6) at package import:

```python
# dsa110_contimg/__init__.py
import sys
from dsa110_contimg.utils.python_version_guard import enforce_casa6_python

enforce_casa6_python()  # Exits if wrong Python version
```

**Developer Setup**:

```bash
source /data/dsa110-contimg/scripts/dev/developer-setup.sh
# Activates casa6 environment and sets PYTHONPATH
```

---

## 11. Known Issues & Future Work

### 11.1 Current Status

**Production-Ready**: ✓ All 24 identified "icebergs" fixed

**Major Fixes (2024-2025)**:

1. ✅ Mosaic registration & publishing
2. ✅ Semi-complete subband group support
3. ✅ Calibration registry with validity windows
4. ✅ Idempotent operations across all stages
5. ✅ Path validation before file operations
6. ✅ Database-backed state persistence
7. ✅ Phase center handling (time-dependent phasing)

### 11.2 Future Enhancements

**Phase 2: Absurd Integration** (In Progress)

- Pipeline task executor (`adapter.py`)
- Worker pool management
- Task queue monitoring

**Phase 3: Absurd UI** (Planned)

- Task status dashboard
- Retry controls
- Queue statistics

**Science Improvements** (Ongoing)

- Advanced flagging strategies
- Improved RFI mitigation
- A-projection primary beam correction
- Multi-scale deconvolution

**Performance Optimizations** (Planned)

- Parallel imaging across MS files
- GPU acceleration (WSClean)
- tmpfs staging optimization
- Distributed worker pools

---

## 12. Reference Information

### 12.1 Important Paths

```
Code:           /data/dsa110-contimg/
Incoming Data:  /data/incoming/
Staging (SSD):  /stage/dsa110-contimg/  (1 TB)
Products (HDD): /data/dsa110-contimg/products/  (13 TB)
State DBs:      /data/dsa110-contimg/state/
Logs:           /data/dsa110-contimg/state/logs/
```

### 12.2 Service Ports

- API Server: `8000`
- Dashboard: `7890` (Habitat UI, optional)
- Redis: `6379` (if caching enabled)

### 12.3 Environment Variables

**Required**:

- `PIPELINE_STATE_DIR` - State directory path (default: `state/`)
- `PYTHONPATH` - Must include `/data/dsa110-contimg/`

**Optional**:

- `ABSURD_ENABLED` - Enable Absurd integration (default: `false`)
- `ABSURD_DATABASE_URL` - PostgreSQL connection string
- `CAL_REGISTRY_DB` - Custom cal registry path
- `PRODUCTS_DB` - Custom products DB path

### 12.4 Key Contacts & Resources

**Project**: DSA-110 Continuum Imaging Pipeline  
**Institution**: Caltech/OVRO  
**Repository**: `dsa110/dsa110-contimg`  
**Documentation**: `/data/dsa110-contimg/docs/`

---

## 13. Quick Reference Commands

### 13.1 Pipeline Operations

```bash
# Convert single HDF5 file
dsa110-convert single --input observation.uvh5 --output observation.ms

# Convert subband groups in time window
dsa110-convert groups \
  --input-dir /data/incoming \
  --output-dir /stage/dsa110-contimg/ms \
  --start-time 2024-01-01T00:00:00 \
  --end-time 2024-01-01T01:00:00

# Calibrate MS
dsa110-calibrate calibrate --ms observation.ms --field calibrator --refant ea01

# Apply calibration
dsa110-calibrate apply --ms science.ms --field science --tables kcal bpcal gpcal

# Image MS
dsa110-image tclean --ms science.ms --output science.image

# Create mosaic
dsa110-mosaic build --name test --output mosaic.image
```

### 13.2 Database Operations

```bash
# Discover MS files and register in database
python -m dsa110_contimg.database.registry_cli discover \
  --scan-dir /stage/dsa110-contimg/ms

# Publish mosaic
python -m dsa110_contimg.database.cli publish \
  --db state/products.sqlite3 \
  --data-id mosaic_2025-11-12_10-00-00

# List staging data
python -m dsa110_contimg.database.cli list \
  --db state/products.sqlite3 \
  --status staging
```

### 13.3 QA & Monitoring

```bash
# Calibration QA
python -m dsa110_contimg.qa.cli calibration --ms-path observation.ms

# Image QA
python -m dsa110_contimg.qa.cli image --image-path image.fits

# Mosaic QA
python -m dsa110_contimg.qa.cli mosaic --mosaic-id mosaic_2025-11-12

# Generate comprehensive QA report
python -m dsa110_contimg.qa.cli report --data-id mosaic_2025-11-12
```

---

## 14. Conclusion

The DSA-110 Continuum Imaging Pipeline is a mature, production-ready system
with:

- **Robust Architecture**: Database-backed state, idempotent operations,
  comprehensive error handling
- **Flexible Operation**: Supports both streaming (continuous) and batch
  (explicit) execution
- **Comprehensive Testing**: Unit and integration tests, QA tools, validation
  frameworks
- **Rich Documentation**: 60K+ words across 5 core documents plus
  module-specific guides
- **Active Development**: Absurd integration underway, ongoing science
  improvements

The codebase is well-organized, thoroughly documented, and follows best
practices for scientific software development. The architecture prioritizes
reliability, observability, and maintainability—critical for a production
observatory pipeline.

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-18  
**Next Review**: As needed for major changes
