# Current Default Calibration Procedure

**Last Updated:** Based on code review of `cli_calibrate.py` and `defaults.py`

## Overview

The DSA-110 continuum imaging pipeline uses a **standard calibration workflow**
that performs bandpass (BP) and gain (G) calibration by default. Delay (K)
calibration is **optional** and skipped by default for connected-element arrays.

## Default Calibration Steps

### Standard Workflow (Default)

1. **MS Validation** ✓
2. **Pre-Calibration Flagging** ✓
3. **Model Data Population** ✓ (using pyradiosky)
4. **Bandpass Calibration (BP)** ✓ (enabled by default)
5. **Gain Calibration (G)** ✓ (enabled by default)
6. **Calibration Table Validation** ✓

**K-Calibration (Delay):** ❌ **Skipped by default**

## Detailed Procedure

### Step 1: MS Validation

**Purpose:** Ensure MS is ready for calibration

**Checks:**

- MS file exists and is readable
- Field(s) exist and are valid
- Reference antenna has unflagged data
- Sufficient unflagged data (>10% required, >30% recommended)

**Auto-Features:**

- Reference antenna auto-selection (outrigger-priority chain)
- Field auto-selection (with `--auto-fields`)

### Step 2: Pre-Calibration Flagging

**Default Mode:** `--flagging-mode zeros` (flag zero-value data only)

**Process:**

1. Reset all flags
2. Flag zero-value data (correlator failures)
3. Optionally flag RFI (`--flagging-mode rfi`)

**Validation:**

- Verifies ≥10% unflagged data remains
- Warns if <30% unflagged

### Step 3: Model Data Population

**Default Source:** `--model-source catalog` (VLA calibrator catalog)

**Method:** **pyradiosky** (now default)

**Process:**

1. **With `--auto-fields`:**
   - Searches VLA catalog for calibrator in MS field of view
   - Selects fields around peak signal
   - Rephases MS to calibrator position (unless `--skip-rephase`)
   - Creates pyradiosky SkyModel from catalog
   - Converts to CASA componentlist
   - Populates MODEL_DATA via CASA `ft()`

2. **With explicit `--field`:**
   - Uses provided field(s)
   - Creates point source model from catalog or NVSS
   - Populates MODEL_DATA

**Sky Model Creation:**

- **Single calibrator:** `make_point_cl()` → pyradiosky → componentlist
- **NVSS sources:** `make_nvss_component_cl()` → pyradiosky → componentlist

**Key Change:** All sky model creation now uses **pyradiosky internally** for
better management.

### Step 4: Bandpass Calibration (BP)

**Status:** ✅ **Enabled by default**

**Purpose:** Correct frequency-dependent instrumental response per antenna

**Default Parameters:**

- `--bp-minsnr 3.0` (minimum SNR threshold)
- `--bp-solint inf` (entire scan)
- `combine='scan'` (combine across scans)
- No smoothing by default

**Optional Enhancements:**

- `--prebp-phase`: Pre-bandpass phase-only solve (improves SNR)
- `--bp-combine-field`: Combine across fields (for weak calibrators)
- `--bp-smooth`: Smooth bandpass solutions

**Field Selection:**

- **With `--auto-fields`:** Automatically selects fields around peak signal
- **With `--field`:** Uses specified field(s)
- **With `--bp-combine-field`:** Combines multiple fields for better SNR

### Step 5: Gain Calibration (G)

**Status:** ✅ **Enabled by default**

**Purpose:** Correct time-variable amplitude and phase per antenna

**Default Parameters:**

- `--gain-minsnr 3.0` (minimum SNR threshold)
- `--gain-solint inf` (entire scan, per-integration for production)
- `--gain-calmode ap` (amplitude+phase, phase-only for fast mode)
- `combine='scan'` (combine across scans)

**Calibration Modes:**

- `ap` (default): Amplitude + phase
- `p`: Phase-only (faster, less accurate)

**Solution Intervals:**

- `inf` (default): Entire scan
- `int`: Per-integration (higher quality, slower)
- `30s`, `60s`, etc.: Time-based intervals

### Step 6: Delay Calibration (K)

**Status:** ❌ **Skipped by default**

**Rationale:**

- DSA-110 is a connected-element array (2.6 km max baseline)
- Following VLA/ALMA practice: residual delays (<0.5 ns) are absorbed into
  complex gain calibration
- K-calibration is primarily needed for VLBI arrays (thousands of km baselines)

**To Enable:**

- Use `--do-k` flag

**When to Use:**

- VLBI observations
- If residual delays are significant
- For high-precision applications

## Default Configuration

### Calibration Defaults (from `utils/defaults.py`)

