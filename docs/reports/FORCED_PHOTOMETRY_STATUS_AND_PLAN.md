# Forced Photometry Pipeline: Status & ESE Detection Strategy

**Date:** 2025-10-24  
**Author:** AI Assistant  
**Purpose:** Document current forced photometry implementation status and propose algorithm for detecting Extreme Scattering Events (ESEs)

---

## Executive Summary

The DSA-110 continuum imaging pipeline has **successfully implemented basic forced photometry**—peak flux extraction and local RMS estimation—with measurements stored in a SQL database. However, **critical components for ESE detection are missing**, specifically:

1. No temporal tracking or source registry
2. No flux normalization for relative measurements
3. No variability metrics or ESE-specific detection

This document outlines the current state, scientific requirements, and a concrete implementation roadmap to achieve ESE detection capability.

---

## Current Implementation Status

### What Works (Functional)

**1. Core Measurement Module** (`src/dsa110_contimg/photometry/forced.py`)
- `measure_forced_peak()`: Extracts peak flux in pixel box at world coordinate
- Local RMS from sigma-clipped annulus (for error bars)
- WCS world-to-pixel conversion
- Batch processing via `measure_many()`

**2. Database Storage** (`src/dsa110_contimg/database/products.py`)
```sql
CREATE TABLE photometry (
    id INTEGER PRIMARY KEY,
    image_path TEXT NOT NULL,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    nvss_flux_mjy REAL,        -- catalog reference
    peak_jyb REAL NOT NULL,     -- measured flux
    peak_err_jyb REAL,
    measured_at REAL NOT NULL
);
```
- Insertion helper: `photometry_insert()`
- Single-epoch measurements only

**3. CLI Interface** (`src/dsa110_contimg/photometry/cli.py`)
```bash
# Single source
python -m dsa110_contimg.photometry.cli peak \
  --fits image.pbcor.fits --ra 128.725 --dec 55.573

# NVSS catalog-driven (closest to pipeline integration)
python -m dsa110_contimg.photometry.cli nvss \
  --fits image.pbcor.fits --min-mjy 10.0
```
- `nvss` command measures all NVSS sources in FoV
- Stores both catalog flux and measured peak
- Manual invocation only (not automated)

### What's Missing (Critical Gaps)

1. **No temporal tracking**
   - Measurements are disconnected across epochs
   - No source_id or persistent object registry
   - Cannot build light curves

2. **No flux normalization**
   - All measurements are absolute (Jy/beam)
   - No correction for systematic drifts (atmospheric, instrumental)
   - Cannot compute reliable relative variability

3. **No variability analysis**
   - No χ²_reduced, fractional variability, or significance metrics
   - No ESE-specific detection flags
   - No light curve characterization

4. **No pipeline integration**
   - Requires manual CLI invocation
   - Not triggered automatically after imaging
   - No automatic reference source selection

5. **No quality control**
   - No flags for bad measurements (edge pixels, RFI, etc.)
   - No systematic error tracking

---

## Scientific Requirements for ESE Detection

### Physical Characteristics of ESEs

**Phenomenon:** Plasma lensing by ionized structures in the interstellar medium (ISM)

**Observational Signatures:**
- **Timescales:** Weeks to months (not seconds/minutes)
- **Morphology:** Characteristic asymmetric light curve
  - Initial slow dip (lens approaching)
  - Sharp caustic-crossing peaks (lens in beam)
  - Gradual recovery (lens departing)
- **Achromatic:** Affects all frequencies similarly (scattering, not intrinsic)
- **Rare:** ~0.5-1 event per source per century
- **Amplitude:** 10-50% flux variations (sometimes up to factors of 2-3)

### Detection Challenges

1. **Absolute flux calibration drifts** 
   - Atmospheric opacity variations (5-10% daily)
   - Instrumental gain drifts (1-3% weekly)
   - Primary beam model uncertainties (2-5%)

2. **Confusion with other variability**
   - Intrinsic source variability (AGN flares)
   - RFI contamination
   - Calibration errors

3. **Photometric precision requirement**
   - Need 1-5% relative photometry to detect 10-50% ESE signals
   - Requires robust normalization against stable references

---

## Proposed Solution: Differential Flux Normalization

### Core Strategy

Use an **ensemble of stable reference sources** within each FoV to normalize out systematic variations.

### Reference Source Selection

