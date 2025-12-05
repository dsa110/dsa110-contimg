# Conversion Module

Converts UVH5 (HDF5) visibility data to CASA Measurement Sets.

## Overview

The DSA-110 telescope produces **16 subband files per observation** that must be
grouped by timestamp and combined before creating a single Measurement Set.

```text
16 UVH5 files (*_sb00.hdf5 ... *_sb15.hdf5)
    ↓
Group by timestamp (60s tolerance)
    ↓
Combine subbands (pyuvdata +=)
    ↓
Write Measurement Set
    ↓
Configure for imaging (antenna positions, field names)
```

## Two Processing Modes

### 1. Batch Conversion

For historical/archived data:

```bash
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-01-01T00:00:00" \
    "2025-01-01T12:00:00"
```

### 2. ABSURD Ingestion

For scheduled/automated data ingest (EXPERIMENTAL):

- Uses PostgreSQL-backed task queue with durable execution
- Run via scheduler or API triggers
- See `backend/src/dsa110_contimg/absurd/` for details

## Key Files

| File                     | Purpose                       |
| ------------------------ | ----------------------------- |
| `cli.py`                 | Command-line interface        |
| `hdf5_orchestrator.py`   | Batch conversion logic        |
| `writers.py`             | MS writer factory             |
| `direct_subband.py`      | Parallel subband writer       |
| `helpers_coordinates.py` | Phase center calculations     |
| `helpers_antenna.py`     | Antenna utilities             |
| `ms_utils.py`            | Measurement Set configuration |

## CLI Options

```bash
python -m dsa110_contimg.conversion.cli groups --help

# Key options:
#   --dry-run                    Preview without writing
#   --skip-existing              Skip already-converted groups
#   --calibrator NAME            Auto-find calibrator transit
#   --writer {parallel-subband}  MS writing strategy
#   --no-rename-calibrator-fields  Disable auto field naming
```

## Critical Implementation Details

1. **Subband grouping**: Uses 60-second time-windowing via `query_subband_groups()`
2. **Subband combining**: Use `pyuvdata.UVData()` with `+=` operator
3. **Antenna positions**: Always update from `utils/antpos_local/`
4. **Phase center**: Visibilities phased to meridian
5. **Calibrator detection**: Auto-renames field containing calibrator

### Subband Grouping

Files within 60 seconds are clustered into the same observation group:

```python
from dsa110_contimg.database.hdf5_index import query_subband_groups
groups = query_subband_groups(db_path, start, end, cluster_tolerance_s=60.0)
```

Tolerance is configured in `settings.conversion.cluster_tolerance_s`.

## Testing

```bash
# Generate synthetic test data
python -m dsa110_contimg.simulation.generate_uvh5 --output-dir /tmp/test

# Run conversion tests
python -m pytest tests/unit/conversion/ -v
```
