# Forced Photometry Normalization: Implementation Summary

**Date:** 2025-10-24  
**Status:** Ready for Testing  
**Next Step:** Validate on 0702+445 field

---

## What Was Delivered Today

### 1. Literature-Based Algorithm Design

**Document:** `docs/reports/ESE_LITERATURE_SUMMARY.md`

**Key Points:**
- Synthesized differential photometry best practices from radio astronomy literature
- Designed 3-tier normalization algorithm (Simple → Differential → Per-Reference)
- Selected **Option 2 (Differential Flux Ratios)** for implementation
- Expected precision: 1-2% relative (vs 5-7% absolute)

**Algorithm:**
```
1. Establish baseline flux for N reference sources (median of first 10 epochs)
2. Per epoch: measure references, compute correction = current/baseline
3. Apply correction to target sources
```

### 2. Complete Normalization Module

**File:** `src/dsa110_contimg/photometry/normalize.py` (355 lines)

**Functions:**
- `query_reference_sources()`: Query master_sources.final_references within FoV
- `establish_baselines()`: Compute baseline from first N epochs
- `compute_ensemble_correction()`: Measure references, compute correction factor with outlier rejection
- `normalize_measurement()`: Apply correction with error propagation
- `check_reference_stability()`: Monitor references for variability (χ² test)

**Key Features:**
- Queries `master_sources.sqlite3` → `final_references` view (high-SNR stable sources)
- Robust statistics: median, MAD (Median Absolute Deviation)
- Outlier rejection: 3-sigma clipping
- Error propagation: measurement + correction uncertainties
- Reference QA: flags variable references (χ²_ν > 2)

### 3. Validation Test Script

**File:** `tests/test_photometry_normalization_0702.py`

**Two Modes:**

**Mode 1: Baseline (Day 1)**
```bash
python test_photometry_normalization_0702.py \
  --image day1_0702.pbcor.fits \
  --mode baseline \
  --catalog state/catalogs/master_sources.sqlite3
```
- Queries 10-20 high-SNR references in FoV
- Measures all references, establishes baseline
- Saves to `state/photometry_baseline_0702.csv`

**Mode 2: Validate (Day 2)**
```bash
python test_photometry_normalization_0702.py \
  --image day2_0702.pbcor.fits \
  --mode validate \
  --plot
```
- Loads baseline from Day 1
- Measures same references in Day 2 image
- Computes correction factor
- Normalizes measurements
- **Success criteria: MAD < 3%**
- Generates diagnostic plots

**Diagnostic Plots:**
1. Raw flux: Day 1 vs Day 2 (expect 5-10% scatter)
2. Normalized flux: Day 1 vs Day 2 (expect <3% scatter)
3. Correction factor distribution (RMS = systematic uncertainty)
4. Normalized deviation distribution (validates normalization)

---

## Testing Plan for 0702+445 Field

### Prerequisites

1. **Calibrator position:** 0702+445 is at RA ≈ 106.57°, Dec ≈ +44.53°
2. **Transit time:** Calculate LST when RA_0702 = LST (meridian crossing)
3. **Image cadence:** Two consecutive transits, 24 hours apart
4. **Bandpass calibration:** Regenerate using 0702+445 each day

### Day 1: Baseline Establishment

```bash
# Step 1: Image 0702+445 transit, solve bandpass
python -m dsa110_contimg.imaging.cli image_ms \
  --ms /scratch/dsa110-contimg/ms/2025-10-XX_0702_transit.ms \
  --field 0702+445 \
  --solve-bandpass

# Step 2: Run forced photometry baseline mode
python tests/test_photometry_normalization_0702.py \
  --image /scratch/dsa110-contimg/images/2025-10-XX_0702_transit.image.pbcor.fits \
  --mode baseline \
  --catalog state/catalogs/master_sources.sqlite3 \
  --baseline-file state/photometry_baseline_0702.csv
```

**Expected output:**
- N=10-20 reference sources found
- All measured successfully
- Baseline saved to CSV

### Day 2: Normalization Validation

```bash
# Step 1: Image next transit (24h later), regenerate bandpass
python -m dsa110_contimg.imaging.cli image_ms \
  --ms /scratch/dsa110-contimg/ms/2025-10-YY_0702_transit.ms \
  --field 0702+445 \
  --solve-bandpass

# Step 2: Validate normalization
python tests/test_photometry_normalization_0702.py \
  --image /scratch/dsa110-contimg/images/2025-10-YY_0702_transit.image.pbcor.fits \
  --mode validate \
  --baseline-file state/photometry_baseline_0702.csv \
  --plot
```

**Expected results:**
- Correction factor ≈ 0.95-1.05 (tracks day-to-day systematics)
- Normalized flux deviation: MAD < 3%
- If MAD < 2%: Excellent (achieving literature precision)
- If MAD = 2-3%: Good (acceptable for ESE detection)
- If MAD > 3%: Investigate (reference selection, beam model, or calibration issues)

### Success Criteria

✓ **PASS:** Normalized MAD < 3%
- Confirms normalization works
- Proceed with Phase 3 (variability metrics)
- Deploy to pipeline

