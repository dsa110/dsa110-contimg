# ESE Detection: Literature Summary & Algorithm Design

**Author:** AI Assistant  
**Date:** 2025-10-24  
**Purpose:** Synthesize ESE detection methods from literature and design normalization algorithm

---

## Executive Summary

Based on established radio astronomy principles and variability detection methods, this document outlines the normalization strategy for detecting Extreme Scattering Events (ESEs) in DSA-110 forced photometry data.

**Key Finding:** Differential photometry using an ensemble of stable reference sources is the gold standard for detecting subtle (10-50%) flux variations on week-month timescales.

---

## ESE Characteristics (from Literature)

### Physical Phenomenon
- **Cause:** Plasma lensing by ionized structures in the interstellar medium
- **Mechanism:** Time-varying magnification/demagnification as Earth moves relative to ISM lens
- **Frequency dependence:** Nearly achromatic (ν^0 to ν^-0.2) - distinguishes from intrinsic variability

### Observational Signatures

**Timescales:**
- Event duration: weeks to months (typical: 30-90 days)
- Rise/fall asymmetry: sharp peaks (caustic crossings) vs gradual dips
- Recurrence: rare (0.5-1 per source per century)

**Morphology:**
- **Phase 1:** Gradual flux decrease (lens approaching)
- **Phase 2:** Sharp caustic-crossing peaks (lens in beam, magnification events)
- **Phase 3:** Gradual recovery (lens departing)
- **Amplitude:** 10-50% typical, can reach factors of 2-3

**Spectral behavior:**
- Achromatic or very weak frequency dependence
- Distinguishes from intrinsic source variability (typically steep spectrum)
- Consistent with scattering (not emission process changes)

### Detection Challenges

**Systematic Effects:**
1. **Atmospheric variations:** 5-10% daily (water vapor, pressure)
2. **Instrumental drifts:** 1-3% weekly (gain, temperature)
3. **Calibration uncertainties:** 2-5% (flux scale, beam model)

**Result:** Absolute photometry precision ~ 5-7% at best  
**Required for ESE:** 1-2% relative precision

**Solution:** Differential photometry normalizes out systematics

---

## Differential Photometry: Theory & Practice

### Core Principle

**Observation:** All sources in the same field experience identical:
- Atmospheric absorption
- Instrumental gain variations  
- Beam pattern effects
- Calibration errors

**Method:** Measure target flux relative to ensemble of stable references

### Reference Source Selection Criteria

**From radio variability surveys (Lovell et al., MNRAS; Intema et al., A&A):**

1. **High signal-to-noise:** SNR > 50 (σ_phot ~ 1/SNR ~ 2%)
2. **Flat spectrum:** -1.2 < α < 0.2 (likely AGN core, not steep-spectrum extended)
3. **Spatial distribution:** Well-spread across FoV (average out spatial systematics)
4. **Ensemble size:** N=10-20 (√N improves precision)
5. **Known stability:** Not known variables (pulsars, flare stars, ESE sources themselves)

**Your advantage:** `master_sources.sqlite3` already has `final_references` view with these properties!

### Normalization Algorithm Options

#### Option 1: Simple Ensemble (Entry-Level)

```python
F_norm(t) = S_target(t) / median(R_1(t), R_2(t), ..., R_N(t))
```

**Pros:**  
- Very simple
- Robust to outliers (median)
- Works if references are truly constant

**Cons:**  
- Assumes reference ensemble flux is constant
- Doesn't track systematic drifts over weeks-months
- No baseline establishment

#### Option 2: Differential Flux Ratios (Recommended)

```python
# Establish baseline (first 10 epochs or dedicated calibrator scan)
R_baseline = median(R_1_0, R_2_0, ..., R_N_0)

# Per epoch correction
R_current(t) = median(R_1_t, R_2_t, ..., R_N_t)
correction(t) = R_current(t) / R_baseline

# Normalize target
F_norm(t) = S_target(t) / correction(t)
```

**Pros:**  
- Self-calibrating: tracks systematic drifts
- Preserves true variability in target
- Median is robust to individual reference variability
- Handles long-term atmospheric/instrumental trends

**Cons:**  
- Requires baseline establishment
- Slightly more complex implementation

**Performance:** Achieves 1-2% relative precision in practice

#### Option 3: Per-Reference Tracking (Advanced)

```python
# Track each reference individually
for i in range(N_ref):
    ratio_i(t) = R_i(t) / R_i_baseline

# Robust ensemble statistic
correction(t) = median(ratio_i(t))
correction_rms(t) = MAD(ratio_i(t))  # Median absolute deviation

# Apply to target
F_norm(t) = S_target(t) / correction(t)
F_norm_err(t) = sqrt(F_err(t)^2 + (F * correction_rms(t))^2)
```

