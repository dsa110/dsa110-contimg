# DSA-110 Continuum Imaging Pipeline - AI Coding Agent Instructions

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

**CRITICAL**: `/data/` is on HDD - avoid I/O-intensive operations there.

**Use `/scratch/` for**:

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

## Critical Conversion Pipeline

### Subband File Patterns

```
2025-10-05T12:30:00_sb00.hdf5  # 16 subbands: sb00 through sb15
2025-10-05T12:30:00_sb01.hdf5
...
2025-10-05T12:30:00_sb15.hdf5
```

**CRITICAL: Time-Windowing for Grouping**

Subbands from the same observation may have slightly different timestamps
(seconds apart) due to write timing. **Never** group by exact timestamp match.

The pipeline uses **±60 second tolerance** (default) to group subbands that
belong together:

```python
# CORRECT - use pipeline's time-windowing functions
from dsa110_contimg.database.hdf5_index import query_subband_groups
groups = query_subband_groups(
    hdf5_db,
    start_time,
    end_time,
    tolerance_s=1.0,           # Small window expansion for query
    cluster_tolerance_s=60.0   # Default 60s clustering tolerance
)
```

For filesystem-based grouping, use `find_subband_groups()` with `tolerance_s`
parameter.

### Two Processing Modes

1. **Batch Converter**
   (`backend/src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py`):
   - For historical/archived data processing
   - Function:
     `convert_subband_groups_to_ms(input_dir, output_dir, start_time, end_time)`
   - Groups files by timestamp, processes sequentially

2. **Streaming Converter**
   (`backend/src/dsa110_contimg/conversion/streaming/streaming_converter.py`):
   - Real-time daemon for live data ingest
   - SQLite-backed queue with checkpoint recovery
   - Run as systemd service (`ops/systemd/contimg-stream.service`)
   - **States**: `collecting` → `pending` → `in_progress` → `completed`/`failed`
   - **Performance tracking**: Records load/phase/write times per observation

### Conversion Data Flow

```
UVH5 files → pyuvdata.UVData → combine subbands →
direct MS writing → configure_ms_for_imaging →
update antenna positions → auto-rename calibrator fields
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
from dsa110_contimg.utils.constants import OVRO_LOCATION

# Phase visibilities to meridian (standard for DSA-110)
phase_to_meridian(uvdata)

# OVRO location (used for LST calculations)
OVRO_LOCATION  # astropy EarthLocation object
```

### Constants

```python
from dsa110_contimg.utils.constants import (
    OVRO_LOCATION,      # Telescope location
    DSA110_LATITUDE,    # Observatory latitude
    DSA110_LONGITUDE,   # Observatory longitude
)
```

## MS Writing Pattern

The pipeline uses **direct MS table writing** via the `writers` module:

```python
from dsa110_contimg.conversion.strategies.writers import get_writer

# Get writer class (recommended: 'parallel-subband' for production)
writer_cls = get_writer('parallel-subband')  # Or 'pyuvdata' for testing
writer_instance = writer_cls(uvdata, output_path, **writer_kwargs)
writer_type = writer_instance.write()  # Returns writer type string

# Direct class usage (alternative)
from dsa110_contimg.conversion.strategies.direct_subband import DirectSubbandWriter
writer = DirectSubbandWriter(uvdata, output_path, file_list=file_list)
writer.write()
```

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
# Field 17 contains 3C286 → renamed to "3C286_t17"
# Field 5 contains J1331+3030 → renamed to "J1331+3030_t5"
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
- `--writer {parallel-subband,pyuvdata}` - MS writing strategy
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

# Or manually for testing
python -m dsa110_contimg.conversion.streaming.streaming_converter \
    --input-dir /data/incoming \
    --output-dir /stage/dsa110-contimg/ms \
    --queue-db /data/dsa110-contimg/state/ingest.sqlite3 \
    --registry-db /data/dsa110-contimg/state/cal_registry.sqlite3 \
    --scratch-dir /stage/dsa110-contimg/scratch \
    --monitoring \
    --monitor-interval 60
```

### Queue Inspection

```bash
# Check streaming queue status
sqlite3 /data/dsa110-contimg/state/ingest.sqlite3 \
  "SELECT group_id, state, processing_stage, retry_count FROM ingest_queue ORDER BY received_at DESC LIMIT 10;"

# Check performance metrics
sqlite3 /data/dsa110-contimg/state/ingest.sqlite3 \
  "SELECT group_id, total_time, load_time, phase_time, write_time FROM performance_metrics ORDER BY recorded_at DESC LIMIT 10;"

# Check HDF5 file index
sqlite3 /data/dsa110-contimg/state/hdf5.sqlite3 \
  "SELECT timestamp, COUNT(*) as subband_count FROM hdf5_file_index GROUP BY group_id HAVING subband_count = 16 LIMIT 10;"
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

- :white_heavy_check_mark: `backend/src/dsa110_contimg/` - Main Python package (production code)
  - `conversion/` - UVH5 → MS conversion
  - `calibration/` - Calibration routines
  - `imaging/` - Imaging wrappers (WSClean, CASA tclean)
  - `pipeline/` - Pipeline stage architecture
  - `api/` - FastAPI backend
  - `database/` - SQLite helpers
  - `utils/` - Shared utilities

**Legacy/Deprecated** (avoid):

- :cross_mark: `.local/archive/` - Old deprecated code, external references (gitignored)
- :cross_mark: Files with "legacy" in the path

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

## External Dependencies & References

The `.local/archive/references/` directory contains external repos for
historical context (gitignored, not committed):

- `.local/archive/references/dsa110-calib/` - Original calibration library
- `.local/archive/references/dsa110-meridian-fs/` - Meridian fringestopping
  reference
- `.local/archive/references/dsa110-xengine/` - Correlator output format
  documentation

**Do not modify** files in `.local/archive/` - they're read-only references.

## Database Locations

All SQLite databases are in `/data/dsa110-contimg/state/`:

- `products.sqlite3` - Product registry (MS, images, photometry)
- `ingest.sqlite3` - Streaming queue management
- `hdf5.sqlite3` - HDF5 file index
- `cal_registry.sqlite3` - Calibration table registry
- `calibrator_registry.sqlite3` - Known calibrators
- `master_sources.sqlite3` - Source catalog (NVSS, FIRST, RAX)
- `docsearch.sqlite3` - Local documentation search index
- `embedding_cache.sqlite3` - Cached OpenAI embeddings

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

**Note:** RAGFlow reference code and examples are located in `docs/ragflow/`.
This code is **not part of the Python package** and must be run as standalone
scripts.

To use RAGFlow:

1. Deploy RAGFlow containers (see `docs/ops/ragflow/README.md`)
2. Access via REST API at `localhost:9380` or web UI at `localhost:9080`
3. Use the standalone scripts in `docs/ragflow/`:

```bash
# Navigate to the ragflow directory
cd /data/dsa110-contimg/docs/ragflow

# Example: Query documentation
python cli.py query "your question"

# Example: Upload documents
python cli.py upload --docs-dir /path/to/docs

# Example: Start MCP server
python mcp_server.py --sse --port 9400
```

For detailed documentation and examples, see `docs/ragflow/README.md`.