**Criteria** (leverage existing `master_sources.sqlite3` catalog):
- NVSS SNR > 50 (high signal-to-noise)
- Spectral index: -1.2 < α < 0.2 (flat-spectrum, likely non-variable AGN)
- Not known variables (no pulsars, flare stars, etc.)
- Spatial distribution: 10-20 sources spread across FoV

**Source:** Your catalog already has this! Use the `final_references` view in `state/catalogs/master_sources.sqlite3`.

### Normalization Algorithm (Option B: Differential Flux Ratios)

**Step 1: Establish baseline epoch**
```python
# Use median of first N epochs (N=10 typical) or dedicated calibrator observation
R_baseline = median([R_1_baseline, R_2_baseline, ..., R_N_baseline])
```

**Step 2: Per-epoch correction**
```python
# For each new image epoch t:
R_current = median([R_1_t, R_2_t, ..., R_N_t])  # measure all reference sources
correction_t = R_current / R_baseline

# Apply to target source
F_norm_t = S_target_t / correction_t
```

**Properties:**
- Self-calibrating: tracks systematic drifts
- Robust to individual reference variability (median)
- Preserves true intrinsic variability in target

### Upgrade Path (Option C: Per-Reference Normalization)

For higher robustness:
```python
# Track each reference individually
ratio_i(t) = R_i(t) / R_i_baseline  # for each reference i

# Median across ensemble
correction(t) = median(ratio_i(t) for all i)

# Apply to target
F_norm(t) = S_target(t) / correction(t)
```

**Advantage:** Individual reference variability doesn't corrupt ensemble

---

## Variability Detection Metrics

### Standard Metrics

**1. Reduced χ²**
```python
chi2_reduced = sum((F_norm - F_mean)^2 / F_err^2) / (N - 1)

# Flag if chi2_reduced > 3.0 (significant variability)
```

**2. Fractional Variability**
```python
V_frac = sqrt((F_std^2 - <F_err^2>) / F_mean^2)

# ESE candidates typically V_frac > 0.1 (10% intrinsic variability)
```

**3. Detection Significance**
```python
sigma_var = (V_frac * sqrt(N)) / sqrt(2/N)

# Flag if sigma_var > 5.0 (5-sigma detection)
```

### ESE-Specific Characterization

**Morphology Check:**
1. Fit asymmetric caustic-crossing model (Gaussian rise + exponential decay)
2. Check for characteristic dip→peak→recovery shape
3. Verify timescale consistency (weeks-months, not days or years)
4. Require achromatic behavior (if multi-frequency data available)

**Quality Cuts:**
- Minimum N_epochs > 20 for reliable detection
- Require stable reference ensemble (σ_ref < 0.03)
- Flag and exclude epochs with RFI or bad weather

---

## Database Schema Extension

### New Tables

```sql
-- 1. Source registry (persistent IDs)
CREATE TABLE photometry_sources (
    source_id INTEGER PRIMARY KEY,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    nvss_name TEXT,
    nvss_flux_mjy REAL,
    is_reference INTEGER DEFAULT 0,  -- 1 if used as reference
    created_at REAL NOT NULL
);
CREATE INDEX idx_phot_src_coords ON photometry_sources(ra_deg, dec_deg);
CREATE INDEX idx_phot_src_ref ON photometry_sources(is_reference);

-- 2. Time series measurements (replaces flat photometry table)
CREATE TABLE photometry_timeseries (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    mjd REAL NOT NULL,
    peak_jyb REAL NOT NULL,
    peak_err_jyb REAL,
    peak_norm REAL,            -- normalized flux
    correction_factor REAL,     -- ensemble correction applied
    n_references INTEGER,       -- how many refs used
    ref_rms REAL,              -- scatter in reference ensemble
    quality_flag INTEGER DEFAULT 0,  -- 0=good, 1=suspect, 2=bad
    measured_at REAL NOT NULL,
    FOREIGN KEY(source_id) REFERENCES photometry_sources(source_id)
);
CREATE INDEX idx_phot_ts_source ON photometry_timeseries(source_id);
CREATE INDEX idx_phot_ts_mjd ON photometry_timeseries(mjd);

-- 3. Variability summary (computed per source)
CREATE TABLE photometry_variability (
    source_id INTEGER PRIMARY KEY,
    n_epochs INTEGER NOT NULL,
    mjd_first REAL,
    mjd_last REAL,
    flux_mean REAL,
    flux_std REAL,
    flux_median REAL,
    chi2_reduced REAL,
    frac_variability REAL,
    variability_sigma REAL,
    ese_candidate INTEGER DEFAULT 0,  -- flagged as ESE candidate
    ese_score REAL,                   -- ESE morphology match score
    last_updated REAL NOT NULL,
    FOREIGN KEY(source_id) REFERENCES photometry_sources(source_id)
);
CREATE INDEX idx_phot_var_ese ON photometry_variability(ese_candidate, ese_score);
```