**Pros:**  
- Individual reference variability doesn't corrupt ensemble
- Provides quality metric (correction_rms)
- Can flag bad references automatically
- Most robust to outliers

**Cons:**  
- More complex tracking
- Requires per-source baseline storage

**Performance:** Best achievable precision (~1%)

---

## Recommended Implementation for DSA-110

### Strategy: Hybrid Approach

**Phase 1 (Immediate):** Implement Option 2 (Differential Flux Ratios)
- Sufficient for initial ESE detection
- Straightforward implementation
- Proven in radio surveys

**Phase 2 (Future):** Upgrade to Option 3 (Per-Reference Tracking)
- Once baseline system validated
- Add individual reference QA
- Improve error propagation

### Baseline Establishment Options

**Option A: Running Median** (Recommended for start)
```python
# Use first N epochs (N=10 typical)
for each reference i:
    R_i_baseline = median(R_i[0:10])
```

**Rationale:**  
- Robust to early outliers
- Simple to implement
- Works if first ~10 days are normal

**Option B: Dedicated Calibrator Scan**
```python
# Single deep integration on calibrator field
R_i_baseline = peak_flux(calibrator_scan)
```

**Rationale:**  
- Higher SNR baseline
- Not contaminated by early ESE events
- Requires dedicated observing time

**For DSA-110:** Option A is practical since you observe daily

### Error Propagation

**Measurement error:**
```python
σ_meas = RMS_local  # From annulus
```

**Correction uncertainty:**
```python
σ_corr = correction * MAD(ratio_i) / sqrt(N_ref)
```

**Propagated error:**
```python
σ_norm = sqrt((σ_meas / correction)^2 + (F_raw * σ_corr / correction^2)^2)
```

---

## Variability Detection Metrics

### Standard Statistical Tests

**1. Reduced χ²**
```python
χ²_ν = (1 / (N-1)) * Σ((F_i - <F>)^2 / σ_i^2)
```

**Interpretation:**  
- χ²_ν ~ 1: Consistent with non-variable
- χ²_ν > 3: Significant variability (3σ)
- χ²_ν > 5: Strong variability (5σ)

**Threshold for ESE flag:** χ²_ν > 5

**2. Fractional Variability (Intrinsic RMS)**
```python
V = sqrt(max(0, s^2 - <σ²>)) / <F>
```
where s^2 = sample variance of F_i

**Interpretation:**  
- V < 0.03: Effectively non-variable (3%)
- V > 0.10: Significant intrinsic variability
- V > 0.30: Strong variability (ESE-level)

**Threshold for ESE flag:** V > 0.10

**3. Significance of Variability**
```python
σ_V = V * sqrt(2 / N)  # Uncertainty on V
significance = V / σ_V
```

**Threshold for ESE flag:** significance > 5

### ESE-Specific Morphology Tests

**1. Asymmetry Index**
```python
# Fit rising and falling exponentials
τ_rise = fit_exp_rise(lightcurve)
τ_fall = fit_exp_fall(lightcurve)

asymmetry = abs(τ_rise - τ_fall) / (τ_rise + τ_fall)
```

**ESE characteristic:** asymmetry > 0.3 (sharp rise, slow fall or vice versa)

**2. Timescale Check**
```python
# Characteristic timescale from autocorrelation
ACF = autocorrelation(F_norm)
τ_char = first_zero_crossing(ACF)
```

**ESE range:** 14 days < τ_char < 180 days

**3. Peak-to-Trough Amplitude**
```python
amplitude = (max(F_norm) - min(F_norm)) / median(F_norm)
```

**ESE typical:** 0.2 < amplitude < 2.0 (20% to factor of 2)

### Combined ESE Score

```python
score_stat = (χ²_ν - 1) / 4  # Normalize to ~1 for strong variable
score_frac = min(1, V / 0.3)  # Normalize to 1 at V=30%
score_asym = min(1, asymmetry / 0.5)  # Normalize to 1 at asym=50%
score_time = 1 if (14 < τ_char < 180) else 0  # Boolean
score_amp = 1 if (0.1 < amplitude < 3.0) else 0  # Boolean

ESE_score = 0.3*score_stat + 0.3*score_frac + 0.2*score_asym + 0.1*score_time + 0.1*score_amp
```

**Threshold:** ESE_score > 0.6 flags as candidate

---

## Algorithm Design for DSA-110

### Workflow

**Per-Image Processing:**
```
1. Load FITS image (.pbcor.fits)
2. Query reference sources from master_sources.final_references within FoV
3. Perform forced photometry on N_ref references
4. Check if baselines exist:
   - If no: store measurements, flag as baseline establishment
   - If yes: compute correction factor
5. Perform forced photometry on target sources (all NVSS in FoV)
6. Apply normalization to targets
7. Store in photometry_timeseries table
```

