# Archived: calibration/qa.py

**Date:** 2025-11-05  
**Reason:** Consolidated with `qa/calibration_quality.py` for better organization

## Original Location
- `src/dsa110_contimg/calibration/qa.py`

## Why Archived

This module contained delay-specific QA functions that were misplaced in the `calibration/` package. QA functionality belongs in the `qa/` package for better organization.

## Functions Moved

All functions have been moved to `qa/calibration_quality.py`:

1. **`check_upstream_delay_correction()`** - Analyzes phase vs frequency to check if delays are corrected upstream
2. **`verify_kcal_delays()`** - Verifies K-calibration delay values and assesses their significance
3. **`inspect_kcal_simple()`** - Inspects K-calibration delay values from a calibration table

## Migration

**Old imports:**
```python
from dsa110_contimg.calibration.qa import check_upstream_delay_correction
from dsa110_contimg.calibration.qa import verify_kcal_delays
from dsa110_contimg.calibration.qa import inspect_kcal_simple
```

**New imports:**
```python
from dsa110_contimg.qa.calibration_quality import check_upstream_delay_correction
from dsa110_contimg.qa.calibration_quality import verify_kcal_delays
from dsa110_contimg.qa.calibration_quality import inspect_kcal_simple
```

**Or use the qa package import:**
```python
from dsa110_contimg.qa import (
    check_upstream_delay_correction,
    verify_kcal_delays,
    inspect_kcal_simple,
)
```

## Updated Files

- `src/dsa110_contimg/calibration/cli.py` - Updated imports for delay QA functions
- `src/dsa110_contimg/qa/calibration_quality.py` - Added delay-specific QA functions
- `src/dsa110_contimg/qa/__init__.py` - Exported delay QA functions

## Benefits

- **Better organization:** All QA functionality is now in the `qa/` package
- **Clearer separation:** Delay-specific QA is alongside general calibration QA
- **Consistent naming:** Follows the pattern of other QA modules

