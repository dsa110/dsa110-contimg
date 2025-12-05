# Conversion Module

Converts UVH5 (HDF5) visibility data to CASA Measurement Sets.

## Overview

The DSA-110 telescope produces **16 subband files per observation** that must be
grouped by timestamp and combined before creating a single Measurement Set.

```text
16 UVH5 files (*_sb00.hdf5 ... *_sb15.hdf5)
    ↓
Group by timestamp:
  • Streaming: normalize filenames on ingest (preferred)
  • Batch: cluster within 60s tolerance (legacy)
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

### 2. Streaming Conversion

Real-time daemon for live data:

```bash
# Via systemd (production)
sudo systemctl start contimg-stream.service

# Manual testing
python -m dsa110_contimg.conversion.streaming.streaming_converter \
    --input-dir /data/incoming \
    --output-dir /stage/dsa110-contimg/ms
```

## Key Files

| File                               | Purpose                       |
| ---------------------------------- | ----------------------------- |
| `cli.py`                           | Command-line interface        |
| `strategies/hdf5_orchestrator.py`  | Batch conversion logic        |
| `strategies/writers.py`            | MS writer factory             |
| `strategies/direct_subband.py`     | Parallel subband writer       |
| `streaming/streaming_converter.py` | Real-time daemon              |
| `helpers_coordinates.py`           | Phase center calculations     |
| `helpers_antenna.py`               | Antenna utilities             |
| `ms_utils.py`                      | Measurement Set configuration |

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

1. **Subband grouping**: Two mechanisms (see below)
2. **Subband combining**: Use `pyuvdata.UVData()` with `+=` operator
3. **Antenna positions**: Always update from `utils/antpos_local/`
4. **Phase center**: Visibilities phased to meridian
5. **Calibrator detection**: Auto-renames field containing calibrator

### Subband Grouping Mechanisms

| Method             | Code Location                       | Tolerance | Use Case               |
| ------------------ | ----------------------------------- | --------- | ---------------------- |
| **Normalization**  | `streaming/`                        | 60s       | Rename files on ingest |
| **Time-Windowing** | `hdf5_index.query_subband_groups()` | 60s       | Query-time clustering  |

Both use 60-second tolerance (configured in `settings.conversion.cluster_tolerance_s`).

## Testing

```bash
# Generate synthetic test data
python -m dsa110_contimg.simulation.generate_uvh5 --output-dir /tmp/test

# Run conversion tests
python -m pytest tests/unit/conversion/ -v
```
