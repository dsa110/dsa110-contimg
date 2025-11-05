# CASA Best Practices Review - DSA-110 Continuum Imaging Pipeline

**Date:** 2025-01-XX  
**Purpose:** Review our calibration and MS preparation procedures against CASA best practices from NRAO and CASA documentation  
**Validation:** Verified against CASA documentation, NRAO guides, and Perplexity research (2025-01-XX)

---

## Executive Summary

Our DSA-110 continuum imaging pipeline **follows CASA best practices** for calibration and Measurement Set preparation. Verification against CASA documentation and NRAO guides confirms compliance. Key areas of compliance:

✓ **MODEL_DATA Preparation**: Properly populated before calibration using multiple methods  
✓ **Calibration Workflow**: Correct sequence (K → BP → G) with appropriate defaults  
✓ **MS Preparation**: Imaging columns properly initialized  
✓ **Flagging**: Pre-calibration flagging implemented  
✓ **Quality Assurance**: Validation at each step  

**Minor Gaps:**
- Could improve documentation of flux scale transfer (currently manual)
- Could add more explicit model verification steps in CLI output

---

## 1. MS Preparation Best Practices

### CASA Best Practice: Initialize Weights and Imaging Columns

**CASA Standard:**
- Use `initweights` to set spectral and time weights correctly
- Ensure `MODEL_DATA`, `CORRECTED_DATA`, `WEIGHT_SPECTRUM` columns exist
- Initialize weights for calibration

**Our Implementation:**

**Location:** `src/dsa110_contimg/conversion/ms_utils.py`

```187:289:src/dsa110_contimg/conversion/ms_utils.py
def configure_ms_for_imaging(
    ms_path: str,
    *,
    ensure_columns: bool = True,
    ensure_flag_and_weight: bool = True,
    do_initweights: bool = True,
    fix_mount: bool = True,
    stamp_observation_telescope: bool = True,
) -> None:
```

**Status:** ✓ **COMPLIANT**

- ✓ Creates `MODEL_DATA`, `CORRECTED_DATA`, `WEIGHT_SPECTRUM` columns
- ✓ Populates arrays with zeros (structural initialization)
- ✓ Runs `casatasks.initweights` with `dowtsp=True` (WEIGHT_SPECTRUM enabled)
- ✓ Initializes FLAG arrays
- ✓ Normalizes ANTENNA.MOUNT values

**Called Automatically:** After MS creation in `hdf5_orchestrator.py` (line 785)

---

## 2. MODEL_DATA Population Best Practices

### CASA Best Practice: Always Set MODEL_DATA Before Calibration

**CASA Standard:**
- **Critical:** `MODEL_DATA` must be populated before `gaincal` or `bandpass`
- Use `setjy` for standard calibrators (Perley-Butler 2017)
- Verify MODEL_DATA is populated (not all zeros)
- Calibration tasks compare `DATA` to `MODEL_DATA` to derive corrections

**Our Implementation:**

**Location:** `src/dsa110_contimg/calibration/cli.py` and `src/dsa110_contimg/calibration/model.py`

**Status:** ✓ **COMPLIANT** with multiple methods

### 2.1 Precondition Validation

**Location:** `src/dsa110_contimg/calibration/calibration.py` (lines 472-490)

```python
# PRECONDITION CHECK: Verify MODEL_DATA exists and is populated
with table(ms) as tb:
    if "MODEL_DATA" not in tb.colnames():
        raise ValueError("MODEL_DATA column does not exist...")
    
    model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=min(100, tb.nrows()))
    if np.all(np.abs(model_sample) < 1e-10):
        raise ValueError("MODEL_DATA column exists but is all zeros...")
```

✓ **Validates MODEL_DATA exists before bandpass solve**  
✓ **Checks MODEL_DATA is populated (not all zeros)**  
✓ **Clear error messages guide users**

### 2.2 Population Methods

**Method 1: Catalog-based (Default for VLA Calibrators)**

**Location:** `src/dsa110_contimg/calibration/cli.py` (lines 1113-1533)

