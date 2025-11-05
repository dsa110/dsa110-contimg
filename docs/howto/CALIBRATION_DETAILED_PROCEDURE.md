# Detailed Calibration Procedure

**Purpose:** This document provides a comprehensive, step-by-step explanation of the calibration procedure for DSA-110 continuum imaging pipeline.

**Location:** `docs/howto/CALIBRATION_DETAILED_PROCEDURE.md`

---

## Overview

The calibration procedure corrects for instrumental and atmospheric effects that distort radio interferometric data. The pipeline performs **bandpass (BP)** and **gain (G)** calibration by default, with optional **delay (K)** calibration available.

**Calibration Order:** K → BP → G (if K is enabled)

**Default Behavior:** K-calibration is **skipped by default** for DSA-110 (connected-element array, 2.6 km max baseline), following VLA/ALMA practice.

---

## Pre-Calibration Steps

### Step 1: Pre-Calibration Flagging

**Purpose:** Remove bad data (zeros, RFI) before calibration to ensure solution integrity.

**Process:**

1. **Reset Flags** (`reset_flags`)
   - Clears any existing flags in the MS
   - Provides a clean slate for flagging operations

2. **Zero-Value Flagging** (`flag_zeros`)
   - Flags completely zero data channels (correlator failures)
   - Uses CASA `flagdata` with `mode="clip"` and `clipzeros=True`
   - **Required** - zeros would corrupt calibration solutions

3. **RFI Flagging** (`flag_rfi`, optional)
   - Two-stage statistical RFI detection:
     - **Stage 1: tfcrop** - Flags outliers in time/frequency space
       - `timecutoff=4.0`, `freqcutoff=4.0`
       - Fits polynomial/line models to detect deviations
     - **Stage 2: rflag** - Flags outliers in residual space
       - `timedevscale=4.0`, `freqdevscale=4.0`
   - **Recommended for calibrators** - ensures clean solutions

**Flagging Modes:**
- `--flagging-mode zeros` (default): Only zeros flagging
- `--flagging-mode rfi`: Zeros + RFI flagging
- `--flagging-mode none`: Skip flagging (not recommended)

**Validation:**
- After flagging, pipeline verifies ≥10% unflagged data remains
- Warns if <30% unflagged (may affect solution quality)

**Example:**
```bash
# Flagging is automatic, but can be controlled:
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103 \
    --flagging-mode rfi  # Use RFI flagging
```

### Step 2: Fast Mode Subset Creation (Optional)

**Purpose:** Speed up calibration by creating a time/channel-binned subset MS.

**When Enabled:** `--fast` flag with `--timebin` and `--chanbin` parameters

**Process:**
1. Creates a new MS with binned data:
   - Time averaging: `--timebin 30s` (average over 30 seconds)
   - Channel binning: `--chanbin 4` (average 4 channels together)
2. Uses subset MS for all calibration solves
3. Original MS remains unchanged
4. Subset can be cleaned up with `--cleanup-subset`

**Trade-offs:**
- ✓ **Faster**: 3-5x speedup for large MS files
- ✓ **Lower memory**: Reduced data volume
- ⚠️ **Lower resolution**: Solutions have coarser time/channel resolution
- ⚠️ **May miss fast variations**: Time-variable effects may be averaged out

**Example:**
```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103 \
    --fast \
    --timebin 30s \
    --chanbin 4
```

### Step 3: Model Data Population

**Purpose:** Populate `MODEL_DATA` column with expected visibility predictions from sky model.

**CRITICAL:** All calibration steps (K, BP, G) **require** `MODEL_DATA` to be populated. Calibration compares observed data (`DATA`) to model predictions (`MODEL_DATA`) to solve for corrections.

**Population Methods:**

1. **Catalog Model** (`--model-source catalog`, default)
   - Uses VLA calibrator catalog to find calibrator flux
   - Creates point source model at calibrator position
   - Uses Perley-Butler 2017 flux scale
   - **Recommended for standard calibrators** (e.g., 0834+555)

2. **NVSS Catalog** (`--model-source nvss`)
   - Uses NVSS catalog to find sources in field
   - Creates point source model for all sources ≥10 mJy
   - **Useful for target fields** with multiple sources

3. **Manual Flux** (`--cal-flux-jy`)
   - Specify calibrator flux manually
   - Creates point source model with specified flux
   - **Useful for non-standard calibrators**

**Validation:**
- Pipeline verifies `MODEL_DATA` exists and is populated (not all zeros)
- Raises error if `MODEL_DATA` is missing or unpopulated

**Technical Details:**
- Model written via CASA `ft()` (Fourier transform) or `setjy()` (standard calibrators)
- Model stored in `MODEL_DATA` column as complex visibilities

