# CalibrationApplicationService Implementation Summary

## Date: 2025-01-XX

## What Was Created

**File**: `src/dsa110_contimg/calibration/apply_service.py`

A unified service for applying calibration tables to Measurement Sets that consolidates duplicate logic found across 5+ scripts.

## Functions Implemented

### 1. `get_active_caltables(ms_path, registry_db, *, set_name=None, mid_mjd=None)`

**Purpose**: Lookup active calibration tables from registry database

**Features**:
- Extracts MS mid-MJD automatically (multiple fallback methods)
- Queries `cal_registry.sqlite3` for active tables
- Supports explicit set_name or automatic selection
- Returns ordered list of calibration table paths

**Returns**: `List[str]` - Ordered calibration table paths

**Raises**: `ValueError` if mid_mjd cannot be determined

### 2. `verify_calibration_applied(ms_path, *, sample_fraction=0.1, min_nonzero_samples=10)`

**Purpose**: Verify CORRECTED_DATA is populated after calibration

**Features**:
- Samples MS data (default: 10% of rows, max 1024 rows)
- Checks for CORRECTED_DATA column presence
- Verifies non-zero samples exist
- Returns diagnostic metrics

**Returns**: `Tuple[bool, dict]` - (verified, metrics)

### 3. `apply_calibration(ms_path, registry_db, *, caltables=None, set_name=None, field="", verify=True, update_db=False, products_db=None, sample_fraction=0.1)`

**Purpose**: Main entry point - applies calibration with full workflow

**Features**:
- Automatic caltable lookup (if not provided)
- Table existence verification
- Calibration application via `apply_to_target()`
- Optional verification (checks CORRECTED_DATA)
- Optional database updates (ms_index.cal_applied)
- Comprehensive error handling and logging

**Returns**: `CalibrationApplicationResult` dataclass with:
- `success`: bool
- `caltables_applied`: List[str]
- `verified`: bool
- `error`: Optional[str]
- `metrics`: Optional[dict]

## Key Features

### Error Handling
- Graceful fallbacks for MJD extraction
- Clear error messages at each stage
- Logging at appropriate levels (INFO, WARNING, ERROR)

### Verification
- Efficient sampling (not full MS scan)
- Configurable sample fraction
- Diagnostic metrics for troubleshooting

### Database Integration
- Optional products database updates
- Updates `ms_index.cal_applied` flag
- Updates `stage` and `stage_updated_at` timestamps

### Backward Compatibility
- Can accept explicit caltables (bypasses registry lookup)
- Can skip verification (verify=False)
- Can skip database updates (update_db=False)

## Usage Examples

### Basic Usage (Automatic Lookup)

```python
from dsa110_contimg.calibration.apply_service import apply_calibration
from pathlib import Path

result = apply_calibration(
    ms_path="/data/ms/target.ms",
    registry_db=Path("state/cal_registry.sqlite3"),
    verify=True
)

if result.success:
    print(f"Applied {len(result.caltables_applied)} tables")
else:
    print(f"Failed: {result.error}")
```

### With Database Updates

```python
result = apply_calibration(
    ms_path="/data/ms/target.ms",
    registry_db=Path("state/cal_registry.sqlite3"),
    verify=True,
    update_db=True,
    products_db=Path("state/products.sqlite3")
)
```

### Explicit Caltables (Bypass Registry)

```python
result = apply_calibration(
    ms_path="/data/ms/target.ms",
    registry_db=Path("state/cal_registry.sqlite3"),
    caltables=["/data/ms/cal.kcal", "/data/ms/cal.bpcal", "/data/ms/cal.gpcal"],
    verify=True
)
```

### Specific Calibration Set

```python
result = apply_calibration(
    ms_path="/data/ms/target.ms",
    registry_db=Path("state/cal_registry.sqlite3"),
    set_name="nightly_2025_01_15",
    verify=True
)
```

## Integration Points

### Existing Functions Used

- `calibration/applycal.py::apply_to_target()` - Core CASA applycal wrapper
- `database/registry.py::get_active_applylist()` - Registry lookup
- `database/products.py::ms_index_upsert()` - Database updates
- `casacore.tables::table` - MS access and verification

### No Breaking Changes

- All existing functions remain unchanged
- Service wraps existing functions
- Scripts can continue using `apply_to_target()` directly
- Gradual migration possible

## Next Steps

1. **Update Scripts**: Replace duplicate calibration application code with service calls
   - `ops/pipeline/build_calibrator_transit_offsets.py`
   - `ops/pipeline/image_groups_in_timerange.py`
   - `ops/pipeline/run_next_field_after_central.py`
   - `imaging/worker.py::_apply_and_image()`
   - Other scripts with inline applycal logic

2. **Create CalibrationSolvingService**: Next service to implement
   - Wrap `solve_delay()`, `solve_bandpass()`, `solve_gains()`
   - Handle calibration table registration
   - Return structured results

3. **Testing**: Add unit tests for service functions
   - Test caltable lookup
   - Test verification logic
   - Test error handling
   - Test database updates

## Benefits Delivered

✓ **Eliminates Duplication**: Single implementation replaces 5+ duplicate code blocks
✓ **Consistent Interface**: Same API across all scripts
✓ **Better Error Handling**: Comprehensive error messages and logging
✓ **Verification Built-in**: Automatic CORRECTED_DATA checking
✓ **Database Integration**: Optional automatic status updates
✓ **Backward Compatible**: Doesn't break existing code
✓ **Follows Architecture**: Matches existing patterns (functional helpers, database-driven)

