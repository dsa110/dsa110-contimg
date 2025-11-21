# Calibrator MS Files and `calib_ms/` Directory

## Overview

There are **two different concepts** related to calibrator MS files in the
pipeline:

1. **Calibrator MS files** - MS files that contain calibrator sources (e.g.,
   0834+555)
2. **Calibrated MS files (`calib_ms` type)** - MS files (science or calibrator)
   that have had calibration tables applied

## Directory Structure

### Calibrator MS Files Location

**Calibrator MS files** (MS files containing calibrator sources) are stored in:

```
/stage/dsa110-contimg/ms/calibrators/YYYY-MM-DD/<timestamp>.ms/
```

These are:

- Detected by checking if the MS contains a calibrator source
- Organized by date in the `ms/calibrators/` subdirectory
- Distinguished from science MS files which go to `ms/science/YYYY-MM-DD/`

### Calibrated MS Files (`calib_ms` type)

**Calibrated MS files** are MS files that have had calibration tables applied to
them. According to the configuration:

- **Staging directory**: `/stage/dsa110-contimg/calib_ms/`
- **Published directory**: `/data/dsa110-contimg/products/calib_ms/`

However, based on the code analysis:

**Current behavior**: When calibration is applied to an MS file:

1. The MS file **stays in its original location** (`ms/science/` or
   `ms/calibrators/`)
2. It is **registered in the data_registry** with `data_type="calib_ms"` to
   indicate it has been calibrated
3. The file path in the registry points to the original location in `ms/`

**Note**: The `calib_ms/` directory exists but appears to be **currently
empty/unused** in practice. The pipeline registers calibrated MS files with
`data_type="calib_ms"` but doesn't move them to the `calib_ms/` directory.

## Code References

### Calibrator MS Detection

- **Function**: `determine_ms_type()` in
  `dsa110_contimg/utils/ms_organization.py`
- **Logic**: Checks if MS contains a calibrator source or is in `calibrators/`
  directory
- **Organization**: Files are moved to `ms/calibrators/YYYY-MM-DD/` via
  `organize_ms_file()`

### Calibrated MS Registration

- **Location**: `dsa110_contimg/pipeline/stages_impl.py` (calibration
  application stage)
- **When**: After calibration tables are successfully applied to an MS file
- **Registration**:
  ```python
  register_pipeline_data(
      data_type="calib_ms",
      data_id=f"calib_{ms_path_obj}",
      file_path=ms_path_obj,  # Original location in ms/science/ or ms/calibrators/
      metadata={
          "calibration_applied": True,
          "calibration_tables": applylist,
      },
      auto_publish=True,
  )
  ```

### Configuration

- **File**: `dsa110_contimg/database/data_config.py`
- **Staging dir**: `STAGE_BASE / "calib_ms"` = `/stage/dsa110-contimg/calib_ms/`
- **Auto-publish criteria**: Requires QA status = "passed"

## Summary

**Which calibrator MS go to `calib_ms/`?**

**Answer**: Currently, **none** are moved to `calib_ms/` in practice. The
`calib_ms/` directory is configured but appears unused. Instead:

1. **Calibrator MS files** (containing calibrator sources) →
   `ms/calibrators/YYYY-MM-DD/`
2. **Calibrated MS files** (any MS with calibration applied) → Stay in original
   location (`ms/science/` or `ms/calibrators/`) but registered with
   `data_type="calib_ms"` in the database

The `calib_ms/` directory exists as a staging location according to the
configuration, but the current implementation keeps calibrated MS files in their
original `ms/` subdirectories and only changes their registration type in the
data registry.