**Example:**
```bash
# Use catalog model (automatic for calibrators)
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103 \
    --model-source catalog

# Use NVSS catalog for target fields
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103 \
    --model-source nvss \
    --nvss-min-mjy 10.0
```

---

## Calibration Solve Steps

### Step 1: Delay Calibration (K) - **Optional**

**Status:** **Skipped by default** for DSA-110

**Purpose:** Corrects frequency-independent delays per antenna (clock offsets, cable delays).

**Rationale for Skipping:**
- DSA-110 is a connected-element array (2.6 km max baseline)
- Following VLA/ALMA practice: residual delays (<0.5 ns) are absorbed into complex gain calibration
- K-calibration is primarily needed for VLBI arrays (thousands of km baselines, independent atomic clocks)

**When to Enable:**
- Use `--do-k` flag to explicitly enable if needed
- Typically only required for VLBI observations or explicit delay measurements

**Process (if enabled):**

1. **Slow Solve** (`solint='inf'`)
   - Solves for delays over entire scan
   - Uses entire frequency range for high SNR
   - **Duration:** ~15-30 minutes

2. **Fast Solve** (`solint='60s'`, optional)
   - Solves for time-variable delays
   - Uses shorter time intervals
   - **Duration:** ~2-3 minutes
   - Can be skipped with `--k-fast-only`

**Technical Details:**
- Uses CASA `gaincal` with `gaintype='K'`
- Combines across scans by default (`combine='scan'`)
- Can combine across SPWs with `--combine-spw`
- Minimum SNR threshold: `--bp-minsnr` (default: 5.0)

**Output:**
- Calibration table: `<ms_prefix>_kcal`
- Format: CASA table directory (not a file)

**Example:**
```bash
# Enable K-calibration
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103 \
    --do-k
```

---

### Step 2: Bandpass Calibration (BP) - **Standard**

**Status:** **Enabled by default**

**Purpose:** Corrects frequency-dependent amplitude and phase variations across the observing band.

**Why Needed:**
- Receivers have frequency-dependent response
- Bandpass shape varies per antenna
- Essential for accurate flux measurements

**Process:**

1. **Pre-Bandpass Phase-Only Solve** (optional, `--prebp-phase`)
   - Corrects phase drifts before bandpass solve
   - Improves SNR for bandpass solutions
   - **Recommended for marginal SNR cases**

2. **Bandpass Solve**
   - Uses CASA `bandpass` task with `bandtype='B'`
   - Per-channel solution (`solint='inf'`)
   - Combines across scans by default (`combine='scan'`)
   - Optionally combines across fields (`--bp-combine-field`)
   - Optionally combines across SPWs (`--combine-spw`)

**Parameters:**

- **Field Selection:**
  - Single field: `--field 0`
  - Field range: `--field 0~15` (combines with `--bp-combine-field`)
  - Auto-select: `--auto-fields` (finds calibrator fields automatically)

- **UV Range Cuts:**
  - Default: No cut (processes all baselines)
  - Speed up: `--uvrange '>1klambda'` (removes short baselines)
  - **Warning:** Too aggressive cuts may reduce SNR

- **SNR Threshold:**
  - `--bp-minsnr 3.0` (default: 3.0)
  - Solutions below threshold are flagged
  - Lower threshold (3.0) for marginal SNR cases

- **Smoothing** (optional):
  - `--bp-smooth-type hanning|boxcar|gaussian`
  - `--bp-smooth-window <channels>`
  - Smooths bandpass table after solve

**Technical Details:**
- **PRECONDITION:** `MODEL_DATA` must be populated
- Uses `MODEL_DATA` as source model (`smodel`)
- Reference antenna: `--refant` (must have good SNR)
- Solution normalization: `solnorm=True` (normalizes solutions)

**Validation:**
- Verifies table exists and has solutions
- Checks reference antenna has solutions
- Validates table compatibility with MS

**Output:**
- Calibration table: `<ms_prefix>_bpcal`
- Format: CASA table directory

**Example:**
```bash
# Standard bandpass calibration
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103 \
    --auto-fields

# Bandpass with field combination (improves SNR)
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0~15 \
    --refant 103 \
    --bp-combine-field

# Bandpass with pre-phase correction (improves SNR)
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103 \
    --prebp-phase
```

---

### Step 3: Gain Calibration (G) - **Standard**

**Status:** **Enabled by default**

**Purpose:** Corrects time-dependent phase and amplitude variations (atmospheric effects, instrumental drifts).

**Why Needed:**
- Atmospheric phase varies on timescales of seconds to minutes
- Instrumental gains drift over time
- Essential for phase coherence and accurate imaging

**Process:**

