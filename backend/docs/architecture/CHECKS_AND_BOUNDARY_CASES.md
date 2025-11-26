# Pipeline Checks and Boundary Cases: Data & Science Requirements

## Overview

The DSA-110 imaging pipeline enforces numerous **checks** and **boundary cases**
that encode critical data-processing and scientific requirements. These checks
prevent invalid data from flowing through the pipeline and ensure published
products meet scientific standards.

This document catalogs all major checks and explains what data/science
requirement each enforces.

---

## Category 1: Data Format & Structure Checks

### Check 1.1: MS Frequency Order Validation

**Location**: `conversion/helpers_validation.py::validate_ms_frequency_order()`

**What it checks**:

- Spectral windows (subbands) are in **ascending frequency order**
- Within each SPW, channels are in ascending frequency order

**Why it matters** (Data Requirement):

- DSA-110 subbands arrive in DESCENDING order from raw HDF5 (sb00=highest,
  sb15=lowest)
- CASA imaging assumes ASCENDING frequency order
- If frequencies out of order:
  - MFS imaging produces **fringe artifacts**
  - Bandpass calibration **fails or produces wrong solutions**
  - Source catalogs become **unreliable**

**Failure action**: Raises `RuntimeError` - entire conversion aborted

**Science requirement**: **Frequency monotonicity** for valid spectral analysis

---

### Check 1.2: Phase Center Coherence Validation

**Location**:
`conversion/helpers_validation.py::validate_phase_center_coherence()`

**What it checks**:

- All spectral windows point to the **same sky coordinates** (within 1 arcsec by
  default)
- Multiple fields are handled consistently
- Detects time-dependent phasing and flags for special handling

**Why it matters** (Data Requirement):

- Mosaicking assumes aligned field centers
- If SPWs point to different locations:
  - Mosaics become **misaligned**
  - Calibration vectors are **incompatible**
  - Astrometry becomes **incorrect**

**Failure action**: Raises `RuntimeError` if too much scatter

**Science requirement**: **Coherent pointing** across all frequency channels

---

### Check 1.3: UVW Precision Validation

**Location**: `conversion/helpers_validation.py::validate_uvw_precision()`

**What it checks**:

- UVW coordinates are accurate to within **0.1 wavelengths** (default)
- No NaN or Inf values in UVW arrays
- UVW distribution is physically reasonable (not clustered at origin)

**Why it matters** (Data Requirement):

- Calibration requires accurate baseline coordinates
- If UVW precision poor:
  - Bandpass calibration **maps to wrong sky coordinates**
  - Self-calibration produces **wildly inaccurate** phase solutions
  - Images show **incorrect structure**

**Failure action**: Warning (non-fatal) - continues but logs concern

**Science requirement**: **High-precision astrometry** for calibration

---

### Check 1.4: Antenna Position Validation

**Location**: `conversion/helpers_validation.py::validate_antenna_positions()`

**What it checks**:

- Antenna positions match known DSA-110 array configuration
- No physically impossible positions (e.g., NaN, extreme outliers)
- Consistency with expected array baseline range

**Why it matters** (Data Requirement):

- Invalid antenna positions break calibration
- If antenna positions wrong:
  - Phase solutions computed at **wrong baseline locations**
  - Calibration vectors are **incorrect**
  - Mosaics show **systematic pointing errors**

**Failure action**: Warning if reference file not available; raises error if
impossible positions

**Science requirement**: **Valid array geometry** for self-calibration

---

### Check 1.5: Model Data Quality Validation

**Location**: `conversion/helpers_validation.py::validate_model_data_quality()`

**What it checks**:

- MODEL_DATA column contains reasonable flux values
- No NaN/Inf in model data
- Model flux structure matches expected source properties

**Why it matters** (Data Requirement):

- MODEL_DATA used in self-calibration
- If model data corrupted:
  - Calibration convergence **fails**
  - Self-cal produces **spurious solutions**

**Failure action**: Warning (non-fatal)

**Science requirement**: **Valid model data** for calibration

---

## Category 2: Calibration Consistency Checks

### Check 2.1: Calibration Application Consistency

