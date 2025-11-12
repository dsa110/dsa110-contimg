# "Measure Twice, Cut Once" Risk Analysis

**Date:** 2025-11-02  
**Purpose:** Identify areas where we operate inefficiently by not establishing preconditions upfront  
**Verified:** Fact-checked via Perplexity research (2025-11-02)

## Philosophy

**"Measure twice, cut once"** means:
- Establish preconditions upfront
- Verify requirements before proceeding
- Fail fast with clear errors
- Prevent wasted time from proceeding with invalid conditions

## Evidence from Best Practices

**Perplexity research confirms:**
- ✅ **Calibration tables should be validated before use** (CASA best practices)[1][2]
- ✅ **K-table should be inspected before using in bandpass calibration** (calibration chain integrity)[3][4]
- ✅ **applycal should validate compatibility** (antenna/frequency matching)[5][6]
- ✅ **Calibration should be verified before imaging** (CORRECTED_DATA validation)[7][8]

**Note:** CASA does not enforce automated compatibility checks by default - this is user responsibility[5][6]. Our pipeline should implement these checks to prevent errors.

## Areas at Risk

### 1. ⚠️ Bandpass Calibration - Missing Precondition Checks

**Location:** `src/dsa110_contimg/calibration/calibration.py:solve_bandpass()`

**Current Behavior:**
- Uses `ktable` in `gaintable_list` if provided (line 277)
- Does NOT verify `ktable` exists or is valid before using it
- If `ktable` is invalid/missing, CASA will fail later during bandpass solve

**Risk:**
- Wasted time attempting bandpass solve with invalid K-table
- Unclear error messages when K-table doesn't exist
- No upfront verification that K-table is compatible with MS

**Fix Required:**
- Verify `ktable` exists and is valid before using it
- Check K-table compatibility (antennas, frequencies) with MS
- Raise clear error if precondition not met

**Evidence:** Perplexity confirms that "validation of the K-table before using it in subsequent gain calibration steps is a critical best practice to ensure the integrity of the calibration process"[3][4]. CASA tutorials recommend inspecting calibration tables with `plotcal` before using them downstream[2][3].

---

### 2. ⚠️ Gain Calibration - Missing Precondition Checks

**Location:** `src/dsa110_contimg/calibration/calibration.py:solve_gains()`

**Current Behavior:**
- Uses `ktable` and `bptables` in `gaintable` (line 363)
- Does NOT verify tables exist or are valid before using them
- Assumes BP tables were created successfully

**Risk:**
- Wasted time attempting gain solve with invalid/missing tables
- Silent failures if BP solve failed but we continue anyway
- No verification that tables are compatible with MS

**Fix Required:**
- Verify all required tables exist before using them
- Check table compatibility (antennas, frequencies, time ranges)
- Raise clear error if precondition not met

**Evidence:** Perplexity confirms that "calibration tables should not be used blindly; they require inspection and validation"[1][2]. Each calibration table should be validated before being used in subsequent steps[2][3].

---

### 3. ⚠️ Apply Calibration - Missing Compatibility Checks

**Location:** `src/dsa110_contimg/calibration/applycal.py:apply_to_target()`

**Current Behavior:**
- Accepts list of calibration tables
- Does NOT verify tables exist before calling CASA `applycal`
- Does NOT check compatibility (antennas, frequencies) with MS
- Some callers check existence (e.g., `apply_service.py`), but base function doesn't

**Risk:**
- CASA `applycal` fails with cryptic errors if tables incompatible
- Wasted time applying incompatible calibration
- No upfront verification

**Fix Required:**
- Verify all tables exist before proceeding
- Check compatibility (antennas, frequencies, time ranges)
- Raise clear error if precondition not met

**Note:** `apply_service.py` has some checks (lines 255-265), but they're not in the base function.

**Evidence:** Perplexity confirms that "calibration tables should be validated for consistency and compatibility before applying them with applycal"[5][6]. While CASA doesn't enforce automated checks by default, "manual validation of calibration table compatibility is a critical step"[5][6]. Antenna and frequency compatibility are especially important[5][6].

---

### 4. ⚠️ Imaging - Missing Calibration Verification

**Location:** `src/dsa110_contimg/imaging/cli.py:_detect_datacolumn()`

**Current Behavior:**
- Detects if CORRECTED_DATA exists and has non-zero values
- Falls back to DATA if CORRECTED_DATA is all zeros
- Does NOT verify that calibration was actually applied successfully

**Risk:**
- May image DATA when calibration failed silently
- No upfront check that calibration was applied before imaging
- Wasted time imaging uncalibrated data

**Fix Required:**
- Verify calibration was applied successfully before imaging
- Check that CORRECTED_DATA is populated and reasonable
- Raise clear error if precondition not met

**Evidence:** Perplexity confirms that "calibration should be verified before proceeding to imaging with tasks like tclean"[7][8]. "Validating the calibration—specifically, ensuring that the CORRECTED_DATA column in the measurement set is accurate and free of significant errors—is a critical step to produce reliable and high-fidelity images"[7][8].

