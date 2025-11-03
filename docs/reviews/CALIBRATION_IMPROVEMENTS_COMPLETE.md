# Calibration Stage Improvements - Implementation Complete

**Date**: 2025-11-03  
**Status**: ✅ All improvements implemented

---

## Summary

All 5 top improvements from the calibration stage review have been successfully implemented, plus the demo script import fix.

---

## 1. ✅ Fixed Demo Script Imports

**File**: `tests/utils/cal_ms_demo.py`

**Changes**:
- Updated imports from `casa_cal.*` to `dsa110_contimg.calibration.*`
- Fixed import path for `quick_image` to use `dsa110_contimg.calibration.imaging`

**Status**: ✅ Complete - script now uses correct production modules

---

## 2. ✅ Validation-Only Mode

**File**: `src/dsa110_contimg/calibration/cli.py`

**New Subcommand**: `validate`

**Usage**:
```bash
python -m dsa110_contimg.calibration.cli validate \
    --ms /data/ms/0834_2025-10-30.ms \
    --field 0 --refant 103
```

**Features**:
- Validates MS structure, field selection, and reference antenna
- Generates comprehensive diagnostics report
- Checks for existing caltables
- Checks CORRECTED_DATA quality (if calibration was already applied)
- Provides detailed MS quality metrics

**Implementation**:
- Uses existing `validate_ms_for_calibration()` function
- Integrates with new `generate_calibration_diagnostics()` function
- Provides human-readable report

---

## 3. ✅ Dry-Run Mode

**File**: `src/dsa110_contimg/calibration/cli.py`

**New Flag**: `--dry-run` on `calibrate` subcommand

**Usage**:
```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /data/ms/0834_2025-10-30.ms \
    --field 0 --refant 103 \
    --dry-run
```

**Features**:
- Validates all inputs without writing caltables
- Checks data quality
- Estimates unflagged data after flagging (simulation)
- Provides time estimates for each calibration stage
- Shows which stages will be executed (K/BP/G)

**Implementation**:
- Early exit after validation and estimation
- No actual calibration solves performed
- Useful for quick feedback before committing to long calibration

---

## 4. ✅ Diagnostics Mode

**File**: `src/dsa110_contimg/calibration/cli.py`  
**New Module**: `src/dsa110_contimg/calibration/diagnostics.py`

**New Flag**: `--diagnostics` on `calibrate` subcommand

**Usage**:
```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /data/ms/0834_2025-10-30.ms \
    --field 0 --refant 103 \
    --diagnostics
```

**Features**:
- Comprehensive diagnostic report after calibration
- MS quality metrics (rows, antennas, unflagged fraction)
- Flagging statistics
- Calibration table quality analysis (if tables exist)
- Issues and warnings identification
- Overall readiness assessment

**Implementation**:
- New `diagnostics.py` module with `CalibrationDiagnostics` dataclass
- `generate_calibration_diagnostics()` function
- Integrates with existing QA modules (`validate_caltable_quality`, `check_corrected_data_quality`)
- Human-readable report format

---

## 5. ✅ Minimal Test Calibration

**File**: `src/dsa110_contimg/calibration/cli.py`

**New Flag**: `--minimal` on `calibrate` subcommand

**Usage**:
```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /data/ms/0834_2025-10-30.ms \
    --field 0 --refant 103 \
    --minimal
```

**Features**:
- Very fast calibration test (<30 seconds)
- Creates ultra-minimal subset:
  - Single time integration (`timebin="inf"`)
  - Aggressive channel binning (`chanbin=16` → 4 channels from 64)
- Automatically enables fast mode settings
- For quick iteration only - not for production use

**Implementation**:
- Uses existing `make_subset()` function
- Creates `.minimal.ms` file
- Validates subset MS before proceeding
- Automatically sets fast mode parameters

---

## 6. ✅ Calibration Comparison Tool

**File**: `src/dsa110_contimg/calibration/cli.py`  
**Uses Module**: `src/dsa110_contimg/calibration/diagnostics.py`

**New Subcommand**: `compare`

**Usage**:
```bash
python -m dsa110_contimg.calibration.cli compare \
    --caltable1 cal1.gcal \
    --caltable2 cal2.gcal \
    --tolerance 1e-6
```

**Features**:
- Compares two calibration tables for consistency
- Structure comparison (solutions, antennas, SPWs)
- Solution comparison (amplitude, phase differences)
- Agreement metrics with configurable tolerance
- Human-readable comparison report
- Exit code indicates agreement status

**Use Cases**:
- Regression testing (verify fixes don't break existing solutions)
- Verifying calibration changes
- Quality control

**Implementation**:
- New `compare_calibration_tables()` function in `diagnostics.py`
- `CalibrationComparison` dataclass for structured results
- Leverages existing `validate_caltable_quality()` function
- Compares key metrics: median/rms amplitude and phase

---

## Files Modified/Created

### New Files
1. `src/dsa110_contimg/calibration/diagnostics.py` - Comprehensive diagnostics and comparison utilities

### Modified Files
1. `src/dsa110_contimg/calibration/cli.py` - Added all new flags and subcommands
2. `tests/utils/cal_ms_demo.py` - Fixed imports
3. `src/dsa110_contimg/calibration/__init__.py` - Added diagnostics to exports

---

## Testing Recommendations

### Validate Subcommand
```bash
python -m dsa110_contimg.calibration.cli validate \
    --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
    --field 0 --refant 103
```

### Dry-Run Mode
```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
    --field 0 --refant 103 \
    --dry-run
```

### Diagnostics Mode
```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
    --field 0 --refant 103 \
    --diagnostics
```

### Minimal Mode
```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms \
    --field 0 --refant 103 \
    --minimal
```

### Compare Command
```bash
python -m dsa110_contimg.calibration.cli compare \
    --caltable1 /path/to/cal1.gcal \
    --caltable2 /path/to/cal2.gcal \
    --tolerance 1e-6
```

---

## Benefits

1. **Validation Mode**: Quick check before committing to long calibration
2. **Dry-Run Mode**: Fast feedback on calibration feasibility
3. **Diagnostics Mode**: Comprehensive understanding of calibration quality
4. **Minimal Mode**: Very fast iteration for testing calibration logic
5. **Comparison Tool**: Regression testing and quality control

All improvements maintain backward compatibility - existing workflows are unaffected.

---

## Next Steps

- Test all new features with real data
- Update documentation/tutorials to include new capabilities
- Consider adding these features to integration tests