**Location**: `mosaic/validation.py::check_calibration_consistency()`

**What it checks**:

- All tiles have **consistent calibration applied** (all or none)
- Calibration table sets are **identical across tiles**
- Calibration validity windows **overlap appropriately**

**Why it matters** (Science Requirement):

- Mosaicking assumes common calibration
- If some tiles calibrated, others not:
  - Mosaic has **discontinuous sensitivity**
  - Flux measurements are **incomparable across tiles**
  - Source detection **biased toward calibrated regions**

**Failure action**: Records as issue → `qa_status='warning'` (blocks
auto-publish)

**Science requirement**: **Uniform calibration** across mosaic group

---

### Check 2.2: Calibration Table Existence & Validity

**Location**: `mosaic/streaming_mosaic.py` and `calibration/apply_service.py`

**What it checks**:

- Calibration tables exist on disk at registered paths
- Tables are not corrupted (can be opened)
- Validity time windows include the observation time

**Why it matters** (Data Requirement):

- Registry says tables exist but files might be deleted/moved
- If tables missing:
  - Calibration application **fails catastrophically**
  - Pipeline stalls waiting for tables that don't exist

**Failure action**: Pipeline skips to re-solving calibration or fails

**Science requirement**: **Persistent calibration artifacts** for
reproducibility

---

## Category 3: Image Quality Checks

### Check 3.1: Image Existence & Format

**Location**: `mosaic/validation.py::validate_tile_quality()`

**What it checks**:

- Image file exists on disk
- Primary beam corrected image available (pbcor version)
- FITS/CASA image format valid and readable

**Why it matters** (Data Requirement):

- Images might be deleted between reference and use
- If image missing or corrupted:
  - Mosaicking **fails**
  - Data loss without clear error message

**Failure action**: Records as critical issue → prevents mosaicking

**Science requirement**: **Data integrity** through pipeline

---

### Check 3.2: Dynamic Range Requirement

**Location**: `qa/image_quality.py::validate_image_quality()`

**Configuration**: `max_dynamic_range: 100.0` (default)

**What it checks**:

- Peak signal-to-noise ratio (SNR) satisfies:
  `DR = peak_value / rms_noise > 100`

**Why it matters** (Science Requirement):

- Low dynamic range indicates poor calibration or data quality
- If DR < 100:
  - Photometry measurements are **unreliable**
  - Faint sources are **lost in noise**
  - Flux calibration **questionable**

**Failure action**: Records as issue → affects QA status

**Science requirement**: **Sufficient signal-to-noise** for science

---

### Check 3.3: RMS Noise Threshold

**Location**: `qa/image_quality.py::validate_image_quality()`

**Configuration**: `max_rms_noise: 0.001` (1 mJy/beam default)

**What it checks**:

- RMS noise in image is below 1 mJy/beam

**Why it matters** (Science Requirement):

- Noise level determines source detection sensitivity
- If noise > 1 mJy/beam:
  - Cannot detect faint sources
  - Image quality is **poor compared to DSA-110 specification**

**Failure action**: Records as issue → affects QA status

**Science requirement**: **Meets specification for sensitivity**

---

### Check 3.4: Primary Beam Correction Application

**Location**: `mosaic/validation.py::check_primary_beam_consistency()`

**What it checks**:

- Primary beam corrected images exist for all tiles
- Primary beam response curves are **consistent across tiles**
- All tiles have **uniform PB correction** (all corrected or all not)

**Why it matters** (Science Requirement):

- PB correction essential for accurate source measurements
- If PB inconsistent:
  - Flux measurements **vary by position on sky**
  - Sensitivity varies **inconsistently**
  - Source detection **biased toward image center**

**Failure action**: Records as issue → `qa_status='warning'`

**Science requirement**: **Uniform primary beam correction** for flux
calibration

---

## Category 4: Mosaic Geometric Consistency Checks

### Check 4.1: Grid Consistency (Shape & Cell Size)

**Location**: `mosaic/validation.py::validate_tiles_consistency()`

**What it checks**:

- All tiles have **identical image dimensions** (e.g., all 1024×1024)
- All tiles have **identical cell size** (arcsec/pixel)
- Tolerance: Cell size difference < 0.001% (1e-9 relative)