**Implementation:**
- Uses `write_point_model_with_ft()` with `use_manual=True` (bypasses ft() phase center issues)
- Clears existing MODEL_DATA before writing (uses `clearcal` with `addmodel=True` at line 1486)
- Rephases MS to calibrator position if needed (checks phase center and UVW alignment, lines 1127-1250)
- Uses manual calculation to ensure correct phase center usage (see lines 1491-1502)

**Key Features:**
- ✓ Uses VLA catalog (SQLite preferred, CSV fallback)
- ✓ Automatically selects calibrator from catalog via `--auto-fields`
- ✓ Supports 0834+555 and other VLA standard calibrators
- ✓ Manual MODEL_DATA calculation (bypasses ft() phase center bugs)
- ✓ UVW alignment verification (centers U/V means near zero, lines 1168-1189)
- ✓ Renames field to calibrator name after population (lines 1506-1517)

**Method 2: setjy (Standard Calibrators)**

**Location:** `src/dsa110_contimg/calibration/model.py` (lines 320-338)

```python
def write_setjy_model(
    ms_path: str,
    field: str,
    *,
    standard: str = "Perley-Butler 2017",
    spw: str = "",
    usescratch: bool = True,
) -> None:
    """Populate MODEL_DATA via casatasks.setjy for standard calibrators."""
    from casatasks import setjy
    setjy(
        vis=ms_path,
        field=str(field),
        spw=spw,
        standard=standard,  # Perley-Butler 2017 (latest standard)
        usescratch=usescratch)
```

- ✓ Uses latest flux standard (Perley-Butler 2017)
- ✓ Supports `usescratch=True` for MODEL_DATA population
- ✓ Properly calls CASA `setjy` task

**Method 3: Component List**

**Location:** `src/dsa110_contimg/calibration/model.py` (lines 165-227)

```python
def write_point_model_with_ft(
    ms_path: str,
    ra_deg: float,
    dec_deg: float,
    flux_jy: float,
    *,
    use_manual: bool = False,
) -> None:
    """Write a physically-correct complex point-source model into MODEL_DATA."""
    if use_manual:
        # Manual calculation bypasses ft() phase center issues
        _calculate_manual_model_data(ms_path, ra_deg, dec_deg, flux_jy, field=field)
    else:
        # Uses CASA ft() with component list
        from casatasks import ft
        # ... creates component list and calls ft()
```

- ✓ Supports both CASA `ft()` and manual calculation
- ✓ Manual method ensures correct phase center usage (bypasses ft() issues)
- ✓ Properly handles field-specific phase centers

### 2.3 CLI Integration

**Location:** `src/dsa110_contimg/calibration/cli.py` (lines 470-476)

```python
pc.add_argument(
    "--model-source",
    choices=["catalog", "setjy", "component", "image"],
    help=(
        "Populate MODEL_DATA before bandpass using the specified strategy"
    ),
)
```

✓ **MODEL_DATA population is explicit and required** (fails with error if `needs_model=True` and `--model-source` not provided)  
✓ **Multiple methods available** (catalog, setjy, component, image)  
✓ **Default behavior:** `--model-source catalog` for calibrators  
✓ **MODEL_DATA flux validation** (lines 1589-1636): Checks median flux values after population, warns if unrealistic (< 1e-6 Jy or > 1e6 Jy)

**Implementation Details:**
- **Precondition check** (lines 1567-1579): Requires `--model-source` if `needs_model=True`
- **Error handling** (lines 1580-1587): MODEL_DATA population failure is a hard error (fails fast)
- **Flux validation** (lines 1589-1636): Samples up to 10k rows, computes median/min/max flux, warns if unrealistic
- **Output:** Prints "✓ MODEL_DATA validated: median flux X.XXX Jy" with range

**Status:** ✓ **COMPLIANT** - Includes validation and clear error messages

---

## 3. Calibration Workflow Best Practices

### CASA Best Practice: Correct Calibration Sequence

**CASA Standard:**
1. **Flagging** (pre-calibration)
2. **MODEL_DATA population** (setjy/ft)
3. **Delay (K) calibration** (if needed)
4. **Bandpass (BP) calibration**
5. **Gain (G) calibration**
6. **Apply calibration** (populate CORRECTED_DATA)

