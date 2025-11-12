# Archived: calibration/imaging.py

**Date:** 2025-11-05  
**Reason:** Misplaced module - imaging functionality belongs in `imaging/` package, not `calibration/`

## Original Location
- `src/dsa110_contimg/calibration/imaging.py`

## Why Archived

This module contains `quick_image()` function which is imaging functionality, not calibration functionality. It was misplaced in the calibration package.

## Replacement

The `imaging/cli.py` module provides comprehensive imaging functionality including:
- `image_ms()` function with `quick=True` parameter
- Full CLI support with `--quick` flag
- More features than the simple `quick_image()` wrapper

## Migration

**If you need quick imaging:**

1. **Use the CLI:**
   ```python
   python -m dsa110_contimg.imaging.cli image --ms MS.ms --imagename output --quick
   ```

2. **Use the function directly:**
   ```python
   from dsa110_contimg.imaging.cli import image_ms
   image_ms(ms_path, imagename="output", quick=True)
   ```

3. **If you specifically need the simple wrapper:**
   - The archived function is available at: `archive/legacy/calibration/imaging.py`
   - But consider using `image_ms(..., quick=True)` instead for better functionality

## Current Usage

This module was used by:
- `imaging/worker.py` - Needs to be updated to use `imaging/cli.py` instead
- `tests/utils/cal_ms_demo.py` - Needs to be updated

## Action Required

Update imports in:
- `src/dsa110_contimg/imaging/worker.py` (line 96)
- `tests/utils/cal_ms_demo.py` (line 13)

Replace:
```python
from dsa110_contimg.calibration.imaging import quick_image
```

With:
```python
from dsa110_contimg.imaging.cli import image_ms
# Then call: image_ms(ms, imagename=imagename, field=field, quick=True, ...)
```