**Why it matters** (Science Requirement):

- Mosaicking assumes common pixel grid
- If grids differ:
  - Reprojection required (causes **artifacts**)
  - Flux calibration becomes **uncertain**
  - Pixel coordinates become **unreliable**

**Failure action**: Critical issue → prevents mosaicking

**Science requirement**: **Common coordinate grid** for tile alignment

---

### Check 4.2: Noise Consistency

**Location**: `mosaic/validation.py::validate_tiles_consistency()`

**What it checks**:

- RMS noise is consistent within **factor of 5** across tiles
- Flags tiles with unusually high noise (> 5x median)

**Why it matters** (Science Requirement):

- Indicates differential data quality
- If noise varies 5x:
  - Some tiles may be compromised
  - Mosaic is **sensitivity-limited by worst tile**
  - Source detection **biased toward low-noise regions**

**Failure action**: Records as warning → affects QA assessment

**Science requirement**: **Uniform sensitivity** across mosaic

---

### Check 4.3: Synthesized Beam Consistency

**Location**: `mosaic/validation.py::validate_tiles_consistency()`

**What it checks**:

- Synthesized beam size is consistent within **20%** across tiles
- Major & minor axes both checked
- Position angle consistency implied

**Why it matters** (Science Requirement):

- Beam size directly affects source resolution and photometry
- If beams differ 20%+:
  - Point-spread function is **spatially variable**
  - Source morphology measurements are **unreliable**
  - Photometry becomes **uncertain**

**Failure action**: Records as warning → affects QA status

**Science requirement**: **Uniform resolution** across mosaic for photometry

---

### Check 4.4: Astrometric Registration Accuracy

**Location**: `mosaic/validation.py::verify_astrometric_registration()`

**Configuration**:

- `max_offset_arcsec: 2.0` (default)
- `max_rms_arcsec: 0.5` (default)
- `min_sources: 3` (minimum for validation)

**What it checks**:

- Sources in each tile match catalog positions within **2 arcsec**
- RMS scatter of offsets < **0.5 arcsec**
- At least 3 catalog sources detected per tile

**Why it matters** (Science Requirement):

- Pointing/tracking accuracy critical for source catalog matching
- If astrometry off by 2 arcsec:
  - Cross-matching with other surveys **fails**
  - Photometry measurements **miss targets**
  - Multi-wavelength correlations become **unreliable**

**Failure action**: Records as warning → affects QA status

**Science requirement**: **Sub-2-arcsec astrometry** for catalog matching

---

## Category 5: Publishing & Registry Checks

### Check 5.1: Mosaic Registration Status

**Location**: `database/data_registry.py`

**What it checks**:

- Mosaic has entry in `data_registry` with `status='staging'`
- `data_id` is unique (no duplicates)
- Metadata includes required fields (group_id, n_images, time_range)

**Why it matters** (Data Requirement):

- Registry is single source of truth for published data
- If not registered:
  - External systems cannot find mosaic
  - Pipeline state tracking **broken**
  - Data lineage is **lost**

**Failure action**: Logs error, mosaic stays in staging

**Science requirement**: **Data provenance tracking** for reproducibility

---

### Check 5.2: QA Status Gate

**Location**: `database/data_registry.py::trigger_auto_publish()`

**What it checks**:

- `qa_status == 'passed'` (required)
- `validation_status == 'validated'` (required)
- No blocking warnings (e.g., inconsistent calibration, noise outliers)

**Why it matters** (Science Requirement):

- Prevents publishing low-quality data
- If QA status not 'passed':
  - Mosaic remains in staging
  - Manual review available before publishing
  - **Protects data archive from corrupted products**

**Failure action**: Auto-publish blocked → manual publish required

**Science requirement**: **Quality gating** before publishing

---

### Check 5.3: Path Validation Before Publishing

**Location**: `database/data_registry.py::trigger_auto_publish()`

**What it checks**:

- `stage_path` exists and is readable
- `published_path` destination is writable
- Paths are within expected directories:
  - Stage: `/stage/dsa110-contimg/`
  - Published: `/data/dsa110-contimg/products/`