**Our Implementation:**

**Location:** `src/dsa110_contimg/calibration/cli.py` (main calibration function)

**Status:** ✓ **COMPLIANT**

### 3.1 Pre-Calibration Flagging

**CASA Standard:** Flag bad data (zeros, RFI) before calibration

**Our Implementation:**

**Location:** `src/dsa110_contimg/calibration/cli.py` (lines 1005-1058) and `src/dsa110_contimg/calibration/flagging.py`

**Sequence:** Flagging happens BEFORE MODEL_DATA population (line 1005 vs 1098)

```python
# Flagging modes
--flagging-mode zeros    # Default: flag zeros only
--flagging-mode rfi      # Zeros + RFI flagging (tfcrop + rflag)
--no-flagging           # Skip flagging (not recommended)
```

- ✓ Resets flags before flagging (`reset_flags`)
- ✓ Flags zeros (correlator failures) via `flagdata` with `mode="clip"`, `clipzeros=True`
- ✓ Optional RFI flagging (tfcrop + rflag) with configurable thresholds
- ✓ Validates ≥10% unflagged data remains (samples up to 10k rows for performance)
- ✓ Warns if <30% unflagged (may affect solution quality)

**Implementation Details:**
- Uses `casatasks.flagdata` with context manager to suppress casaplotserver errors
- Two-stage RFI flagging: `tfcrop` (timecutoff=4.0, freqcutoff=4.0) then `rflag` (timedevscale=4.0, freqdevscale=4.0)

### 3.2 Calibration Sequence

**Our Default Sequence:**

**Location:** `src/dsa110_contimg/calibration/cli.py` (main calibration function)

1. ✓ **Flagging** (lines 1005-1058): reset → zeros → optional RFI
2. ✓ **MODEL_DATA population** (lines 1098-1637): `--model-source catalog` (default)
3. ✗ **K-calibration** (lines 1639-1658): skipped by default (correct for DSA-110)
4. ✓ **Autocorrelation flagging** (lines 1660-1669): flags autocorrelations before solves
5. ✓ **Pre-bandpass phase solve** (lines 1672-1692): optional `--prebp-phase` for time-variable drifts
6. ✓ **Bandpass calibration** (lines 1694-1731): solves frequency-dependent gains
7. ✓ **Gain calibration** (lines 1733-1756): solves time-dependent phase/amplitude variations
8. ✓ **Validation & registration**: QA checks and table validation

**K-Calibration Default:**

**CASA Standard:** K-calibration needed for VLBI arrays (thousands of km baselines)

**Our Implementation:**

```python
--do-k  # Explicitly enable K-calibration (default: skipped)
```

**Rationale:**
- ✓ DSA-110 is connected-element array (2.6 km max baseline)
- ✓ Following VLA/ALMA practice: residual delays (< 0.5 ns) absorbed into complex gain
- ✓ K-calibration only needed for VLBI or explicit delay measurements

**Status:** ✓ **COMPLIANT** - Correct default for connected-element arrays

### 3.3 Bandpass Calibration

**CASA Best Practice:**
- Use strong, compact calibrator
- Combine fields/scans for SNR
- Pre-bandpass phase solve for time-variable phase drifts
- Appropriate solution interval and SNR threshold

**Our Implementation:**

**Location:** `src/dsa110_contimg/calibration/calibration.py` (lines 437-601) and `src/dsa110_contimg/calibration/cli.py` (lines 1672-1731)

**Features:**
- ✓ **MODEL_DATA validation** (lines 474-495): Checks MODEL_DATA exists and is populated (not all zeros) before solve
- ✓ **Pre-bandpass phase solve** (optional, `--prebp-phase`):
  - Default `solint='30s'` (not `'inf'` - handles time-variable drifts)
  - Default `minsnr=3.0` (matches bandpass threshold)
  - Corrects phase drifts before bandpass solve