1. **Phase-Only Gain Solve** (`calmode='p'`)
   - Solves for phase-only gains after bandpass
   - Solution interval: `--gain-solint` (default: `'inf'`)
   - **Always performed** (required for bandpass-calibrated data)

2. **Short-Timescale Phase-Only Solve** (optional, `--gain-solint 60s`)
   - Solves for rapid phase variations
   - Uses shorter solution intervals (e.g., `'60s'`, `'30s'`, `'int'`)
   - **Recommended for long observations** or high phase noise

**Parameters:**

- **Solution Interval:**
  - `--gain-solint inf` (default): Entire scan
  - `--gain-solint 60s`: 60-second intervals
  - `--gain-solint 30s`: 30-second intervals
  - `--gain-solint int`: Per integration

- **Calibration Mode:**
  - `--gain-calmode p` (default): Phase-only
  - `--gain-calmode ap`: Amplitude + phase
  - `--gain-calmode a`: Amplitude-only

- **Field Selection:**
  - Same as bandpass: `--field 0` or `--field 0~15`
  - Optionally combines across fields: `--bp-combine-field`

- **UV Range Cuts:**
  - Same as bandpass: `--uvrange '>1klambda'` (optional)

- **SNR Threshold:**
  - `--gain-minsnr 3.0` (default: 3.0)
  - Solutions below threshold are flagged

**Technical Details:**
- **PRECONDITION:** `MODEL_DATA` must be populated
- **PRECONDITION:** Bandpass tables must exist and be validated
- Applies bandpass tables during gain solve (`gaintable=bptables`)
- Uses CASA `gaincal` with `gaintype='G'`
- Combines across scans by default
- Optionally combines across fields (`--bp-combine-field`)

**Fast Mode:**
- `--fast` flag enables phase-only gains automatically
- Phase-only (`calmode='p'`) is faster than amplitude+phase

**Output:**
- Calibration tables:
  - `<ms_prefix>_gpcal` (phase-only, `solint='inf'`)
  - `<ms_prefix>_2gcal` (phase-only, `solint='60s'`, if `--gain-solint` specified)
- Format: CASA table directories

**Validation:**
- Verifies tables exist and have solutions
- Checks reference antenna has solutions
- Validates table compatibility with MS

**Example:**
```bash
# Standard gain calibration (phase-only)
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103 \
    --auto-fields

# Gain calibration with short-timescale solutions
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --gain-solint 60s

# Gain calibration with amplitude+phase
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --gain-calmode ap
```

---

## Post-Calibration Steps

### Step 1: Calibration Table Validation

**Purpose:** Verify calibration tables are valid and compatible with MS.

**Process:**
- Checks tables exist and are readable
- Verifies tables have solutions (non-empty)
- Validates reference antenna has solutions
- Checks table compatibility with MS (frequency ranges, time ranges)

**QA Validation:**
- Runs `check_calibration_quality()` after each solve
- Checks solution quality metrics
- Alerts on issues (low SNR, flagged solutions, etc.)

### Step 2: Calibration Table Registration

**Purpose:** Register calibration tables in database for later application to target fields.

**Process:**
- Tables registered in `cal_registry.sqlite3`
- Validity windows stored (MJD ranges)
- Apply order tracked (K → BP → G)

**Benefits:**
- Tracks which tables are valid for which time periods
- Enables automatic table selection for target fields
- Prevents using outdated calibration tables

---

## Complete Calibration Workflow Example

### Standard Calibration (Recommended)

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/dsa110-contimg/ms/2025-10-30T13:34:54.ms \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --model-source catalog
```

**What Happens:**
1. ✓ Flagging: Reset flags → Flag zeros → (Optional RFI)
2. ✓ Model Population: Populate `MODEL_DATA` from VLA catalog
3. ✗ K-calibration: Skipped (default)
4. ✓ Bandpass: Solve frequency-dependent gains
5. ✓ Gain: Solve time-dependent phase variations
6. ✓ Validation: Verify tables and register in database

**Output Tables:**
- `<ms_prefix>_bpcal` (bandpass)
- `<ms_prefix>_gpcal` (phase-only gains)

### Fast Calibration (Quick 5-Minute Image)

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/dsa110-contimg/ms/2025-10-30T13:34:54.ms \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --fast \
    --timebin 30s \
    --chanbin 4 \
    --uvrange '>1klambda'
```

**What Happens:**
1. ✓ Create subset MS (time/channel binned)
2. ✓ Flagging: Reset flags → Flag zeros
3. ✓ Model Population: Populate `MODEL_DATA` from catalog
4. ✓ Bandpass: Solve on subset MS (faster)
5. ✓ Gain: Solve phase-only gains on subset MS (faster)
6. ✓ Validation: Verify tables