✗ **FAIL:** Normalized MAD >= 3%
- Debug: Check reference source selection (are they truly stable?)
- Debug: Verify beam model accuracy (spatial systematics?)
- Debug: Bandpass calibration quality
- May need to adjust parameters or upgrade to Option 3 (per-reference tracking)

---

## Key Implementation Details

### Reference Source Selection

**Catalog Query:**
```sql
SELECT source_id, ra_deg, dec_deg, s_nvss, snr_nvss
FROM final_references  -- Already has quality cuts in master_sources.sqlite3
WHERE ra_deg BETWEEN ? AND ?
  AND dec_deg BETWEEN ? AND ?
  AND snr_nvss >= 50
ORDER BY snr_nvss DESC
LIMIT 20
```

**Why final_references view?**
- Combines NVSS (1.4 GHz) + VLASS (3.0 GHz) crossmatch
- Quality cuts: SNR > 80, -1.2 < α < 0.2, resolved_flag=0
- Pre-vetted as stable, flat-spectrum sources
- Perfect for differential photometry

### Baseline Establishment

**Running Median (First 10 Epochs):**
- Pro: Robust to outliers, simple
- Con: Requires ~10 days before baselines solidify
- Alternative: Use dedicated deep calibrator scan as baseline

**For DSA-110:**
- Daily cadence → 10-day baseline establishment is acceptable
- After 10 days: normalization fully operational
- Before 10 days: measurements stored but not normalized

### Correction Factor Statistics

**Median ratio:**
- Tracks atmospheric opacity (water vapor, pressure)
- Tracks instrumental gain drifts
- Typical range: 0.95-1.05 (5% day-to-day variations)

**RMS scatter:**
- Measures ensemble stability
- Target: RMS < 0.02 (2%)
- If RMS > 0.03: investigate reference selection or spatial systematics

### Error Propagation

**Total normalized error:**
```
σ_norm^2 = (σ_meas / correction)^2 + (F_raw * σ_corr / correction^2)^2
           └─measurement error────┘   └─correction uncertainty────────┘
```

- First term: propagates RMS from annulus
- Second term: adds systematic from reference ensemble scatter
- Ensures conservative error estimates

---

## Next Steps After Validation

### If Normalization Passes (<3% scatter)

**Phase 3: Variability Metrics**
1. Implement `photometry/variability.py`:
   - χ²_reduced, fractional variability, significance
   - ESE morphology scoring (asymmetry, timescale, amplitude)
2. Add `photometry_variability` table to database
3. Nightly cron job to compute metrics for all sources with N_epochs > 20

**Phase 4: Pipeline Integration**
1. Hook into `imaging.worker.py` after `.pbcor.fits` creation
2. Automatic forced photometry on all NVSS sources in FoV
3. Store normalized measurements in `photometry_timeseries`
4. Flag ESE candidates automatically

**Phase 5: API & Visualization**
1. Light curve endpoints: `/api/photometry/lightcurve/{source_id}`
2. ESE candidate list: `/api/photometry/ese_candidates`
3. Dashboard with real-time alerts

### If Normalization Fails (>=3% scatter)

**Debug Steps:**
1. Check reference stability: Are they truly non-variable?
2. Inspect spatial systematics: Does scatter correlate with position in FoV?
3. Verify calibration quality: Are bandpass solutions good?
4. Consider upgrade to Option 3 (per-reference tracking)

---

## File Deliverables Summary

### Documentation
- `docs/reports/ESE_LITERATURE_SUMMARY.md` - Algorithm design and theory
- `docs/reports/FORCED_PHOTOMETRY_STATUS_AND_PLAN.md` - Complete implementation roadmap
- `docs/reports/PHOTOMETRY_IMPLEMENTATION_SUMMARY_2025_10_24.md` - This document

### Code
- `src/dsa110_contimg/photometry/normalize.py` - Normalization module (355 lines)
- `tests/test_photometry_normalization_0702.py` - Validation script (247 lines)

### Updates
- `MEMORY.md` - Updated with ESE detection status and implementation phases

---

## Usage Example (Quick Reference)

```bash
# Day 1: Establish baseline
python tests/test_photometry_normalization_0702.py \
  --image day1.pbcor.fits \
  --mode baseline

# Day 2: Validate normalization (after 24h)
python tests/test_photometry_normalization_0702.py \
  --image day2.pbcor.fits \
  --mode validate \
  --plot

# Check results
# If MAD < 3%: SUCCESS - proceed with pipeline integration
# If MAD >= 3%: DEBUG - check references, calibration, beam model
```

---

## Questions for Next Session

1. **Transit times:** Do you have 0702+445 transit times calculated? Need LST when RA=106.57°
2. **Existing data:** Do you have any 0702+445 field images already? Can start validation immediately
3. **Observing schedule:** When is next 0702+445 observation? Need two consecutive transits for test
4. **Calibration workflow:** Confirm bandpass regeneration every 24h is standard procedure

**Ready to test when you provide 0702+445 images!**