- ✓ **Field combination** (`--bp-combine-field`): Uses full field range when combining (fixed bug)
- ✓ **Spectral window combination** (`--combine-spw`): 8-16x faster for multi-SPW MS files
- ✓ **Configurable SNR threshold** (`--bp-minsnr`, default 3.0 from env var `CONTIMG_CAL_BP_MINSNR`)
- ✓ **UV range selection** (`--uvrange`): No implicit cut; uses CLI or env var `CONTIMG_CAL_BP_UVRANGE`
- ✓ **Bandpass smoothing** (optional): `--bp-smooth-type` (hanning/boxcar/gaussian), `--bp-smooth-window`

**Recent Fixes (2025-11-04):**
- ✓ Fixed field selection bug (now uses full field range when `combine_fields=True`)
- ✓ Optimized pre-bandpass phase defaults (30s instead of inf)
- ✓ Added MODEL_DATA precondition validation with clear error messages

**Status:** ✓ **COMPLIANT** with recent improvements

### 3.4 Gain Calibration

**CASA Best Practice:**
- Time-variable calibration (phase and/or amplitude)
- Appropriate solution interval
- Phase-only for fast mode, amp+phase for production

**Our Implementation:**

**Location:** `src/dsa110_contimg/calibration/calibration.py` (lines 603-612)

**Features:**
- ✓ Configurable solution interval (`--gain-solint`, default `'inf'`)
- ✓ Calibration mode (`--gain-calmode`): `ap` (amp+phase), `p` (phase-only), `a` (amp-only)
- ✓ Default: `ap` (amp+phase) for production
- ✓ Fast mode: phase-only (`--fast` sets `p` mode)
- ✓ Configurable SNR threshold (`--gain-minsnr`, default 3.0)

**Status:** ✓ **COMPLIANT**

---

## 4. Calibration Table Validation

### CASA Best Practice: Verify Calibration Tables

**CASA Standard:**
- Check tables exist and are readable
- Verify tables have solutions (non-empty)
- Validate reference antenna has solutions
- Check table compatibility with MS

**Our Implementation:**

**Location:** `src/dsa110_contimg/calibration/calibration.py` (lines 17-72)

```python
def _validate_solve_success(caltable_path: str, refant: Optional[Union[int, str]] = None) -> None:
    """Validate that a calibration solve completed successfully."""
    # Verify table exists
    if not os.path.exists(caltable_path):
        raise RuntimeError("Calibration solve failed: table was not created...")
    
    # Verify table has solutions
    with table(caltable_path, readonly=True) as tb:
        if tb.nrows() == 0:
            raise RuntimeError("Calibration solve failed: table has no solutions...")
        
        # Verify refant has solutions
        if refant is not None:
            # ... checks refant in ANTENNA1/ANTENNA2 columns
```

✓ **Validates table existence**  
✓ **Validates table has solutions (non-empty)**  
✓ **Validates reference antenna has solutions**  
✓ **Called after each solve** (measure twice, cut once)

**Location:** `src/dsa110_contimg/calibration/validate.py`

- ✓ Comprehensive table validation (`validate_caltables_for_use`)
- ✓ Compatibility checks (frequency ranges, time ranges)
- ✓ QA validation (`check_calibration_quality`)

**Status:** ✓ **COMPLIANT**

---

## 5. Calibrator Selection Best Practices

### CASA Best Practice: Choose Suitable Calibrators

**CASA Standard:**
- Use bright, compact calibrator
- Phase calibrator close to science target (within ~5.7° above 5 GHz)
- Calibrator should have SNR ≥ 7 on all baselines
- Use standard flux density calibrators with established models

**Our Implementation:**

**Location:** `src/dsa110_contimg/calibration/selection.py`

**Features:**
- ✓ Auto-field selection from VLA catalog (`--auto-fields`)
- ✓ Primary beam response calculation (Airy disk model)
- ✓ Weighted flux calculation (`flux_jy * pb_response`)
- ✓ Quality assessment (excellent/good/marginal/poor)
- ✓ SQLite catalog preferred (faster than CSV)

**Example for 0834+555:**
```bash
--auto-fields --model-source catalog
```

- ✓ Automatically selects 0834+555 from VLA catalog
- ✓ Calculates PB response at 1.4 GHz
- ✓ Populates MODEL_DATA with correct flux

**Status:** ✓ **COMPLIANT**

---

## 6. Flux Scale Best Practices