**Trade-offs:**
- ✓ Faster: 3-5x speedup
- ⚠️ Lower resolution: Solutions averaged over bins

### Full Calibration (K + BP + G)

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/dsa110-contimg/ms/2025-10-30T13:34:54.ms \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --do-k \
    --gain-solint 60s
```

**What Happens:**
1. ✓ Flagging: Reset flags → Flag zeros → RFI
2. ✓ Model Population: Populate `MODEL_DATA` from catalog
3. ✓ K-calibration: Solve delays (slow + fast)
4. ✓ Bandpass: Solve frequency-dependent gains (uses K)
5. ✓ Gain: Solve phase-only gains (uses K + BP)
6. ✓ Validation: Verify all tables

**Output Tables:**
- `<ms_prefix>_kcal` (delay)
- `<ms_prefix>_bpcal` (bandpass)
- `<ms_prefix>_gpcal` (phase-only gains, `solint='inf'`)
- `<ms_prefix>_2gcal` (phase-only gains, `solint='60s'`)

---

## Key Parameters Summary

### Required Parameters

- `--ms`: Path to Measurement Set
- `--field`: Field selection (e.g., `0`, `0~15`)
- `--refant`: Reference antenna ID (e.g., `103`)

### Optional Parameters

**Flagging:**
- `--flagging-mode zeros|rfi|none` (default: `zeros`)
- `--no-flagging`: Skip flagging (not recommended)

**Fast Mode:**
- `--fast`: Enable fast mode
- `--timebin <interval>`: Time averaging (e.g., `30s`)
- `--chanbin <factor>`: Channel binning (e.g., `4`)

**Model Population:**
- `--model-source catalog|nvss` (default: `catalog`)
- `--cal-catalog <path>`: Calibrator catalog path
- `--cal-flux-jy <flux>`: Manual calibrator flux

**Bandpass:**
- `--bp-combine-field`: Combine across fields
- `--bp-minsnr <value>`: Minimum SNR (default: 3.0)
- `--uvrange <cut>`: UV range selection (e.g., `>1klambda`)
- `--prebp-phase`: Pre-bandpass phase correction

**Gain:**
- `--gain-solint <interval>`: Solution interval (default: `inf`)
- `--gain-calmode p|ap|a`: Calibration mode (default: `p`)
- `--gain-minsnr <value>`: Minimum SNR (default: 3.0)

**K-Calibration:**
- `--do-k`: Enable K-calibration (disabled by default)
- `--combine-spw`: Combine across SPWs
- `--k-fast-only`: Skip slow solve, only fast solve

---

## Troubleshooting

### Low SNR Solutions

**Symptoms:** Many solutions flagged, warnings about low SNR

**Solutions:**
- Use `--bp-combine-field` to combine across fields (improves SNR)
- Reduce UV range cut: `--uvrange ''` (no cut)
- Lower SNR threshold: `--bp-minsnr 3.0` (default)
- Use pre-bandpass phase: `--prebp-phase`
- Check reference antenna: `--auto-refant` or `--refant-ranking`

### Missing MODEL_DATA

**Symptoms:** Error: "MODEL_DATA column does not exist" or "MODEL_DATA is all zeros"

**Solutions:**
- Ensure `--model-source catalog` or `--model-source nvss` is specified
- Check calibrator is in catalog: `--cal-catalog <path>`
- Verify calibrator coordinates: `--cal-ra-deg`, `--cal-dec-deg`
- Manual flux: `--cal-flux-jy <flux>`

### Insufficient Unflagged Data

**Symptoms:** Warning: "Only X% data remains unflagged"

**Solutions:**
- Use less aggressive flagging: `--flagging-mode zeros` (skip RFI)
- Check data quality: `python -m dsa110_contimg.qa.ms_quality <ms>`
- Adjust flagging parameters: `--no-flagging` (not recommended)

### Calibration Tables Not Found

**Symptoms:** Error: "Calibration table does not exist"

**Solutions:**
- Verify MS path is correct
- Check calibration completed successfully (check logs)
- Verify table names match expected pattern: `<ms_prefix>_bpcal`, `<ms_prefix>_gpcal`

---

## References

- **Calibration Reference**: `docs/reference/calibration.md`
- **Calibration CLI**: `src/dsa110_contimg/calibration/cli.py`
- **Calibration Functions**: `src/dsa110_contimg/calibration/calibration.py`
- **Flagging Module**: `src/dsa110_contimg/calibration/flagging.py`
- **Model Population**: `src/dsa110_contimg/calibration/model.py`
- **Best Practices Review**: `docs/reports/CALIBRATION_REVIEW_PERPLEXITY.md`

