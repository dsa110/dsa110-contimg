# Calibration Provenance Tracking Implementation

**Date**: 2025-01-XX  
**Status**: Complete  
**Priority**: High (Scientific Reproducibility Requirement)

## Overview

Implemented complete provenance tracking for calibration tables in the
calibration registry. This enhancement enables full reproducibility by capturing
source MS paths, solver commands, CASA versions, calibration parameters, and
quality metrics for all calibration tables.

## Problem Statement

The calibration registry previously lacked provenance information, making it
difficult to:

- Reproduce calibration results
- Track which MS files generated which calibration tables
- Understand calibration parameters used
- Analyze quality metrics across calibration runs
- Perform impact analysis when calibration tables change

## Solution

Added comprehensive provenance tracking that captures:

1. **Source MS Path**: Input measurement set that generated the caltable
2. **Solver Command**: Full CASA command executed
3. **Solver Version**: CASA version used (e.g., "6.7.2")
4. **Solver Parameters**: All calibration parameters as JSON
5. **Quality Metrics**: SNR statistics, flagged fraction, antenna/SPW counts

## Implementation Details

### Database Schema Changes

**File**: `src/dsa110_contimg/database/registry.py`

Added five new columns to `caltables` table:

- `source_ms_path TEXT` - Input MS that generated this caltable
- `solver_command TEXT` - Full CASA command executed
- `solver_version TEXT` - CASA version used
- `solver_params TEXT` - JSON: all calibration parameters
- `quality_metrics TEXT` - JSON: SNR, flagged_fraction, etc.

**Migration**: Automatic schema migration via `_migrate_schema()` function that
adds columns to existing databases without data loss.

**Index**: Added `idx_caltables_source` index on `source_ms_path` for efficient
queries.

### New Module: Provenance Tracking

**File**: `src/dsa110_contimg/database/provenance.py`

New module providing:

- `track_calibration_provenance()` - Store provenance for a caltable
- `query_caltables_by_source()` - Query all caltables from a specific MS
- `get_caltable_provenance()` - Get full provenance for a single caltable
- `impact_analysis()` - Find MS paths affected by caltable changes
- `CalTable` dataclass - Represents caltable with provenance

### Calibration Function Integration

**File**: `src/dsa110_contimg/calibration/calibration.py`

Added helper functions:

- `_get_casa_version()` - Detect CASA version (handles string/list/tuple
  formats)
- `_build_command_string()` - Build human-readable command strings
- `_extract_quality_metrics()` - Extract SNR, flagged fraction, antenna counts
- `_track_calibration_provenance()` - Track provenance after successful solve

**Integration Points**: Provenance tracking automatically called after
successful solves in:

- `solve_delay()` - Slow and fast delay solves
- `solve_prebandpass_phase()` - Pre-bandpass phase solve
- `solve_bandpass()` - Bandpass solve
- `solve_gains()` - Phase-only and short-timescale gain solves

**Error Handling**: Provenance tracking failures are non-blocking - calibration
continues even if provenance tracking fails.

## Usage Examples

### Query Calibration Tables by Source MS

```python
from dsa110_contimg.database.provenance import query_caltables_by_source
from pathlib import Path

registry_db = Path("/data/dsa110-contimg/state/cal_registry.sqlite3")
ms_path = "/stage/dsa110-contimg/ms/2025-01-15T12:00:00.ms"

# Get all calibration tables generated from this MS
caltables = query_caltables_by_source(registry_db, ms_path)

for caltable in caltables:
    print(f"Table: {caltable.path}")
    print(f"Type: {caltable.table_type}")
    print(f"CASA Version: {caltable.solver_version}")
    print(f"SNR Mean: {caltable.quality_metrics.get('snr_mean')}")
```

### Get Full Provenance for a Calibration Table

```python
from dsa110_contimg.database.provenance import get_caltable_provenance

caltable = get_caltable_provenance(registry_db, "/path/to/caltable_kcal")

if caltable:
    print(f"Source MS: {caltable.source_ms_path}")
    print(f"Command: {caltable.solver_command}")
    print(f"Parameters: {caltable.solver_params}")
    print(f"Quality Metrics: {caltable.quality_metrics}")
```

### Impact Analysis

```python
from dsa110_contimg.database.provenance import impact_analysis

# Find all MS files affected by changes to these calibration tables
affected_ms_paths = impact_analysis(
    registry_db,
    ["/path/to/caltable1_kcal", "/path/to/caltable2_bpcal"]
)

print(f"Affected MS files: {affected_ms_paths}")
```

### Manual Provenance Tracking