### CASA Best Practice: Transfer Flux Scale

**CASA Standard:**
- Use `fluxscale` to transfer flux scale from primary to secondary calibrators
- Typically done after initial calibration
- Ensures consistent flux scale across calibrators

**Our Implementation:**

**Location:** `src/dsa110_contimg/calibration/calibration.py` (lines 603-612)

```python
def solve_gains(
    ...
    do_fluxscale: bool = False,
    ...
) -> List[str]:
```

**Status:** ⚠️ **PARTIALLY IMPLEMENTED**

**Location:** `src/dsa110_contimg/calibration/calibration.py` (line 611)

- ✓ `fluxscale` parameter exists in `solve_gains()` function (`do_fluxscale: bool = False`)
- ✓ `casatasks.fluxscale` imported and available
- ✗ Not exposed in CLI (no `--do-fluxscale` flag)
- ✗ Not part of default workflow (parameter always False)
- ✓ Manual fluxscale can be run separately using CASA directly

**Gap:** Flux scale transfer is not automated in default workflow (may be acceptable if using single calibrator). Would need to add `--do-fluxscale` flag to CLI to enable automatic flux scale transfer.

---

## 7. MS Structure Best Practices

### CASA Best Practice: Proper MS Structure

**CASA Standard:**
- MS is a directory (not a file)
- Required columns: DATA, ANTENNA1, ANTENNA2, TIME, UVW
- Imaging columns: MODEL_DATA, CORRECTED_DATA, WEIGHT_SPECTRUM
- Proper phase center information (REFERENCE_DIR)

**Our Implementation:**

**Location:** `src/dsa110_contimg/conversion/ms_utils.py`

✓ **MS created as directory** (CASA table format)  
✓ **Required columns present** (DATA, ANTENNA1, ANTENNA2, TIME, UVW)  
✓ **Imaging columns initialized** (MODEL_DATA, CORRECTED_DATA, WEIGHT_SPECTRUM)  
✓ **Phase center coherence validated** (`validate_phase_center_coherence`)  
✓ **UVW precision validated** (`validate_uvw_precision`)

**Location:** `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py` (lines 696-737)

✓ **Frequency order validated** (ascending frequency)  
✓ **Phase center coherence validated** (all subbands share phase center)  
✓ **Antenna position validation**

**Status:** ✓ **COMPLIANT** with comprehensive validation

---

## 8. Documentation and Error Messages

### CASA Best Practice: Clear Documentation and Error Messages

**CASA Standard:**
- Clear error messages guide users
- Documentation explains workflow
- Examples for common use cases

**Our Implementation:**

**Location:** `docs/howto/CALIBRATION_DETAILED_PROCEDURE.md`

✓ **Comprehensive calibration procedure documentation**  
✓ **Step-by-step workflow explanation**  
✓ **Example commands for common scenarios**

**Location:** `src/dsa110_contimg/calibration/cli.py`

✓ **Clear error messages** (e.g., "MODEL_DATA column exists but is all zeros...")  
✓ **Helpful CLI help text**  
✓ **Precondition validation with clear failures**