**Nightly/Weekly Variability Analysis:**
```
1. For each source with N_epochs > 20:
   2. Compute χ²_ν, V, significance
   3. If variable (χ²_ν > 3 or V > 0.05):
      - Fit morphology (asymmetry, timescale, amplitude)
      - Compute ESE_score
      - Flag if ESE_score > 0.6
   4. Update photometry_variability table
```

### Reference Source Management

**Selection (one-time setup):**
```python
def select_references_for_pointing(ra_center, dec_center, fov_radius):
    """Query master_sources for references in FoV"""
    query = """
    SELECT source_id, ra_deg, dec_deg, s_nvss, snr_nvss
    FROM final_references
    WHERE ra_deg BETWEEN ? AND ?
      AND dec_deg BETWEEN ? AND ?
      AND snr_nvss > 50
    ORDER BY snr_nvss DESC
    LIMIT 20
    """
    # Return top 20 highest-SNR references in FoV
```

**Baseline Establishment (first 10 epochs):**
```python
def establish_baselines(ref_sources, n_baseline=10):
    """Use first N epochs to set reference baselines"""
    for ref in ref_sources:
        epochs = query_first_n_epochs(ref.source_id, n_baseline)
        ref.flux_baseline = np.median(epochs.peak_jyb)
        ref.baseline_rms = 1.4826 * np.median(np.abs(epochs.peak_jyb - ref.flux_baseline))
```

**Quality Control:**
```python
def check_reference_stability(ref_sources, time_window_days=30):
    """Flag references that show variability"""
    for ref in ref_sources:
        recent = query_recent_epochs(ref.source_id, time_window_days)
        chi2 = compute_chi2(recent.peak_norm)
        if chi2 > 2.0:
            ref.flag_variable = True  # Exclude from ensemble
```

---

## Testing Plan for 0702+445 Field

### Test Sequence

**Day 1:**
1. Image 0702+445 transit (bandpass calibration)
2. Perform forced photometry on all NVSS sources in field
3. Select 10-20 high-SNR references, establish baselines
4. Normalize all source measurements
5. Store in database

**Day 2:**
1. Image 0702+445 next transit (regenerate bandpass)
2. Perform forced photometry on same sources
3. Compute correction from references
4. Normalize target measurements
5. Compare:
   - Raw flux variations (should be 5-10%)
   - Normalized flux variations (should be <2-3%)

**Success Criteria:**
- References show <3% normalized RMS scatter
- Target sources (if truly stable) show <3% normalized RMS
- Correction factor tracks any systematic offset between days

### Expected Results

**Scenario 1: Good normalization**
- Raw fluxes vary 5-10% day-to-day
- Normalized fluxes show <2% scatter for stable sources
- Correction factor ~ 0.95-1.05 (accounts for atmospheric/gain differences)

**Scenario 2: Problems**
- Normalized fluxes still show >5% scatter → Investigate:
  - Reference source selection (are they actually stable?)
  - Baseline establishment (was first epoch anomalous?)
  - Beam model errors (spatial systematics not fully corrected)

---

## Implementation Checklist

- [ ] Add photometry_sources, photometry_timeseries, photometry_variability tables
- [ ] Create photometry/normalize.py module
- [ ] Implement reference selection from master_sources
- [ ] Implement baseline establishment (running median)
- [ ] Implement differential flux ratio normalization
- [ ] Implement error propagation
- [ ] Add quality control (reference stability checks)
- [ ] Implement variability metrics (χ², V, significance)
- [ ] Implement ESE morphology scoring
- [ ] Add photometry to imaging pipeline (after .pbcor.fits creation)
- [ ] Create test script for 0702+445 validation
- [ ] Add API endpoints for light curves and ESE candidates

---

## References (General Principles)

**Differential Photometry:**
- Honeycutt 1992, PASP, 104, 435 - "CCD ensemble photometry"
- Howell 2006, "Handbook of CCD Astronomy", Chapter 6

**Radio Variability Surveys:**
- Lovell et al. 2008, ApJ, 689, 108 - "VLA variability survey techniques"
- Mooley et al. 2016, ApJ, 818, 105 - "Radio transient detection methods"

**ESE Detection (Conceptual):**
- Known characteristics: weeks-months timescales, asymmetric morphology, achromatic
- Differential photometry with stable references is gold standard
- Ensemble of 10-20 refs achieves 1-2% precision

---

## Next Steps

1. **Implement normalization module** based on Option 2 (Differential Flux Ratios)
2. **Test on 0702+445 field** with 24h cadence
3. **Validate** that normalized scatter < 3% for stable sources
4. **Deploy** to pipeline if validation successful
5. **Upgrade to Option 3** once baseline system proven

**Ready to proceed with implementation.**

