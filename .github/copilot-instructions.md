# DSA-110 Continuum Imaging Pipeline - AI Coding Agent Instructions

# !!! GROUND TRUTH HIERARCHY !!!

**Code is truth, docs are intent.** When docs and code conflict, trust the code.

## Document Status Key

| Document                              | Status             | Use For                                |
| ------------------------------------- | ------------------ | -------------------------------------- |
| This file (`copilot-instructions.md`) | **CURRENT**        | How the system works TODAY             |
| `COMPLEXITY_REDUCTION.md`             | **FUTURE ROADMAP** | Where we're heading, NOT current state |
| `COMPLEXITY_REDUCTION_NOTES.md`       | **FUTURE ROADMAP** | Implementation notes for roadmap       |

**Before building anything new:** Query existing databases and code to understand what already exists.

## AI Instruction Pack

Use the companion instruction set as defaults for AI coding agents:

- Charter with goals and priorities
- Problem-solving playbook outlining the workflow
- Coding standards, testing checklist, review self-check, and tooling usage guidance
- Domain invariants, performance/scaling principles, security and data handling, debugging and logging practices, and example templates

## Project Overview

**Development Branch**: `master-dev` in `/data/dsa110-contimg/`.

**DSA-110 continuum imaging pipeline** converts radio telescope visibility data
from UVH5 (HDF5) format to CASA Measurement Sets for calibration and imaging.
The DSA-110 telescope produces **16 separate subband files per observation**
that must be grouped by timestamp and combined before processing.

**Critical Architecture Pattern**: Every observation consists of a group of 16
subband files (`*_sb00.hdf5` through `*_sb15.hdf5`) with timestamps as
filenames. For a single group, the timestamps can be identical or slightly
variable within approximately +/- 30 seconds, and still belong to the same
observation. This is why we introduce a time-windowing mechanism to group files
that belong together.

> **⚠️ NEVER use exact timestamp matching to find subband groups!**
>
> Subbands have timestamp jitter (±30s). Simple glob patterns like
> `${timestamp}_sb*.hdf5` will FAIL to find all 16 subbands.
>
> **ALWAYS use `find_subband_groups()` with tolerance:**
>
> ```python
> from dsa110_contimg.database.hdf5_index import query_subband_groups
> groups = query_subband_groups(
>     db_path="/data/incoming/hdf5_file_index.sqlite3",
>     start_time="2025-01-15T00:00:00",
>     end_time="2025-01-15T23:59:59",
>     cluster_tolerance_s=60.0,
> )
> complete = [g for g in groups if len(g) == 16]
> ```

The conversion code must:

1. Group files by timestamp (within 60 second tolerance)
2. Combine subbands using pyuvdata's `+=` operator
3. Output a single Measurement Set per observation group

## Environment & Dependencies

**Conda Environment**: All code runs in `casa6` conda environment

```bash
conda activate casa6  # Always activate before running scripts
```

**Critical Version Constraints**:

- Python 3.11 (casa6 environment)
- CASA 6.7 (via casatools, casatasks, casacore)
- pyuvdata 3.2.4 (uses `Nants_telescope`, not deprecated `Nants_data`)
- pyuvsim, astropy, numpy (see `ops/docker/environment.yml` for complete list)

**Fast Metadata Reading**: Use `FastMeta` for reading UVH5 metadata (~700x
faster):

```python
from dsa110_contimg.utils import FastMeta, get_uvh5_mid_mjd

# Quick helper
mid_mjd = get_uvh5_mid_mjd("/path/to/file.hdf5")

# Context manager for multiple attributes
with FastMeta("/path/to/file.hdf5") as meta:
    times = meta.time_array
    freqs = meta.freq_array
```

**Running Commands**: Use `run_in_terminal` with casa6 environment activated for
all Python scripts and CASA tasks.

## I/O Performance & Build Practices

**Storage Architecture**:

| Mount       | Type     | Purpose                                 |
| ----------- | -------- | --------------------------------------- |
| `/data/`    | HDD      | Raw HDF5, source code, databases (slow) |
| `/stage/`   | NVMe SSD | Output MS files, working data (fast)    |
| `/scratch/` | NVMe SSD | Temporary files, builds (fast)          |
| `/dev/shm/` | tmpfs    | In-memory staging during conversion     |

**CRITICAL**: `/data/` is on HDD - avoid I/O-intensive operations there.

**Use `/scratch/` or `/stage/` for**:

- Frontend builds (`npm run build`)
- MkDocs documentation builds
- Python package installs with compilation
- Large file processing and temporary files
- Any operation that is I/O heavy

**Build workflow for frontend**:

```bash
# Use the scratch-based build script
cd /data/dsa110-contimg/frontend
npm run build:scratch  # Builds in /scratch/, copies result back
```

**Build workflow for MkDocs documentation**:

```bash
# Build on scratch SSD, then move back
mkdir -p /scratch/mkdocs-build
mkdocs build -f /data/dsa110-contimg/mkdocs.yml -d /scratch/mkdocs-build/site
rm -rf /data/dsa110-contimg/site
mv /scratch/mkdocs-build/site /data/dsa110-contimg/site
rmdir /scratch/mkdocs-build
```

**For Python/Backend**:

```bash
conda activate casa6
# Run tests and builds - scratch is used automatically via TMPDIR when needed
```

## Directory Structure

**Actual Production Paths**:

- `/data/incoming/` - Raw HDF5 subband files from correlator (watched by
  streaming converter)
- `/stage/dsa110-contimg/` - Processed Measurement Sets and images (working
  directory)
- `/data/dsa110-contimg/state/` - SQLite databases and runtime state
- `/data/dsa110-contimg/state/db/` - All SQLite databases
- `/data/dsa110-contimg/state/run/` - Runtime state (PID files, status JSON)
- `/data/dsa110-contimg/state/logs/` - Pipeline execution logs
- `/data/dsa110-contimg/products/` - Final data products (symlinked to
  /stage/dsa110-contimg/)

**Active Code Structure**:

- `backend/src/dsa110_contimg/` - Main Python package (active development)
- `frontend/src/` - React dashboard
- `config/` - Centralized configuration (docker, hooks, linting, editor)
- `scripts/` - Consolidated utility scripts (backend, ops, archive)
- `ops/` - Operational configuration (systemd, docker, deployment)
- `docs/` - Documentation (architecture, guides, reference, operations)
- `vendor/` - External dependencies (aocommon, everybeam)
- `.ai/` - AI tool configurations (cursor, codex, gemini)

## Database Rules

**DATABASE REQUIREMENTS**:

- **ONLY SQLite databases** (`.sqlite3` extension) are permitted
- All catalog databases MUST be in `/data/dsa110-contimg/state/catalogs/`
- Never use CSV, text files, or other formats as primary data sources
- Source data files (for building databases) go in `state/catalogs/sources/`

**VLA Calibrator Database**: The pipeline uses a SQLite database of VLA
calibrators at `/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3`.
To rebuild:

```bash
python -m dsa110_contimg.catalog.build_vla_calibrators \
    --source /data/dsa110-contimg/state/catalogs/sources/vlacalibrators.txt
```

## Critical Conversion Pipeline

### Subband File Patterns

```
2025-10-05T12:30:00_sb00.hdf5  # 16 subbands: sb00 through sb15
2025-10-05T12:30:00_sb01.hdf5
...
2025-10-05T12:30:00_sb15.hdf5
```

**Subband Grouping**

The correlator may write subbands with slightly different timestamps (±60s jitter).
The pipeline uses two mechanisms to group files that belong together:

| Method             | When Used        | How It Works                                        |
| ------------------ | ---------------- | --------------------------------------------------- |
| **Normalization**  | ABSURD ingestion | Renames files to canonical `group_id` (sb00's time) |
| **Time-Windowing** | Batch processing | Clusters files within 60s tolerance at query time   |

**Normalization (ABSURD)**: When subbands are ingested via ABSURD, files are
renamed to use sb00's timestamp as the canonical group_id:

```python
from dsa110_contimg.conversion.streaming import normalize_directory

# Batch normalize historical files
stats = normalize_directory(Path("/data/incoming"), dry_run=True)
print(f"Would rename {stats['files_renamed']} files")
```

**Time-Windowing (Batch)**: For batch processing, use `query_subband_groups()`:

```python
from dsa110_contimg.database.hdf5_index import query_subband_groups

groups = query_subband_groups(
    db_path="/data/incoming/hdf5_file_index.sqlite3",
    start_time="2025-01-15T00:00:00",
    end_time="2025-01-15T23:59:59",
    cluster_tolerance_s=60.0,  # Default 60s clustering tolerance
)
complete = [g for g in groups if len(g) == 16]
```

See `docs/guides/storage-and-file-organization.md` for full details.

### Two Processing Modes

1. **Batch Converter** (`backend/src/dsa110_contimg/conversion/hdf5_orchestrator.py`):

   - For historical/archived data processing
   - Function:
     `convert_subband_groups_to_ms(input_dir, output_dir, start_time, end_time)`
   - Groups files by timestamp (60s tolerance), processes sequentially

2. **ABSURD Ingestion** (`backend/src/dsa110_contimg/absurd/ingestion.py`):
   - For scheduled/automated data ingest
   - Uses PostgreSQL-backed task queue with durable execution
   - **Normalizes filenames** to canonical group_id before conversion
   - Run via scheduler or API triggers
   - **Note**: ABSURD is labeled EXPERIMENTAL

### Conversion Data Flow

```
UVH5 files :arrow_right: pyuvdata.UVData :arrow_right: combine subbands :arrow_right:
direct MS writing :arrow_right: configure_ms_for_imaging :arrow_right:
update antenna positions :arrow_right: auto-rename calibrator fields
```

**Key Implementation Details**:

- Use `pyuvdata.UVData()` with `strict_uvw_antpos_check=False` for DSA-110
  compatibility
- Direct MS writing via `strategies/writers.py` (no UVFITS intermediate)
- Antenna positions from
  `backend/src/dsa110_contimg/utils/antpos_local/data/DSA110_Station_Coordinates.csv`
- Phase visibilities to meridian using `helpers_coordinates.py`
- Use batched subband loading (default: 4 subbands per batch) to reduce memory
- Auto-detect and rename calibrator fields (enabled by default, use
  `--no-rename-calibrator-fields` to disable)

### Pointing Change Detection & Precomputation

The streaming converter automatically detects pointing changes (when the
telescope declination changes significantly) and proactively prepares resources:

**How it works**:

1. When new HDF5 files arrive, the `PointingTracker` reads the `phase_center_dec`
   from the first subband's metadata
2. If Dec changes by more than 1.0° (configurable), triggers precomputation:
   - Selects best bandpass calibrator for the new Dec
   - Computes upcoming transit times for that calibrator
   - Queues background catalog strip database builds

**Precomputation Module** (`backend/src/dsa110_contimg/pipeline/precompute.py`):

```python
from dsa110_contimg.pipeline.precompute import (
    get_pointing_tracker,
    PointingTracker,
    ensure_catalogs_for_dec,
)

# Get current pointing status
tracker = get_pointing_tracker()
status = tracker.get_status()
print(f"Current Dec: {status['current_dec_deg']}°")

# Get best calibrator for a declination
best = tracker.get_best_calibrator(dec_deg=55.0)
print(f"Best calibrator: {best.name}, transit at {best.transit_utc}")

# Ensure catalog databases exist (queues background build if needed)
catalogs = ensure_catalogs_for_dec(dec_deg=55.0)
```

**API Endpoints** (`/api/calibrator-imaging/pointing/`):

| Endpoint                        | Method | Description                     |
| ------------------------------- | ------ | ------------------------------- |
| `/pointing/status`              | GET    | Current pointing tracker status |
| `/pointing/best-calibrator`     | GET    | Best calibrator for Dec         |
| `/pointing/transits`            | GET    | Upcoming transits for Dec       |
| `/pointing/precompute-transits` | POST   | Precompute all transits         |
| `/pointing/ensure-catalogs`     | POST   | Build missing catalog strips    |

This reduces pipeline latency by having calibrators and catalogs ready before
the telescope reaches a new pointing.

## DSA-110 Specific Utilities

### Antenna Positions

Go back to

```python
from dsa110_contimg.utils.antpos_local import get_itrf
df_itrf = get_itrf()  # Returns DataFrame with ITRF coordinates
antpos = np.array([df_itrf['x_m'], df_itrf['y_m'], df_itrf['z_m']]).T  # (nants, 3) in meters
```

- Reads from
  `backend/src/dsa110_contimg/utils/antpos_local/data/DSA110_Station_Coordinates.csv`
- Returns ITRF coordinates in meters (X, Y, Z)
- Used during MS creation to set antenna positions

### Coordinate Transformations

```python
from dsa110_contimg.conversion.helpers_coordinates import phase_to_meridian
from dsa110_contimg.utils.constants import DSA110_LOCATION

# Phase visibilities to meridian (standard for DSA-110)
phase_to_meridian(uvdata)

# DSA-110 telescope location (used for LST calculations)
DSA110_LOCATION  # astropy EarthLocation object
```

### Constants

```python
from dsa110_contimg.utils.constants import (
    DSA110_LOCATION,    # Telescope location (EarthLocation)
    DSA110_LATITUDE,    # Observatory latitude (degrees)
    DSA110_LONGITUDE,   # Observatory longitude (degrees)
    # Note: OVRO_LOCATION is deprecated - use DSA110_LOCATION instead
)
```

## MS Writing Pattern

The pipeline uses **direct MS table writing** via the `writers` module:

```python
from dsa110_contimg.conversion.strategies.writers import get_writer

# Get writer class for production (always use 'parallel-subband' or 'direct-subband')
writer_cls = get_writer('parallel-subband')  # Or 'direct-subband' (same writer)
writer_instance = writer_cls(uvdata, output_path, **writer_kwargs)
writer_type = writer_instance.write()  # Returns writer type string

# Direct class usage (alternative)
from dsa110_contimg.conversion.strategies.direct_subband import DirectSubbandWriter
writer = DirectSubbandWriter(uvdata, output_path, file_list=file_list)
writer.write()
```

**IMPORTANT**: The `pyuvdata` writer is **test-only** and will raise an error
if requested via `get_writer('pyuvdata')`. For testing purposes only, import
from `backend/tests/fixtures/writers.py`.

**Expected visibility shape**: `(nblt, nfreq, npol)`

- Typical: `nblt = nbaselines * ntimes`, `nfreq = 1024 per subband`, `npol = 4`
- After combining 16 subbands: `nfreq = 16384`

## Field Naming and Calibrator Auto-Detection

**Observation Duration**: Each measurement set covers **~5 minutes (309
seconds)** of observation time, consisting of 24 fields × 12.88 seconds per
field.

**Default Field Names**: All MS files have 24 fields named `meridian_icrs_t0`
through `meridian_icrs_t23` (one per 12.88-second timestamp during drift-scan).

**Auto-Renaming**: By default, the pipeline auto-detects which field contains a
known calibrator from the VLA catalog and renames it to `{calibrator}_t{idx}`:

```python
# Field 17 contains 3C286 :arrow_right: renamed to "3C286_t17"
# Field 5 contains J1331+3030 :arrow_right: renamed to "J1331+3030_t5"
```

**Implementation**: `configure_ms_for_imaging()` calls
`rename_calibrator_fields_from_catalog()` which:

1. Uses `select_bandpass_from_catalog()` to scan all 24 fields
2. Computes primary-beam-weighted flux for each field
3. Identifies field with peak response (closest to calibrator transit)
4. Renames that field to `{calibrator}_t{field_idx}`

**Disable auto-renaming**:

```bash
# CLI flag
python -m dsa110_contimg.conversion.cli groups \
    --no-rename-calibrator-fields \
    /data/incoming /stage/dsa110-contimg/ms \
    "2025-10-05T00:00:00" "2025-10-05T01:00:00"

# Python API
from dsa110_contimg.conversion.ms_utils import configure_ms_for_imaging
configure_ms_for_imaging(ms_path, rename_calibrator_fields=False)
```

**Manual renaming**:

```python
from dsa110_contimg.calibration.field_naming import rename_calibrator_field

# Rename field 17 to "3C286_t17"
rename_calibrator_field("observation.ms", "3C286", 17, include_time_suffix=True)
```

## Testing Patterns

Tests live in `backend/tests/` and `backend/src/tests/`:

```python
# Mock CASA tools to avoid CASA dependency in unit tests
def test_conversion(tmp_path, monkeypatch):
    # Mock casacore.tables to avoid requiring CASA
    fake_table = MagicMock()
    monkeypatch.setattr('casacore.tables.table', fake_table)

    # Test conversion logic
    result = convert_function(input_path, output_path)
    assert result.exists()
```

**Run tests**:

```bash
conda activate casa6
cd /data/dsa110-contimg/backend

# IMPORTANT: Use 'python -m pytest' to ensure casa6's pytest is used
# (not ~/.local/bin/pytest which may be linked to system Python)

# Unit tests (no CASA required)
python -m pytest tests/unit/ -v

# Integration tests (requires CASA)
python -m pytest tests/integration/ -v

# Run specific test
python -m pytest tests/unit/conversion/test_helpers.py -v
```

## Development Workflows

### Running Batch Conversion

```bash
conda activate casa6
cd /data/dsa110-contimg/backend

# Convert subband groups in a time window
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-10-05T00:00:00" \
    "2025-10-05T23:59:59"

# Dry-run to preview what would be converted
python -m dsa110_contimg.conversion.cli groups --dry-run \
    /data/incoming /stage/dsa110-contimg/ms \
    "2025-10-05T00:00:00" "2025-10-05T01:00:00"

# Convert by calibrator transit (auto-finds time window)
python -m dsa110_contimg.conversion.cli groups \
    --calibrator "0834+555" \
    /data/incoming /stage/dsa110-contimg/ms

# Find calibrator transit without converting
python -m dsa110_contimg.conversion.cli groups \
    --calibrator "3C286" --find-only \
    /data/incoming

# Convert a single UVH5 file
python -m dsa110_contimg.conversion.cli single \
    /data/incoming/observation.uvh5 \
    /stage/dsa110-contimg/ms/observation.ms
```

**Key CLI options for `groups` command:**

- `--dry-run` - Preview without writing files
- `--find-only` - Find groups/transits without converting
- `--calibrator NAME` - Auto-find transit time for calibrator
- `--skip-existing` - Skip groups with existing MS files
- `--no-rename-calibrator-fields` - Disable auto calibrator detection
- `--writer {parallel-subband,direct-subband,auto}` - MS writing strategy (all use DirectSubbandWriter)
- `--scratch-dir PATH` - Temp file location

**Python API (alternative):**

```python
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import convert_subband_groups_to_ms

convert_subband_groups_to_ms(
    input_dir="/data/incoming",
    output_dir="/stage/dsa110-contimg/ms",
    start_time="2025-10-05T00:00:00",
    end_time="2025-10-05T23:59:59",
)
```

### Starting Streaming Daemon

```bash
conda activate casa6

# Via systemd (recommended for production)
sudo systemctl start contimg-stream.service
sudo systemctl status contimg-stream.service

# Or manually for testing (uses PIPELINE_DB env var by default)
PIPELINE_DB=/data/dsa110-contimg/state/db/pipeline.sqlite3 \
python -m dsa110_contimg.conversion.streaming.streaming_converter \
    --input-dir /data/incoming \
    --output-dir /stage/dsa110-contimg/ms \
    --scratch-dir /stage/dsa110-contimg/scratch \
    --monitoring \
    --monitor-interval 60
```

### Queue Inspection

```bash
# Check HDF5 file index (in /data/incoming/)
sqlite3 /data/incoming/hdf5_file_index.sqlite3 \
  "SELECT timestamp, COUNT(*) as subband_count FROM hdf5_file_index GROUP BY timestamp HAVING subband_count = 16 LIMIT 10;"

# Check job history
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT id, job_type, status, started_at FROM jobs ORDER BY started_at DESC LIMIT 10;"

# Check MS registry
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT path, status, stage FROM ms_index ORDER BY created_at DESC LIMIT 10;"
```

### Creating Synthetic Test Data

```bash
conda activate casa6

# Generate synthetic UVH5 files
python -m dsa110_contimg.simulation.generate_uvh5 \
    --output-dir /tmp/synthetic_test \
    --start-time "2025-10-06T12:00:00" \
    --duration-minutes 5.0 \
    --num-subbands 16

# Or use existing simulation tools (if available)
# Check ops/simulation/ for deployment-specific tools
```

## Code Organization

**Active Development** (use these):

- :check: `backend/src/dsa110_contimg/` - Main Python package (production code)
  - `conversion/` - UVH5 :arrow_right: MS conversion
  - `calibration/` - Calibration routines
  - `imaging/` - Imaging wrappers (WSClean, CASA tclean)
  - `pipeline/` - Pipeline stage architecture
  - `api/` - FastAPI backend
  - `database/` - SQLite helpers
  - `utils/` - Shared utilities

**When in doubt**: Check `backend/src/dsa110_contimg/` first.

## Performance Considerations

### Memory Usage

- Each 16-subband group: ~2-4 GB RAM
- Use `--scratch-dir` on fast storage (NVMe/tmpfs) for temp files
- Checkpoint recovery prevents re-processing on failures

### Thread Tuning

```bash
--omp-threads 4  # Limit OpenMP/MKL threads (8-core system)
--omp-threads 8  # For 16-core systems
```

### Monitoring

```bash
# Streaming converter provides real-time metrics
--monitoring --monitor-interval 60  # Check queue health every 60s
--profile  # Enable detailed performance profiling
```

**Performance Warnings**: Groups taking >4.5 min indicate I/O bottlenecks or
insufficient resources.

## Common Pitfalls

1. **Forgetting casa6 environment**: Always `conda activate casa6` before
   running scripts
2. **Processing individual subbands**: Must group by timestamp first, never
   process `_sb01.hdf5` alone
3. **Using legacy code**: Check `backend/src/dsa110_contimg/` first, not
   `src/dsa110_contimg/`
4. **pyuvdata compatibility**: Use `Nants_telescope`, not deprecated
   `Nants_data`
5. **MS shape mismatches**: Squeeze `nspw=1` dimension before processing
6. **Missing antenna positions**: Always update MS with DSA-110 station
   coordinates
7. **CASA simulator issues**: Use `convert_to_ms_data_driven()` or UVFITS path
   instead

## Key Files for Reference

- `docs/SYSTEM_CONTEXT.md` - System architecture overview
- `docs/CODE_MAP.md` - Code-to-documentation mapping
- `backend/src/dsa110_contimg/conversion/README.md` - Conversion module docs
- `backend/src/dsa110_contimg/conversion/SEMI_COMPLETE_SUBBAND_GROUPS.md` -
  Subband grouping
- `ops/systemd/contimg.env` - Runtime configuration
- `backend/src/dsa110_contimg/pipeline/stages_impl.py` - Pipeline stages

## When Making Changes

1. **Subband Processing**: Any new converter must group files by timestamp
   (default: within 60s tolerance)
2. **Testing**: Mock CASA tools (see `backend/tests/unit/` for patterns)
3. **Antenna Positions**: Always use
   `dsa110_contimg.utils.antpos_local.get_itrf()`, not hardcoded values
4. **Error Handling**: Log to files in `/data/dsa110-contimg/state/logs/`, use
   structured logging
5. **Documentation**: Update corresponding docs in `docs/` and module README
   files
6. **Configuration**: Use environment variables or config files in `ops/`, not
   hardcoded parameters
7. **Database Paths**: Use paths in `/data/dsa110-contimg/state/` for SQLite
   databases

## Database Locations

SQLite databases are organized across two locations:

**HDF5 File Index** (`/data/incoming/`):

- `hdf5_file_index.sqlite3` - **Production HDF5 file tracking** (83K+ records):
  - Table: `hdf5_file_index` - maps HDF5 files to timestamps and subbands
  - Used by conversion API endpoints and storage validator
  - Located alongside raw HDF5 files for colocality

**Unified Pipeline Database** (`state/db/`):

- `pipeline.sqlite3` - **Primary unified database** for pipeline state:
  - Product registry - `ms_index`, `images`, `photometry`
  - Calibration - `caltables`, `calibrator_transits`
  - Jobs - `jobs`, `batch_jobs`, `operation_metrics`
  - Mosaics - `mosaics`, `mosaic_tiles`
  - HDF5 files - `hdf5_files` (schema exists, for future unified tracking)

**Other runtime databases** (`state/db/`):

- `docsearch.sqlite3` - Local documentation search index
- `docsearch_code.sqlite3` - Code-aware documentation search index
- `embedding_cache.sqlite3` - Cached OpenAI embeddings
- `hdf5.sqlite3` - HDF5 file metadata index (for fast queries)
- `ragflow_sync.sqlite3` - RAGFlow synchronization state

**Survey catalogs** (`state/catalogs/`):

- `nvss_dec+XX.X.sqlite3` - NVSS sources by declination strip
- `first_dec+XX.X.sqlite3` - FIRST survey sources
- `vlass_dec+XX.X.sqlite3` - VLASS sources
- `atnf_dec+XX.X.sqlite3` - ATNF pulsar catalog
- `rax_dec+XX.X.sqlite3` - RAX sources
- `vla_calibrators.sqlite3` - VLA calibrator catalog
- `master_sources.sqlite3` - Combined crossmatch of NVSS/FIRST/VLASS (~1.6M sources, 108MB)

Use WAL mode for concurrent access. Connection timeouts are set to 30 seconds.

## Local Documentation Search

**Use `DocSearch` for semantic search over project documentation.** This is the
preferred method for finding relevant documentation - no external services
required.

### Command Line

```bash
conda activate casa6

# Search documentation
python -m dsa110_contimg.docsearch.cli search "how to convert UVH5 to MS"

# More results
python -m dsa110_contimg.docsearch.cli search "calibration" --top-k 10

# Re-index after doc changes (incremental - only changed files)
python -m dsa110_contimg.docsearch.cli index
```

### Python API

```python
from dsa110_contimg.docsearch import DocSearch

search = DocSearch()
results = search.search("streaming converter queue states", top_k=5)

for r in results:
    print(f"{r.score:.3f} - {r.file_path}: {r.heading}")
    print(r.content[:200])
```

### When to Use

- Finding documentation on specific pipeline features
- Looking up API usage patterns
- Understanding module architecture
- Locating configuration examples

**Alternative**: RAGFlow is also available for full-featured RAG with chat, but
requires Docker containers and manual setup. Use DocSearch by default; RAGFlow
is optional for advanced use cases.

### RAGFlow (Alternative)

RAGFlow provides full-featured RAG with chat capabilities via Docker.

To use RAGFlow:

1. Ensure RAGFlow container is running: `docker ps --filter "name=ragflow"`
2. Access via REST API at `localhost:9380` or web UI at `localhost:9080`
3. Sync documentation using the sync script:

```bash
# Check sync status
python scripts/ragflow_sync.py status

# Sync documentation (incremental)
python scripts/ragflow_sync.py sync

# Full re-index
python scripts/ragflow_sync.py sync --full
```

For detailed documentation, see `docs/ragflow/README.md`.