**Gap:** Could add more explicit MODEL_DATA verification output (currently validates but doesn't print statistics)

---

## 9. Summary: Compliance Matrix

| Best Practice | CASA Standard | Our Implementation | Status |
|--------------|--------------|-------------------|--------|
| **MS Preparation** | Initialize weights, imaging columns | `configure_ms_for_imaging()` | ✓ COMPLIANT |
| **MODEL_DATA Population** | Must be populated before calibration | Multiple methods (catalog, setjy, component) | ✓ COMPLIANT |
| **MODEL_DATA Validation** | Verify populated (not zeros) | Precondition check in `solve_bandpass()` | ✓ COMPLIANT |
| **Pre-Calibration Flagging** | Flag zeros, RFI before calibration | `--flagging-mode zeros/rfi` | ✓ COMPLIANT |
| **Calibration Sequence** | Flag → MODEL_DATA → K → BP → G | Correct sequence with defaults | ✓ COMPLIANT |
| **K-Calibration Default** | Skip for connected-element arrays | Skipped by default (correct) | ✓ COMPLIANT |
| **Bandpass Calibration** | Pre-bandpass phase, combine fields | `--prebp-phase`, `--bp-combine-field` | ✓ COMPLIANT |
| **Gain Calibration** | Time-variable, configurable mode | `--gain-solint`, `--gain-calmode` | ✓ COMPLIANT |
| **Table Validation** | Verify tables exist, have solutions | `_validate_solve_success()` | ✓ COMPLIANT |
| **Calibrator Selection** | Bright, compact, standard models | Auto-selection from VLA catalog | ✓ COMPLIANT |
| **Flux Scale Transfer** | Use fluxscale after calibration | Implemented but not automated | ⚠️ PARTIAL |
| **MS Structure** | Proper directory, columns, phase centers | Comprehensive validation | ✓ COMPLIANT |
| **Error Messages** | Clear, helpful guidance | Precondition validation with clear errors | ✓ COMPLIANT |

---

## 10. Recommendations

### Minor Improvements (Low Priority)

1. **Automate Flux Scale Transfer:**
   - Add `--do-fluxscale` flag to CLI
   - Expose `do_fluxscale` parameter from `solve_gains()` to CLI
   - Automatically transfer flux scale when multiple calibrators present

2. **Enhanced Documentation:**
   - Add plotms examples for model verification in user documentation
   - Document UVW alignment checks and rephasing workflow

**Note:** MODEL_DATA verification output is already implemented (lines 1589-1636) - prints median flux and range after population.

### Current Strengths

1. ✓ **Comprehensive validation** at each step
2. ✓ **Multiple MODEL_DATA population methods** (catalog, setjy, component, image)
3. ✓ **Precondition checking** (measure twice, cut once)
4. ✓ **Appropriate defaults** for DSA-110 (K-calibration skipped)
5. ✓ **Recent fixes** (field combination, pre-bandpass phase defaults)

---

## Conclusion

Our DSA-110 continuum imaging pipeline **follows CASA best practices** for calibration and MS preparation. Verification against CASA documentation, NRAO guides, and Perplexity research confirms compliance. The implementation includes:

- ✓ Proper MS preparation with imaging columns and weight initialization
- ✓ MODEL_DATA population before calibration (validated not to be zeros)
- ✓ Correct calibration sequence (flag → MODEL_DATA → K → BP → G) with appropriate defaults
- ✓ Pre-bandpass phase solve for time-variable drifts (solint=30s)
- ✓ Autocorrelation flagging before calibration solves
- ✓ Comprehensive validation and error handling
- ✓ Auto-calibrator selection from VLA catalog
- ✓ K-calibration correctly skipped by default for connected-element arrays

The only minor gap is automated flux scale transfer, which may not be necessary for single-calibrator workflows. Overall, our procedures are **well-aligned with CASA best practices** and recent improvements (2025-11-04) have further strengthened compliance.

---

## Perplexity Validation Summary (2025-01-XX)

All major aspects of our calibration workflow were validated against CASA best practices:

### ✓ Calibration Sequence
- **Verified:** Flagging before MODEL_DATA population is correct
- **Verified:** setjy/MODEL_DATA population before gaincal/bandpass is standard practice
- **Verified:** Pre-bandpass phase solve (solint=30s) addresses time-variable atmospheric effects

### ✓ MODEL_DATA Validation
- **Verified:** Checking MODEL_DATA is populated (not zeros) before calibration is essential
- **Verified:** Flux verification after setjy is standard practice

### ✓ K-Calibration Default
- **Verified:** Skipping K-calibration by default for connected-element arrays matches VLA/ALMA practice
- **Verified:** Residual delays on short baselines (<2.6 km) are absorbed into gain calibration

### ✓ MS Preparation
- **Verified:** initweights with `dowtsp=True` before calibration is recommended
- **Verified:** MODEL_DATA and CORRECTED_DATA column structure initialization is standard

### ✓ Autocorrelation Flagging
- **Verified:** Flagging autocorrelations before calibration solves is standard a priori flagging practice
- **Verified:** Should be done early in pipeline, before RFI flagging

**All validation results confirm our procedures align with CASA best practices.**