### Migration Strategy

Existing `photometry` table can be migrated:
1. Create `photometry_sources` from unique (ra_deg, dec_deg) in photometry
2. Populate `photometry_timeseries` with foreign keys to sources
3. Compute initial `photometry_variability` from time series
4. Rename `photometry` → `photometry_legacy` (keep for reference)

---

## Implementation Roadmap

### Phase 1: Enhanced Data Model (1-2 days)

**Tasks:**
1. Add new tables to `database/products.py`
2. Create `source_registry_init()` helper:
   - Query NVSS catalog within typical FoV
   - Cross-match with `master_sources.sqlite3`
   - Mark `final_references` as `is_reference=1`
3. Migration script for existing data
4. Update `photometry_insert()` to use new schema

**Deliverables:**
- Schema migration SQL script
- Updated database helpers
- Tests for source matching

### Phase 2: Normalization Module (2-3 days)

**File:** `src/dsa110_contimg/photometry/normalize.py`

**Functions:**
```python
def select_reference_sources(fits_path: str, catalog_db: str) -> List[ReferenceSource]:
    """Query master_sources final_references within FoV."""
    
def establish_baseline(sources: List[int], db: Connection) -> Dict[int, float]:
    """Compute baseline flux for each reference (median of first N epochs)."""
    
def compute_ensemble_correction(
    fits_path: str,
    ref_sources: List[ReferenceSource],
    baseline: Dict[int, float]
) -> CorrectionResult:
    """Measure current reference fluxes and compute correction factor."""
    
def normalize_measurement(
    raw_flux: float,
    correction: CorrectionResult
) -> float:
    """Apply correction to target source measurement."""
```

**Integration:**
- Update `cli.py` to optionally apply normalization
- Add `--normalize` flag to commands

**Deliverables:**
- Normalization module
- Unit tests with synthetic data
- CLI integration

### Phase 3: Time Series & Variability (2-3 days)

**File:** `src/dsa110_contimg/photometry/variability.py`

**Functions:**
```python
def update_timeseries(source_id: int, measurement: Measurement, db: Connection):
    """Add new epoch to time series."""
    
def compute_variability_metrics(source_id: int, db: Connection) -> VariabilityMetrics:
    """Compute chi2, V_frac, sigma_var for source."""
    
def detect_ese_candidates(
    source_id: int,
    db: Connection,
    *,
    chi2_threshold: float = 3.0,
    vfrac_threshold: float = 0.1,
    sigma_threshold: float = 5.0
) -> bool:
    """Flag ESE candidates based on variability metrics."""
    
def characterize_ese_morphology(lightcurve: TimeSeries) -> ESEScore:
    """Fit asymmetric model and score ESE likelihood."""
```

**Deliverables:**
- Variability analysis module
- ESE detection logic
- Light curve characterization

### Phase 4: Pipeline Integration (1-2 days)

**Hook Point:** `imaging.worker.py` after `.pbcor.fits` creation

**Workflow:**
```python
# After tclean completes and .pbcor.fits written:

1. Query NVSS sources in FoV (or use pre-defined target list)
2. Run forced photometry on all sources
3. Apply normalization using reference ensemble
4. Store normalized measurements in photometry_timeseries
5. Update variability metrics
6. Flag new ESE candidates
7. Log results to products DB
```

**Configuration:**
```bash
# In contimg.env
PHOTOMETRY_ENABLE=true
PHOTOMETRY_MIN_NVSS_MJY=10.0
PHOTOMETRY_REFERENCE_SNR_MIN=50
PHOTOMETRY_NORMALIZE=true
```

**Deliverables:**
- Imaging worker integration
- Configuration options
- Performance benchmarks (time per image)

### Phase 5: Visualization & API (2-3 days)

**API Endpoints** (add to `api/routes.py`):

