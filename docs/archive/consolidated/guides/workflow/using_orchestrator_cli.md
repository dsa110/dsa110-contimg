# Using the Conversion Orchestrator CLI

**Purpose**: This document explains how to use the unified orchestrator CLI for
UVH5 :arrow_right: MS conversion. The orchestrator CLI is the **single, canonical pathway**
for all conversion workflows, with flags enabling different modes.

**Location**: `docs/how-to/USING_ORCHESTRATOR_CLI.md`  
**Related**: `docs/how-to/FIND_CALIBRATOR_TRANSIT_DATA.md`

## Philosophy: One Pathway with Flags

The orchestrator CLI (`dsa110_contimg.conversion.strategies.hdf5_orchestrator_orchestrator`)
is the **single entry point** for all conversion workflows. Instead of creating
separate scripts for different use cases, we use flags to enable different
modes:

- **Standard mode**: Explicit time window (`start_time` and `end_time`)
- **Calibrator mode**: Automatic transit finding (`--calibrator`)

This keeps the codebase clean and avoids redundant wrapper scripts.

## Basic Usage

### Mode 1: Explicit Time Window (Production Streaming)

This is the default mode used by the streaming pipeline:

```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-10-30 13:00:00" \
    "2025-10-30 14:00:00" \
    --writer parallel-subband \
    --stage-to-tmpfs
```

**Output**: MS files are written directly to organized locations:

- `ms/science/YYYY-MM-DD/<timestamp>.ms` (default)
- `ms/calibrators/YYYY-MM-DD/<timestamp>.ms` (if calibrator detected)
- `ms/failed/YYYY-MM-DD/<timestamp>.ms` (if conversion fails)

**When to use**: Processing all groups in a time window (streaming pipeline,
batch processing)

### Mode 2: Calibrator Transit (Find Transit Automatically)

This mode finds the calibrator transit and calculates the time window
automatically:

```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    --calibrator 0834+555 \
    --writer parallel-subband \
    --stage-to-tmpfs
```

**When to use**: Processing a specific calibrator transit (most recent
available)

### Mode 3: Specific Calibrator Transit Date

To target a specific transit date:

```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    --calibrator 0834+555 \
    --transit-date 2025-10-30 \
    --writer parallel-subband \
    --stage-to-tmpfs
```

**When to use**: Processing a specific calibrator transit on a known date

### Mode 4: Specific Transit Time

For a known transit time:

```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    --calibrator 0834+555 \
    --transit-date 2025-10-30T13:51:30 \
    --writer parallel-subband \
    --stage-to-tmpfs
```

**When to use**: Processing a specific calibrator transit with a known exact
time

## Calibrator Mode Options

When using `--calibrator`, you can customize the search:

- `--window-minutes`: Search window in minutes around transit (default: 60,
  i.e., ±30 minutes)
- `--max-days-back`: Maximum days to search back (default: 30)
- `--transit-date`: Specific date (YYYY-MM-DD) or time (YYYY-MM-DDTHH:MM:SS)

Example with custom window:

```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    --calibrator 0834+555 \
    --transit-date 2025-10-30 \
    --window-minutes 120 \
    --max-days-back 60 \
    --writer parallel-subband
```

## What Happens in Calibrator Mode

1. **Finds transit**: Uses `CalibratorMSGenerator.find_transit()` to locate the
   transit
2. **Verifies data**: Checks that subband groups exist for that transit time
3. **Calculates window**: Computes `start_time` and `end_time` based on transit
   ± window
4. **Converts groups**: Calls the standard conversion pipeline with the
   calculated window

The orchestrator logs the transit information:

```
INFO: Finding transit for calibrator: 0834+555
INFO: Calibrator transit found:
INFO:   Transit time: 2025-10-30T13:51:30
INFO:   Group ID: 2025-10-30T13:34:54
INFO:   Search window: 2025-10-30T13:21:30 to 2025-10-30T14:21:30
INFO:   Files: 16 subband files
```

## Common Workflows

### Workflow 1: Test Pipeline on Specific Transit

```bash
# Find and convert 0834+555 transit on 2025-10-30
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator_orchestrator \
    /data/incoming \
    /tmp/test-ms \
    --calibrator 0834+555 \
    --transit-date 2025-10-30 \
    --writer parallel-subband \
    --stage-to-tmpfs
```

### Workflow 2: Process Most Recent Transit

```bash
# Process most recent 0834+555 transit (no date specified)
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    --calibrator 0834+555 \
    --writer parallel-subband
```

### Workflow 3: Batch Processing (Standard Mode)

```bash
# Process all groups in time window (streaming pipeline style)
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-10-30 00:00:00" \
    "2025-10-31 00:00:00" \
    --writer parallel-subband \
    --stage-to-tmpfs
```

## Why This Approach?

**Before**: Multiple scripts (`generate_calibrator_ms.py`,
`generate_transit_hour_ms.py`, etc.) that duplicated logic and created confusion
about which tool to use.

**Now**: Single orchestrator CLI with flags. One pathway, different modes
enabled by flags.

**Benefits**:

- **Clear entry point**: Always use the orchestrator CLI
- **No redundancy**: Logic lives in one place (orchestrator +
  CalibratorMSGenerator service)
- **Consistent behavior**: Same conversion pipeline regardless of mode
- **Easier maintenance**: Changes to conversion logic affect all use cases

## Integration with Other Pipeline Stages

The orchestrator CLI is designed to work with other pipeline stages:

1. **Conversion** (this tool): UVH5 :arrow_right: MS
2. **Calibration**: `python -m dsa110_contimg.calibration.cli`
3. **Imaging**: `python -m dsa110_contimg.imaging.cli`

Each stage has its own CLI with flags for different modes. The orchestrator CLI
focuses solely on conversion.

## See Also

- **Finding transit data**: `docs/how-to/FIND_CALIBRATOR_TRANSIT_DATA.md`
- **CalibratorMSGenerator**:
  `backend/src/dsa110_contimg/conversion/calibrator_ms_service.py`
- **Conversion process**: `docs/archive/reports/`
