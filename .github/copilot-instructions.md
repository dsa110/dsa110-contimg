# DSA-110 Continuum Imaging Pipeline - AI Coding Agent Instructions

## Project Overview

**DSA-110 continuum imaging pipeline** converts radio telescope visibility data from UVH5 (HDF5) format to CASA Measurement Sets for calibration and imaging. The DSA-110 telescope produces **16 separate subband files per observation** that must be grouped by timestamp and combined before processing.

**Critical Architecture Pattern**: Every observation consists of 16 subband files (`*_sb01.hdf5` through `*_sb16.hdf5`) with identical timestamps. All conversion code must:
1. Group files by timestamp (within 2.5 min tolerance)
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
- pyuvsim, astropy, numpy (see `environment.yml` for complete list)

**Running Commands**: Use `run_in_terminal` with casa6 environment activated for all Python scripts and CASA tasks.

## Directory Structure

Follow the template in `alldir_structure_template.md`:
- `/data/dsa110/raw/` - Raw HDF5 subband files from correlator
- `/data/dsa110/processed/ms/` - CASA Measurement Sets (temporary)
- `/data/dsa110/processed/images/` - FITS images (permanent)
- `/data/dsa110/calibration/` - Calibration tables
- `/data/dsa110/database/` - SQLite database
- `/data/dsa110/logs/` - Pipeline execution logs

**Active Code**: Use `pipeline/pipeline/` (new unified structure), not `pipeline/legacy/` or `backups/`.

## Critical Conversion Pipeline

### Subband File Patterns
```
2025-10-05T12:30:00_sb01.hdf5  # Timestamp must match exactly across all 16 subbands
2025-10-05T12:30:00_sb02.hdf5
...
2025-10-05T12:30:00_sb16.hdf5
```

### Two Processing Modes

1. **Batch Converter** (`pipeline/pipeline/core/conversion/uvh5_to_ms_converter.py`):
   - For historical/archived data processing
   - Function: `convert_subband_groups_to_ms(input_dir, output_dir, start_time, end_time)`
   - Groups files by timestamp, processes sequentially

2. **Streaming Converter** (`pipeline/pipeline/core/conversion/streaming_converter.py`):
   - Real-time daemon for live data ingest
   - SQLite-backed queue with checkpoint recovery
   - Run as systemd service or in screen session
   - **States**: `collecting` → `pending` → `in_progress` → `completed`/`failed`
   - **Performance tracking**: Records load/phase/write times per observation

### Conversion Data Flow
```
UVH5 files → pyuvdata.UVData → combine subbands → UVFITS (temp) → 
CASA importuvfits → MS → addImagingColumns → update antenna positions
```

**Key Implementation Details**:
- Use `pyuvdata.UVData()` with `strict_uvw_antpos_check=False` for DSA-110 compatibility
- Write temporary UVFITS before calling `importuvfits()` (required for metadata fidelity)
- Always add imaging columns via `casacore.tables.addImagingColumns()`
- Update antenna positions from `pipeline/pipeline/utils/data/DSA110_Station_Coordinates.csv`
- Clean up temporary UVFITS files unless `keep_uvfits=True`

## DSA-110 Specific Utilities

### Antenna Positions (`pipeline/pipeline/utils/antpos.py`)
```python
from pipeline.utils.antpos import get_itrf, get_lonlat
antpos = get_itrf()  # Returns ITRF coordinates as pandas DataFrame
```
- Reads from `DSA110_Station_Coordinates.csv`
- Filters out 200E/200W stations
- Returns shape (nants, 3) ITRF coordinates

### Fringestopping (`pipeline/pipeline/utils/fringestopping.py`)
```python
from pipeline.utils.fringestopping import calc_uvw_blt, phase_to_direction
# Calculate UVW coordinates using CASA measures
buvw = calc_uvw_blt(blen, tobs, 'J2000', src_lon, src_lat, obs='OVRO_MMA')
```
- Uses CASA tools (`casatools.measures()`) for coordinate transformations
- Adapted from dsacalib/dsamfs libraries
- Critical for phase referencing visibilities

### Constants (`pipeline/pipeline/utils/constants.py`)
```python
from pipeline.utils import constants as ct
# DSA-110 specific parameters like TSAMP, NINT, CASA_TIME_OFFSET
```

## MS I/O Pattern (`pipeline/pipeline/utils/ms_io.py`)

**Avoid CASA simulator** - causes performance issues and shape mismatches. Instead:
```python
from pipeline.utils.ms_io import convert_to_ms_data_driven, write_uvdata_to_ms_via_uvfits

# Data-driven MS creation (direct table manipulation)
convert_to_ms_data_driven(source, vis, obstm, ofile, bname, antenna_order, antpos=antpos)

# Or via UVFITS intermediate (more robust)
write_uvdata_to_ms_via_uvfits(uvdata, output_path, antenna_positions=antpos)
```

**Expected visibility shape**: `(nblt, nfreq, npol)` or `(nblt, nspw, nfreq, npol)`
- If `nspw=1`, squeeze that dimension before processing
- Typical: `nblt = nbaselines * ntimes`, `nfreq = 1024`, `npol = 4`

## Testing Patterns