```python
@router.get("/photometry/sources", response_model=PhotSourceList)
def list_sources(
    min_epochs: int = 10,
    ese_candidates_only: bool = False
) -> PhotSourceList:
    """List photometry sources with variability summary."""

@router.get("/photometry/lightcurve/{source_id}")
def get_lightcurve(source_id: int) -> LightCurveData:
    """Retrieve full light curve for source."""

@router.get("/photometry/ese_candidates")
def list_ese_candidates(
    min_score: float = 0.5,
    limit: int = 50
) -> ESECandidateList:
    """List ESE candidates sorted by score."""
```

**Visualizations:**
- Light curve plots (Matplotlib or Plotly)
- Reference ensemble stability check plots
- ESE candidate dashboard with morphology fits

**Deliverables:**
- API endpoints
- Light curve plotting utilities
- Dashboard UI (simple HTML/JS)

---

## Expected Performance

### Photometric Precision

**Theoretical:** σ/S ~ 1/(SNR) ~ 0.01-0.02 (1-2%) for SNR > 50 sources

**Systematic Floor:** ~0.03-0.05 (3-5%) limited by:
- Primary beam model accuracy
- Atmospheric variations (even with normalization)
- Calibration errors

**ESE Detection Threshold:** 10-50% variations easily detectable at 5-10σ significance

### Computational Cost

**Per-image overhead:**
- ~200 NVSS sources per FoV
- ~0.1 sec per forced photometry measurement
- ~20 sec total per image (acceptable)

**Storage:**
- ~200 bytes per measurement × 200 sources × 1000 epochs = 40 MB per field
- Negligible compared to MS/image sizes

---

## Testing & Validation Strategy

### Phase-by-Phase Testing

**Phase 1 (Database):**
- Unit tests for source matching
- Migration script validation on test DB

**Phase 2 (Normalization):**
- Synthetic light curves with known injection
- Validate correction removes systematic trends
- Check robustness to individual reference variability

**Phase 3 (Variability):**
- Inject synthetic ESE events into real data
- Validate detection thresholds (ROC curves)
- Test morphology characterization

**Phase 4 (Pipeline):**
- End-to-end test on historical data
- Performance benchmarking
- Validate storage and retrieval

**Phase 5 (API/Viz):**
- API endpoint tests
- UI/dashboard user testing

### Validation with Known Variables

**Positive Controls:**
- Known AGN with documented variability
- Pulsar fields (though too fast for ESE)
- Previously detected ESEs (if available)

**Negative Controls:**
- Stable calibrators (3C sources)
- Reference sources themselves (should show minimal variability)

---

## Next Steps & Questions

### Immediate Actions

1. **Confirm cadence:** How often does DSA-110 re-observe the same field?
   - ESE detection requires weeks-months baseline
   - Need at least ~20 epochs per source for robust statistics

2. **Check reference density:** Verify ~10-20 high-SNR NVSS sources per typical FoV
   - Query `master_sources.sqlite3` for representative pointings
   - May need to adjust FoV size or reference selection criteria

3. **Review existing data:** Check `photometry` table
   - How many measurements already exist?
   - Can we retroactively apply normalization?

### Literature Access

The `/data/dsa110-contimg/references/query_bib/` tools are available for downloading papers. Once you provide specific bibcodes or arXiv IDs for ESE papers (e.g., Fiedler et al. 1987, 1994; Walker papers; recent reviews), I can download and read them to refine:
- ESE morphology models
- Typical timescales and amplitudes
- Detection criteria from literature

### Decision Point

**Do you want me to:**

**Option A:** Proceed with full implementation (Phases 1-5, ~8-13 days)

**Option B:** Implement just normalization (Phases 1-2) and evaluate with test data first

**Option C:** Provide more specific literature analysis before coding (if you can supply bibcodes)

**Option D:** Check existing photometry data and assess retroactive normalization feasibility

Let me know your preference and I'll proceed accordingly!

---

## References

- Your existing tools: `photometry/forced.py`, `photometry/cli.py`, `database/products.py`
- Your catalog: `state/catalogs/master_sources.sqlite3` (already has `final_references` view)
- Pipeline integration point: `imaging.worker.py`
- API framework: `api/routes.py`

## Contact

For questions or to request specific ESE literature downloads, please provide bibcodes or arXiv IDs via the `/data/dsa110-contimg/references/query_bib/` tools.

