# Calibration Service Architecture

## Overview

The calibration system is split into three distinct services aligned with the pipeline stages:

1. **ConversionService** (UVH5 → MS)
   - Converts raw visibility data to Measurement Sets
   - Located: `conversion/strategies/hdf5_orchestrator.py`
   - **Status**: Already exists, may be enhanced with unified interface

2. **CalibrationSolvingService** (MS → Calibration Tables)
   - Solves for calibration tables (K, BP, G) on calibrator fields
   - Located: `calibration/calibration.py` (functions exist)
   - **Status**: To be implemented as service wrapper
   - **Dependencies**: Requires MS from ConversionService

3. **CalibrationApplicationService** (Calibration Tables → CORRECTED_DATA)
   - Applies existing calibration tables to target MS files
   - Located: `calibration/apply_service.py` (NEW)
   - **Status**: ✓ Implemented
   - **Dependencies**: Requires MS from ConversionService, caltables from CalibrationSolvingService

## Why Separate Services?

### Stage Separation
- **Solving**: Happens on calibrator fields (specific science target)
- **Application**: Happens on all target fields (uses solved tables)
- **Different workflows**: Solving requires calibrator detection, field selection, flux scaling
- **Different dependencies**: Solving requires MS + calibrator info; Application requires MS + caltables

### Current Code Organization
- `calibration/calibration.py` - Solving functions (`solve_delay()`, `solve_bandpass()`, `solve_gains()`)
- `calibration/applycal.py` - Application function (`apply_to_target()`)
- Already separate modules - service layer organizes existing separation

### Workflow Example
```
1. Convert calibrator MS → ConversionService
2. Solve calibration → CalibrationSolvingService (new caltables)
3. Register caltables → Database registry
4. Convert target MS → ConversionService
5. Apply calibration → CalibrationApplicationService (uses registered caltables)
```

## CalibrationApplicationService Implementation

### Functions

1. **`get_active_caltables()`**
   - Looks up calibration tables from registry
   - Handles MJD extraction from MS
   - Supports explicit set_name or automatic selection

2. **`verify_calibration_applied()`**
   - Checks CORRECTED_DATA is populated
   - Samples data for efficiency
   - Returns diagnostic metrics

3. **`apply_calibration()`**
   - Main entry point
   - Orchestrates lookup → apply → verify → database update
   - Returns structured result with diagnostics

### Usage Example

```python
from dsa110_contimg.calibration.apply_service import apply_calibration
from pathlib import Path

result = apply_calibration(
    ms_path="/data/ms/target.ms",
    registry_db=Path("state/cal_registry.sqlite3"),
    verify=True,
    update_db=True,
    products_db=Path("state/products.sqlite3")
)

if result.success:
    print(f"Applied {len(result.caltables_applied)} tables")
    print(f"Verified: {result.verified}")
else:
    print(f"Failed: {result.error}")
```

## Next Steps: CalibrationSolvingService

The solving service would wrap existing functions:

```python
# calibration/solve_service.py (to be implemented)

def solve_calibration(
    ms_path: str,
    cal_field: str,
    refant: str,
    *,
    registry_db: Path,
    table_prefix: Optional[str] = None,
    do_flagging: bool = True,
    fast_mode: bool = False,
    ...
) -> CalibrationSolvingResult:
    """Solve K, BP, G tables and register in database."""
    # Uses existing: solve_delay(), solve_bandpass(), solve_gains()
    # Registers tables via database/registry.py
```

## Benefits of Separation

1. **Clear Responsibilities**: Each service has single, well-defined purpose
2. **Reusability**: Can solve calibration independently of application
3. **Testability**: Each service can be tested in isolation
4. **Workflow Flexibility**: Different workflows can use different combinations
5. **Matches Existing Architecture**: Aligns with current module separation