Tests live in `pipeline/tests/unit/`. Example from `test_ms_io_uvfits.py`:
```python
# Mock CASA tools to avoid CASA dependency in tests
def test_write_uvdata_to_ms_via_uvfits(tmp_path, monkeypatch):
    fake_uv = FakeUVData()
    monkeypatch.setattr(ms_io, 'importuvfits', fake_importuvfits)
    monkeypatch.setattr(ms_io, 'table', fake_table)
    result = ms_io.write_uvdata_to_ms_via_uvfits(fake_uv, output_path, ...)
    assert result.exists()
```

**Run tests**: 
```bash
conda activate casa6
pytest pipeline/tests/unit/test_ms_io_uvfits.py -v
```

## Development Workflows

### Running Batch Conversion
```bash
conda activate casa6
python pipeline/pipeline/core/conversion/uvh5_to_ms_converter.py \
    /data/raw/2025-10-05 \
    /data/processed/ms \
    "2025-10-05 00:00:00" \
    "2025-10-05 23:59:59"
```

### Starting Streaming Daemon
```bash
conda activate casa6
python pipeline/pipeline/core/conversion/streaming_converter.py \
    --input-dir /data/incoming \
    --output-dir /data/processed/ms \
    --scratch-dir /data/scratch \
    --checkpoint-dir /data/checkpoints \
    --chunk-duration 5.0 \
    --omp-threads 4
```

### Queue Inspection
```bash
# Check streaming queue status
sqlite3 streaming_queue.sqlite3 \
  "SELECT group_id, state, processing_stage, retry_count FROM ingest_queue ORDER BY received_at DESC LIMIT 10;"

# Check performance metrics
sqlite3 streaming_queue.sqlite3 \
  "SELECT group_id, total_time, load_time, phase_time, write_time FROM performance_metrics ORDER BY recorded_at DESC LIMIT 10;"
```

### Creating Synthetic Test Data
```bash
conda activate casa6

# Quick single observation (16 subbands, 5 minutes)
python simulation/make_synthetic_uvh5.py \
    --layout-meta simulation/config/reference_layout.json \
    --telescope-config simulation/pyuvsim/telescope.yaml \
    --output /tmp/synthetic_test \
    --start-time "2025-10-06T12:00:00" \
    --duration-minutes 5.0

# Or use example scripts
./simulation/examples/basic_generation.sh

# Validate generated data
python simulation/validate_synthetic.py /tmp/synthetic_test/*.hdf5
```

## Migration Status & Code Organization

**Active Development**: Code is being refactored from `pipeline/legacy/` to `pipeline/pipeline/`

**Prefer**:
- ✅ `pipeline/pipeline/core/conversion/` - New unified converters
- ✅ `pipeline/pipeline/utils/` - Shared utilities (antpos, fringestopping, ms_io)

**Avoid**:
- ❌ `pipeline/legacy/` - Deprecated scripts (kept for reference only)
- ❌ `backups/` - Old deprecated code
- ❌ `references/` - External reference repositories (dsacalib, dsa110-xengine, etc.)

**Migration Guide**: See `pipeline/legacy/conversion/MIGRATION_GUIDE.md` for patterns when updating legacy code.

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

**Performance Warnings**: Groups taking >4.5 min indicate I/O bottlenecks or insufficient resources.

## Common Pitfalls

1. **Forgetting casa6 environment**: Always `conda activate casa6` before running scripts
2. **Processing individual subbands**: Must group by timestamp first, never process `_sb01.hdf5` alone
3. **Using legacy scripts**: Check `pipeline/pipeline/` first, not `pipeline/legacy/`
4. **pyuvdata compatibility**: Use `Nants_telescope`, not deprecated `Nants_data`
5. **MS shape mismatches**: Squeeze `nspw=1` dimension before processing
6. **Missing antenna positions**: Always update MS with DSA-110 station coordinates
7. **CASA simulator issues**: Use `convert_to_ms_data_driven()` or UVFITS path instead

## Key Files for Reference

- `reports/CONVERSION_PROCESS_SUMMARY.md` - Detailed conversion documentation
- `reports/DSA110_SUBBAND_UPDATE_SUMMARY.md` - Subband grouping architecture
- `pipeline/docs/streaming_converter_README.md` - Streaming daemon deployment
- `config/pipeline_config_template.yaml` - Pipeline configuration schema
- `alldir_structure_template.md` - Expected directory layout

## When Making Changes

1. **Subband Processing**: Any new converter must group files by timestamp (within 2.5 min)
2. **Testing**: Mock CASA tools (see `test_ms_io_uvfits.py` pattern)
3. **Antenna Positions**: Always use `pipeline/pipeline/utils/antpos.py`, not hardcoded values
4. **Error Handling**: Log to files in `/data/dsa110/logs/`, use structured logging
5. **Documentation**: Update corresponding README in `pipeline/docs/` when changing converters
6. **Configuration**: Use YAML configs from `config/`, not hardcoded parameters

## External Dependencies (References Only)

The `references/` directory contains external repos for context:
- `dsa110-calib/` - Original calibration library (source of fringestopping logic)
- `dsa110-meridian-fs/` - Meridian fringestopping reference
- `dsa110-xengine/` - Correlator output format documentation

**Do not modify** files in `references/` - they're read-only references.