```python
# Bandpass
CAL_BP_MINSNR = 3.0
CAL_BP_SOLINT = "inf"  # Entire scan
CAL_BP_SMOOTH_TYPE = "none"  # No smoothing

# Gain
CAL_GAIN_MINSNR = 3.0
CAL_GAIN_SOLINT = "inf"  # Entire scan (per-integration for production)
CAL_GAIN_CALMODE = "ap"  # Amplitude+phase

# K-calibration
CAL_K_MINSNR = 5.0
CAL_K_COMBINE_SPW = False

# Flagging
CAL_FLAGGING_MODE = "zeros"  # Zero-value flagging only
CAL_FLAG_AUTOCORR = True  # Flag autocorrelations

# Model
CAL_MODEL_SOURCE = "catalog"  # VLA catalog
```

## Quality Presets

### Standard (Default)

**Recommended for all science observations**

- Full MS (no subsetting)
- Amplitude+phase gains
- No aggressive cuts
- Production quality

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103 \
    --preset standard
```

### High Precision

**Enhanced quality for critical observations**

- Full MS
- Per-integration solutions
- Higher SNR thresholds
- Maximum quality (slower)

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103 \
    --preset high_precision
```

### Development

**⚠️ NON-SCIENCE QUALITY - For code testing only**

- Aggressive subsetting (30s timebin, 4x chanbin)
- Phase-only gains
- UV range cuts
- Reduced quality (faster)

**WARNING:** Development tier produces `NON_SCIENCE_DEVELOPMENT` prefixed tables
that **cannot** be applied to production data.

## Key Features

### Auto-Field Selection

**Recommended for production use**

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --auto-fields \
    --refant 103
```

**Benefits:**

- Automatically finds calibrator in MS
- Selects optimal fields around peak signal
- Rephases MS to calibrator position
- Uses VLA catalog for flux/position

### Field Combination

**For weak calibrators (<5 Jy)**

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --auto-fields \
    --bp-combine-field \
    --refant 103
```

**Benefits:**

- Combines data from multiple fields
- Increases SNR for weak sources
- Better calibration solutions

### Fast Mode

**For quick testing (reduced quality)**

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103 \
    --fast \
    --timebin 30s \
    --chanbin 4
```

**Trade-offs:**

- 3-5x faster
- Lower time/frequency resolution
- May miss fast variations

## Recent Changes

### pyradiosky Integration (Latest)

**All sky model creation now uses pyradiosky internally:**

- `make_point_cl()` → pyradiosky → componentlist
- `make_nvss_component_cl()` → pyradiosky → componentlist

**Benefits:**

- Better sky model management
- Support for multiple catalog formats
- Advanced spectral modeling
- Backward compatible (same API)

**No code changes required** - existing code works as-is.

## Example Commands

### Basic Calibration

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /data/ms/0834_2025-10-30.ms \
    --field 0 \
    --refant 103
```

### Production Calibration (Recommended)

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /data/ms/0834_2025-10-30.ms \
    --auto-fields \
    --refant 103 \
    --preset standard
```

### High Precision Calibration

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /data/ms/0834_2025-10-30.ms \
    --auto-fields \
    --refant 103 \
    --preset high_precision
```

### With RFI Flagging

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /data/ms/0834_2025-10-30.ms \
    --auto-fields \
    --refant 103 \
    --flagging-mode rfi
```

### With K-Calibration

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /data/ms/0834_2025-10-30.ms \
    --auto-fields \
    --refant 103 \
    --do-k
```

## Summary

**Default Calibration Procedure:**

1. ✅ **MS Validation** - Comprehensive checks
2. ✅ **Pre-Calibration Flagging** - Zero-value data (default)
3. ✅ **Model Data Population** - pyradiosky (default) → componentlist → `ft()`
4. ✅ **Bandpass Calibration** - Enabled by default
5. ✅ **Gain Calibration** - Enabled by default
6. ❌ **Delay Calibration** - Skipped by default (use `--do-k` to enable)

**Key Defaults:**

- Bandpass: SNR ≥ 3.0, entire scan
- Gain: SNR ≥ 3.0, entire scan, amplitude+phase
- Flagging: Zero-value data only
- Model: VLA catalog (via pyradiosky)

**Recommended for Production:**

- Use `--auto-fields` for automatic field selection
- Use `--preset standard` for science observations
- Use `--bp-combine-field` for weak calibrators

## References

- [Detailed Calibration Procedure](../calibration-overview.md)
- [pyradiosky Guide](../calibration-overview.md)
- Calibration Defaults: `../../src/dsa110_contimg/utils/defaults.py` (external
  file)