**Why it matters** (Data Requirement):

- Prevents data loss if paths misconfigured
- If paths invalid:
  - Files moved to wrong locations
  - Data becomes **unreachable**
  - Publishing **silently fails**

**Failure action**: Raises exception, rollback, error logged

**Science requirement**: **Safe file operations** with validation

---

### Check 5.4: Validation Issues Recording

**Location**: `mosaic/post_validation.py` and `database/data_registry.py`

**What it checks**:

- All validation issues (warnings, errors) captured in metadata
- Issues stored in `data_registry.metadata_json`
- Issues accessible for later review

**Why it matters** (Data Requirement):

- Users need to know why data has warnings
- If issues not recorded:
  - Users can't assess data quality
  - Warning status appears **arbitrary**
  - Scientific reproducibility compromised

**Failure action**: Issues recorded in metadata

**Science requirement**: **Transparent data quality reporting**

---

## Category 6: Data Continuity Checks

### Check 6.1: Idempotent Operations

**Location**: Throughout pipeline (conversion, imaging, mosaicking)

**What it checks**:

- Database state checked before re-processing
- Existing output files detected and skipped
- Same inputs always produce same outputs

**Why it matters** (Data Requirement):

- Enables safe retries without data corruption
- If not idempotent:
  - Retrying failed job **corrupts data**
  - Users cannot safely restart pipeline
  - **Partial states** become unrecoverable

**Failure action**: Skips re-processing, returns cached result

**Science requirement**: **Safe re-execution** for debugging

---

### Check 6.2: File Existence Verification

**Location**: Throughout pipeline

**What it checks**:

- Input files exist before processing
- Output files exist after processing
- References in database match filesystem

**Why it matters** (Data Requirement):

- Prevents "ghost" data (in DB but not on disk)
- If files deleted/moved:
  - Pipeline continues with stale references
  - Users get **incorrect data**
  - **Silent data loss**

**Failure action**: Fails with clear error message

**Science requirement**: **Data integrity** verification

---

## Summary Table: Check Categories & Their Implications

| Category               | Purpose                       | Failure Impact                   | Scientific/Data Requirement                          |
| ---------------------- | ----------------------------- | -------------------------------- | ---------------------------------------------------- |
| **Format & Structure** | Ensure valid data layout      | Catastrophic pipeline failure    | Valid spectral, astrometric, and geometric structure |
| **Calibration**        | Ensure consistent calibration | Incorrect flux/phase corrections | Uniform calibration across mosaic                    |
| **Image Quality**      | Ensure useful images          | Poor science output              | Sufficient SNR and dynamic range for detection       |
| **Geometric**          | Ensure alignable tiles        | Cannot mosaic                    | Common pixel grid, resolution, astrometry            |
| **Publishing**         | Ensure quality products       | Corrupted archive                | Only high-quality data published                     |
| **Continuity**         | Ensure safe operations        | Data loss/corruption             | Reproducible, safe pipeline execution                |

---

## Key Insight: Boundaries Define Science Capability

Each check defines a **boundary** between acceptable and unacceptable data:

- **RMS noise < 1 mJy**: Sensitivity boundary
- **Dynamic range > 100**: Quality boundary
- **Astrometry < 2 arcsec**: Catalog matching boundary
- **Beam consistency < 20%**: Morphology boundary
- **Phase center < 1 arcsec**: Alignment boundary
- **Frequency monotonic**: Spectral validity boundary

Exceeding these boundaries doesn't just produce wrong numbers—it produces
**scientifically meaningless** results. The pipeline treats boundary violations
as **fatal** or **critical warnings** depending on severity.

---

## Configuration & Tuning

Most checks have configurable thresholds in `qa/config.py`:

```python
class QAConfig:
    max_rms_noise: float = 0.001  # 1 mJy/beam
    min_dynamic_range: float = 100.0
    max_offset_arcsec: float = 2.0
    max_rms_arcsec: float = 0.5
    # ... etc
```

These defaults are **science-driven**, not arbitrary. Changing them changes what
data the pipeline will publish.