---

### 5. ⚠️ Model Population - Missing MS Structure Verification

**Location:** `src/dsa110_contimg/calibration/model.py`

**Current Behavior:**
- Functions like `write_setjy_model()`, `write_point_model_with_ft()` call `_ensure_imaging_columns()`
- `_ensure_imaging_columns()` silently fails if columns already exist
- Does NOT verify MS structure is valid before populating MODEL_DATA

**Risk:**
- Attempting to populate MODEL_DATA on corrupted/invalid MS
- Silent failures if MS structure is wrong
- Wasted time on invalid MS

**Fix Required:**
- Verify MS structure is valid before populating MODEL_DATA
- Check that required columns exist and have correct shape
- Raise clear error if precondition not met

---

### 6. ⚠️ UVH5 Conversion - Missing File Validity Checks

**Location:** `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py`

**Current Behavior:**
- `find_subband_groups()` checks completeness (line 181: verifies all required subbands present)
- Does NOT verify files are readable/valid before starting conversion
- Conversion starts without checking file integrity

**Risk:**
- Wasted time converting corrupted/invalid files
- Conversion fails partway through reading files
- No upfront verification that files are readable/valid

**Fix Required:**
- Verify all files are readable before starting conversion
- Check file sizes/corruption before proceeding
- Raise clear error if precondition not met

---

### 7. ⚠️ Calibration Table Chain Validation

**Current Behavior:**
- BP calibration uses K-table
- G calibration uses K-table + BP-tables
- No verification that tables form a valid chain

**Risk:**
- Using incompatible calibration tables
- Wasted time on invalid calibration chain
- Unclear errors when chain is broken

**Fix Required:**
- Verify calibration table chain is valid before proceeding
- Check that tables are compatible with each other
- Raise clear error if precondition not met

---

## Summary Table

| Area | Risk Level | Impact | Fix Priority |
|------|-----------|--------|--------------|
| Bandpass calibration | High | Wasted time, unclear errors | High |
| Gain calibration | High | Wasted time, unclear errors | High |
| Apply calibration | Medium | Compatibility issues | Medium |
| Imaging | Medium | Imaging wrong data | Medium |
| Model population | Low | Silent failures | Low |
| UVH5 conversion | Medium | Incomplete conversions | Medium |
| Calibration chain | High | Invalid calibration | High |

## Recommended Fixes

### Priority 1: Calibration Preconditions

1. **Bandpass calibration:**
   - Verify K-table exists and is valid before using it
   - Check K-table compatibility with MS

2. **Gain calibration:**
   - Verify K-table and BP-tables exist and are valid
   - Check table compatibility with MS

3. **Apply calibration:**
   - Verify all tables exist and are compatible
   - Check antennas, frequencies, time ranges match

### Priority 2: Imaging Preconditions

4. **Imaging:**
   - Verify calibration was applied successfully
   - Check CORRECTED_DATA is populated and reasonable

### Priority 3: Other Preconditions

5. **Model population:**
   - Verify MS structure is valid
   - Check required columns exist and have correct shape

6. **UVH5 conversion:**
   - Verify all required subbands exist
   - Check file completeness before starting

## Implementation Strategy

For each area:
1. **Add precondition checks** at the start of functions
2. **Raise clear errors** if preconditions not met
3. **Document preconditions** in function docstrings
4. **Verify before proceeding** - fail fast, not after expensive operations

This ensures we follow "measure twice, cut once" throughout the pipeline.

---

## References

[1] Calibration - NRAO - National Radio Astronomy Observatory (2024-10-10)
https://science.nrao.edu/facilities/vla/docs/manuals/obsguide/calibration

[2] gaincal — CASAdocs 6.2 documentation (2021-12-06)
https://casadocs.readthedocs.io/en/v6.2.0/api/tt/casatasks.calibration.gaincal.html

[3] Synthesis Calibration — CASAdocs documentation (2008-02-24)
https://casadocs.readthedocs.io/en/v6.5.5/notebooks/synthesis_calibration.html

[4] ERIS22 - 3C277.1 full tutorial (2022-08-12)
https://www.jb.man.ac.uk/DARA/ERIS22/3C277_full.html

[5] applycal — CASAdocs documentation - Read the Docs
https://casadocs.readthedocs.io/en/stable/api/tt/casatasks.calibration.applycal.html

[6] ERIS2024 - 3C277.1 full tutorial (2024-09-24)
https://eris2024.iaa.csic.es/3C277_full.html

[7] VIPCALs: A fully-automated calibration pipeline for VLBI data - arXiv (2025-08-18)
https://arxiv.org/html/2508.13282v1

[8] VLA Self-calibration Tutorial-CASA5.7.0 - CASA Guides (2020-10-18)
https://casaguides.nrao.edu/index.php/VLA_Self-calibration_Tutorial-CASA5.7.0