```python
from dsa110_contimg.database.provenance import track_calibration_provenance

track_calibration_provenance(
    registry_db=registry_db,
    ms_path="/path/to/input.ms",
    caltable_path="/path/to/caltable.cal",
    params={"field": "0", "refant": "103", "gaintype": "K"},
    metrics={"snr_mean": 10.5, "n_solutions": 100},
    solver_command="gaincal(vis='/path/to/input.ms', ...)",
    solver_version="6.7.2",
)
```

## Testing

### Unit Tests

**Files**:

- `tests/unit/database/test_calibration_provenance.py` (14 tests)
- `tests/unit/calibration/test_calibration_provenance_helpers.py` (14 tests)
- `tests/unit/calibration/test_calibration_provenance_smoke.py` (7 tests)

**Coverage**:

- Database schema migration
- Provenance tracking functions
- CASA version detection
- Command string building
- Quality metrics extraction
- End-to-end integration workflows

**Results**: All 35 tests passing in < 1.2 seconds

### Test Execution

```bash
# Run all provenance tests
/opt/miniforge/envs/casa6/bin/python -m pytest \
    tests/unit/database/test_calibration_provenance.py \
    tests/unit/calibration/test_calibration_provenance_helpers.py \
    tests/unit/calibration/test_calibration_provenance_smoke.py \
    -v

# Run smoke tests only (fastest)
/opt/miniforge/envs/casa6/bin/python -m pytest \
    tests/unit/calibration/test_calibration_provenance_smoke.py \
    -v
```

## Database Migration

Existing calibration registry databases are automatically migrated when
accessed:

1. `ensure_db()` checks for existing columns
2. `_migrate_schema()` adds missing provenance columns
3. Existing data is preserved (new columns are NULL for old entries)
4. Index is created on `source_ms_path`

**No manual migration required** - happens automatically on first access.

## Quality Metrics Captured

The following metrics are automatically extracted from calibration tables:

- `n_solutions` - Total number of solutions
- `flagged_fraction` - Fraction of solutions flagged (0.0-1.0)
- `snr_mean` - Mean SNR across all solutions
- `snr_median` - Median SNR
- `snr_min` - Minimum SNR
- `snr_max` - Maximum SNR
- `n_antennas` - Number of unique antennas
- `n_spws` - Number of unique spectral windows

## CASA Version Detection

The system automatically detects CASA version using multiple fallback methods:

1. `casatools.version()` (primary)
2. `casatasks.version()` (fallback)
3. `CASA_VERSION` environment variable (fallback)

Handles both string format ("6.7.2") and list/tuple formats ([6, 7, 2]).

## Backward Compatibility

- Existing calibration tables continue to work without provenance
- NULL values are allowed for all provenance fields
- Old calibration workflows continue to function
- New provenance is captured automatically for new calibrations

## Future Enhancements

Potential improvements:

1. Track which MS files actually used which calibration tables (applycal
   tracking)
2. Version control for calibration parameters
3. Automated quality metric analysis and alerts
4. Provenance visualization in dashboard
5. Export provenance reports for publications

## Related Documentation

- Database Schema: `docs/reference/database_schema.md`
- Calibration Procedures: `docs/how-to/CALIBRATION_DETAILED_PROCEDURE.md`
- API Reference: `src/dsa110_contimg/database/provenance.py` (docstrings)

## Files Modified

1. `src/dsa110_contimg/database/registry.py` - Schema, migration, CalTableRow
2. `src/dsa110_contimg/database/provenance.py` - New module (created)
3. `src/dsa110_contimg/calibration/calibration.py` - Integration, helpers
4. `tests/unit/database/test_calibration_provenance.py` - Unit tests (created)
5. `tests/unit/calibration/test_calibration_provenance_helpers.py` - Helper
   tests (created)
6. `tests/unit/calibration/test_calibration_provenance_smoke.py` - Smoke tests
   (created)

## Verification

To verify the implementation:

```bash
# 1. Check database schema
sqlite3 /data/dsa110-contimg/state/cal_registry.sqlite3 \
    "PRAGMA table_info(caltables);" | grep -E "source_ms_path|solver_"

# 2. Run tests
/opt/miniforge/envs/casa6/bin/python -m pytest \
    tests/unit/database/test_calibration_provenance.py \
    tests/unit/calibration/test_calibration_provenance_helpers.py \
    tests/unit/calibration/test_calibration_provenance_smoke.py \
    -v

# 3. Test provenance tracking in Python
/opt/miniforge/envs/casa6/bin/python -c "
from dsa110_contimg.database.provenance import get_caltable_provenance
from pathlib import Path
import sys
sys.path.insert(0, 'src')
# Test imports work
print('Provenance module imported successfully')
"
```

## Summary

Complete provenance tracking is now implemented and automatically captures:

- Source MS paths
- CASA commands and versions
- Calibration parameters
- Quality metrics

This enables full scientific reproducibility and facilitates calibration
analysis and debugging. The implementation is backward-compatible, non-blocking,
and includes comprehensive test coverage.
