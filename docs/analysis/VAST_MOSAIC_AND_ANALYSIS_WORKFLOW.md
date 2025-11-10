# VAST Mosaic Creation and Analysis Workflow

**Date:** 2025-01-XX  
**Purpose:** Analysis of VAST Pipeline mosaic creation and image/mosaic analysis workflows  
**Reference:** VAST Pipeline (https://vast-survey.org/vast-pipeline/) + VAST Tools codebase  
**Source:** Perplexity search results + VAST Tools code analysis

---

## Executive Summary

VAST Pipeline uses a sophisticated workflow for creating mosaics from ASKAP beam images and performing science analysis. This document analyzes:
1. **Mosaic Creation**: How VAST combines individual beam images into mosaics
2. **Image/Mosaic Analysis**: How VAST performs science analysis on mosaics and images
3. **Comparison with DSA-110**: How DSA-110's approach compares and what can be learned

**Key Findings:**
- VAST uses **linear mosaicking** with primary beam weighting (immath/imcombine)
- **Two-tier structure**: TILES (individual beams) → COMBINED (mosaics)
- **Selavy source finding** on mosaics for catalog generation
- **Pipeline analysis** for transient/variability detection
- **Light curve construction** from multi-epoch measurements

---

## 1. VAST Mosaic Creation Workflow

### 1.1 High-Level Process

**VAST Mosaic Creation Steps:**

```
Individual Beam Images (36 PAF beams)
    ↓
Primary Beam Correction (per beam)
    ↓
Convolution to Common Resolution
    ↓
Linear Mosaicking (immath/imcombine)
    ├─ Primary Beam Weighting
    ├─ Overlapping Region Handling
    └─ Flux Scaling
    ↓
COMBINED Mosaic Image
    ↓
Source Finding (Selavy)
    ↓
Source Catalog
```

### 1.2 Technical Details

**From ASKAPsoft Documentation:**
- **Linear Mosaicking**: Combines images using weighted averages
- **Primary Beam Weighting**: Each pixel weighted by PB²/σ² (Sault weighting)
- **Common Resolution**: All beams convolved to standard resolution before combining
- **Overlapping Regions**: Properly handled with weighted combination

**Tools Used:**
- **immath** (CASA): Mathematical operations on images (PB correction, scaling)
- **imcombine** (CASA): Combines multiple images into mosaic
- **Alternative**: Custom mosaicking scripts using numpy/astropy

**Key Parameters:**
- Weighting scheme: PB²/σ² (optimal SNR weighting)
- Projection: Common coordinate system (e.g., SIN projection)
- Overlap handling: Weighted average in overlapping regions

### 1.3 Directory Structure

**VAST Data Organization:**

```
EPOCH{XX}/
├── TILES/
│   ├── STOKESI_IMAGES/
│   │   ├── image.i.{field}.SB{SBID}.cont.taylor.0.restored.fits
│   │   └── image.i.{field}.SB{SBID}.cont.taylor.0.restored.conv.fits
│   ├── STOKESI_RMSMAPS/
│   │   └── noiseMap.image.i.{field}.SB{SBID}.cont.taylor.0.restored.fits
│   └── STOKESI_SELAVY/
│       └── {field}.SB{SBID}.selavy.components.txt
└── COMBINED/
    ├── STOKESI_IMAGES/
    │   └── {field}.EPOCH{XX}.I.conv.fits
    ├── STOKESI_RMSMAPS/
    │   └── {field}.EPOCH{XX}.I_rms.fits
    └── STOKESI_SELAVY/
        └── {field}.EPOCH{XX}.I.selavy.components.txt
```

**Key Points:**
- **TILES**: Individual beam images (36 per field)
- **COMBINED**: Mosaicked images (1 per field)
- Both have associated RMS maps and Selavy catalogs

### 1.4 Mosaicking Algorithm

**Sault Weighting Scheme:**

For each pixel (i,j) in the mosaic:

```
weight[k][i,j] = pb_response[k][i,j]² / noise_variance[k]
mosaic[i,j] = Σ(weight[k][i,j] * tile[k][i,j]) / Σ(weight[k][i,j])
```

**Where:**
- `pb_response[k][i,j]`: Primary beam response for tile k at pixel (i,j)
- `noise_variance[k]`: Noise variance for tile k
- `tile[k][i,j]`: Pixel value from tile k

**Benefits:**
- Optimal SNR weighting
- Proper flux scaling
- Handles overlapping regions correctly

---

## 2. VAST Image/Mosaic Analysis Workflow

### 2.1 Source Finding (Selavy)

**Purpose:** Detect and characterize sources in mosaics

**Selavy Workflow:**
1. **Statistical Analysis**: Apply global/local statistics to identify sources
2. **Thresholding**: SNR-based detection (configurable threshold)
3. **Component Extraction**: Extract source properties (flux, position, size)
4. **Island Detection**: Group components into islands (optional)

**Output:**
- Component catalog: Individual source detections
- Island catalog: Grouped sources (optional)
- RMS maps: Background noise estimation
- Background maps: Sky background estimation

**Key Parameters:**
- SNR threshold: Typically 5σ for reliable detections
- Statistics: Robust (MADFM) or classical (mean/std)
- Island detection: Optional grouping of components

### 2.2 Pipeline Analysis

**VAST Pipeline Analysis Steps:**

```
Mosaic Images + Selavy Catalogs
    ↓
Image & Catalog Ingest
    ├─ Load images.parquet
    ├─ Load measurements.parquet
    └─ Load sources.parquet
    ↓
Source Association
    ├─ Spatial matching across epochs
    ├─ Epoch-based association
    └─ Light curve construction
    ↓
Variability Analysis
    ├─ Variability metrics (V, η)
    ├─ Two-epoch metrics (Vs, M)
    └─ Transient detection
    ↓
Science Products
    ├─ Light curves
    ├─ Variability statistics
    └─ Transient candidates
```

### 2.3 Variability Metrics

**From VAST Tools (`vasttools/utils.py`):**

**1. Fractional Variability (V):**
```python
V = std(flux) / mean(flux)
```

**2. η Metric:**
```python
weights = 1 / flux_err²
η = (N / (N-1)) * (
    mean(weights * flux²) - 
    (mean(weights * flux)² / mean(weights))
)
```

**3. Two-Epoch Metrics:**

**Vs Metric (t-statistic):**
```python
Vs = (flux_a - flux_b) / sqrt(flux_err_a² + flux_err_b²)
```

**M Metric (modulation index):**
```python
M = 2 * (flux_a - flux_b) / (flux_a + flux_b)
```

**Reference:** Mooley et al. (2016), DOI: 10.3847/0004-637X/818/2/105

### 2.4 Light Curve Construction

**VAST Pipeline Light Curves:**

**From `vasttools/source.py::Source.plot_lightcurve()`:**

**Features:**
- Peak and integrated flux options
- Error bars and upper limits
- Multiple time axes (datetime, MJD, days from start)
- Frequency grouping (if multi-frequency)
- Forced photometry integration

**Workflow:**
1. Load measurements for source across epochs
2. Group by frequency (if multi-frequency)
3. Plot detections and upper limits
4. Apply color coding by frequency
5. Add error bars and annotations

### 2.5 Transient Detection

**VAST Transient Detection:**

**Two-Epoch Analysis:**
- Compare consecutive epochs
- Calculate Vs and M metrics
- Flag significant variations
- Generate transient candidates

**Multi-Epoch Analysis:**
- Build light curves
- Calculate variability statistics
- Identify transient patterns
- Generate alerts

**Key Methods:**
- `run_two_epoch_analysis()`: Two-epoch comparison
- `run_transient_search()`: Multi-epoch transient detection
- `run_variability_search()`: Variability analysis

---

## 3. DSA-110 Comparison

### 3.1 Mosaic Creation

**VAST Approach:**
- Linear mosaicking with PB weighting
- immath/imcombine tools
- Sault weighting scheme
- Common resolution convolution

**DSA-110 Approach:**
- Primary beam-weighted combination (`_build_weighted_mosaic()`)
- Uses CASA `immath` and `imregrid`
- Sault weighting scheme (PB²/σ²)
- Common coordinate system regridding

**Comparison:**

| Aspect | VAST | DSA-110 |
|--------|------|---------|
| **Weighting** | PB²/σ² (Sault) | PB²/σ² (Sault) ✅ |
| **Tools** | immath/imcombine | immath/imregrid ✅ |
| **Regridding** | Common resolution | Common coordinate system ✅ |
| **Overlap Handling** | Weighted average | Weighted average ✅ |
| **Validation** | Basic checks | Comprehensive validation ✅ |

**Key Findings:**
- ✅ DSA-110's approach matches VAST's best practices
- ✅ Sault weighting scheme correctly implemented
- ✅ Proper regridding to common coordinate system
- ✅ Comprehensive validation (DSA-110 advantage)

### 3.2 Image/Mosaic Analysis

**VAST Approach:**
- Selavy source finding on mosaics
- Pipeline analysis for variability
- Light curve construction
- Transient detection

**DSA-110 Approach:**
- Forced photometry at catalog positions
- Differential normalization
- Variability statistics (χ², V)
- ESE detection (specialized)

**Comparison:**

| Aspect | VAST | DSA-110 |
|--------|------|---------|
| **Source Finding** | Selavy (blind detection) | Forced photometry (catalog-based) |
| **Variability Metrics** | V, η, Vs, M | χ², V (fractional variability) |
| **Light Curves** | Multi-epoch plots | Normalized flux timeseries |
| **Science Goal** | Transient detection | ESE detection (slow variability) |

**Key Differences:**
- **Source Finding**: VAST uses blind detection (Selavy), DSA-110 uses forced photometry
- **Variability Metrics**: VAST has more metrics (η, Vs, M), DSA-110 focuses on χ² and V
- **Normalization**: DSA-110 uses differential normalization (1-2% precision)
- **Science Focus**: VAST (transients), DSA-110 (ESEs - slow variability)

**Both Valid:**
- VAST's approach: Good for discovering new sources
- DSA-110's approach: Good for monitoring known sources (ESEs)

### 3.3 Analysis Workflow

**VAST Pipeline Analysis:**

```
Images → Selavy → Catalogs → Association → Light Curves → Variability
```

**DSA-110 Pipeline Analysis:**

```
Images → Forced Photometry → Normalization → Variability Stats → ESE Detection
```

**Key Differences:**
- VAST: Blind detection → association → analysis
- DSA-110: Catalog-based → forced photometry → normalization → analysis

**Both Approaches:**
- ✅ Valid for their respective science goals
- ✅ VAST: Discovery-oriented (transients)
- ✅ DSA-110: Monitoring-oriented (ESEs)

---

## 4. Key Patterns and Best Practices

### 4.1 Mosaic Creation

**1. Primary Beam Weighting**
- Always use PB²/σ² weighting (Sault scheme)
- Ensures optimal SNR and proper flux scaling
- Critical for accurate mosaics

**2. Common Coordinate System**
- Regrid all tiles to common coordinate system
- Ensures proper alignment
- Handles overlapping regions correctly

**3. Validation**
- Check grid consistency
- Verify astrometric registration
- Validate calibration consistency
- Check primary beam consistency

**4. Quality Metrics**
- Track effective integration time per pixel
- Track PB response per pixel
- Track noise variance per pixel
- Track number of tiles contributing per pixel

### 4.2 Image/Mosaic Analysis

**1. Source Finding**
- Use appropriate tool for science goal
- Selavy for blind detection
- Forced photometry for known sources
- Both have their place

**2. Variability Metrics**
- Use multiple metrics (V, η, χ², Vs, M)
- Each metric provides different insights
- Combine metrics for robust detection

**3. Light Curve Construction**
- Include error bars
- Handle upper limits properly
- Support multiple time axes
- Group by frequency if multi-frequency

**4. Multi-Epoch Analysis**
- Proper source association
- Handle missing epochs
- Account for systematic effects
- Use normalization when needed

---

## 5. Recommendations for DSA-110

### 5.1 Mosaic Creation (Already Well-Implemented)

**Current Status:** ✅ Excellent alignment with VAST

**Minor Enhancements:**
1. **Quality Metrics Visualization**: Create visualization of mosaic quality metrics (integration time, PB response, noise, coverage)
2. **Mosaic Validation Reports**: Generate comprehensive validation reports
3. **Performance Optimization**: Benchmark mosaic creation performance

### 5.2 Image/Mosaic Analysis (Enhancement Opportunities)

**1. Additional Variability Metrics (High Priority)**
- Add η metric calculation (complementary to χ²)
- Add two-epoch metrics (Vs, M) for rapid change detection
- Useful for ESE caustic crossing detection

**2. Light Curve Visualization (High Priority)**
- Implement light curve plotting (from VAST Tools)
- Add baseline period highlighting
- Add ESE candidate period highlighting
- Support multiple time axes

**3. Source Finding Integration (Medium Priority)**
- Consider adding Selavy-like source finding for discovery
- Could complement forced photometry
- Useful for finding new sources in mosaics

**4. Mosaic Analysis Tools (Medium Priority)**
- Create mosaic analysis class (similar to VAST's `Image` class)
- Provide methods for:
  - Mosaic quality assessment
  - Source finding on mosaics
  - Cross-epoch comparison
  - Coverage analysis

**5. Background/Noise Estimation (Low Priority)**
- Implement systematic background estimation
- Create background maps (like VAST's `meanMap`)
- Useful for quality assurance

---

## 6. Code Examples

### 6.1 Mosaic Creation (DSA-110 Current)

**From `mosaic/cli.py::_build_weighted_mosaic()`:**

```python
def _build_weighted_mosaic(
    tiles: List[str],
    metrics_dict: dict,
    output_path: str,
) -> None:
    """
    Build mosaic using primary beam-weighted combination.
    
    Weighting: weight[k][i,j] = pb_response[k][i,j]² / noise_variance[k]
    Mosaic: mosaic[i,j] = Σ(weight[k][i,j] * tile[k][i,j]) / Σ(weight[k][i,j])
    """
    # Regrid all tiles to common coordinate system
    # Calculate weights: PB² / σ²
    # Combine with weighted average
    # Save mosaic
```

**Alignment:** ✅ Matches VAST's approach

### 6.2 Variability Metrics (VAST Reference)

**From `vasttools/utils.py`:**

```python
def calculate_vs_metric(
    flux_a: float, flux_b: float, flux_err_a: float, flux_err_b: float
) -> float:
    """Vs metric: t-statistic for variability."""
    return (flux_a - flux_b) / np.hypot(flux_err_a, flux_err_b)

def calculate_m_metric(flux_a: float, flux_b: float) -> float:
    """M metric: modulation index."""
    return 2 * ((flux_a - flux_b) / (flux_a + flux_b))

def pipeline_get_eta_metric(df: pd.DataFrame, peak: bool = False) -> float:
    """η metric: complementary to χ²."""
    weights = 1. / df[f'flux_{suffix}_err'].values**2
    fluxes = df[f'flux_{suffix}'].values
    eta = (df.shape[0] / (df.shape[0] - 1)) * (
        (weights * fluxes**2).mean() - (
            (weights * fluxes).mean()**2 / weights.mean()
        )
    )
    return eta
```

**Recommendation:** Copy these functions directly (pure functions, well-tested)

### 6.3 Light Curve Plotting (VAST Reference)

**From `vasttools/source.py::Source.plot_lightcurve()`:**

**Key Features:**
- Error bars and upper limits
- Multiple time axes
- Frequency grouping
- Forced photometry integration

**Adaptation for DSA-110:**
- Use normalized flux (from differential photometry)
- Add baseline period highlighting (first 10 epochs)
- Add ESE candidate period highlighting (14-180 days)
- Integrate with `photometry_timeseries` table

---

## 7. Summary

### 7.1 Mosaic Creation

**VAST Approach:**
- Linear mosaicking with PB weighting
- immath/imcombine tools
- Sault weighting scheme
- Common resolution convolution

**DSA-110 Status:** ✅ **Excellent alignment**
- Same weighting scheme (PB²/σ²)
- Proper regridding to common coordinate system
- Comprehensive validation
- Well-implemented

### 7.2 Image/Mosaic Analysis

**VAST Approach:**
- Selavy source finding
- Multi-metric variability analysis
- Light curve construction
- Transient detection

**DSA-110 Status:** 🟡 **Good, with enhancement opportunities**
- Forced photometry (appropriate for ESE detection)
- Basic variability metrics (χ², V)
- Missing: η metric, two-epoch metrics, light curve visualization

**Recommendations:**
1. **High Priority**: Add η metric, Vs/M metrics, light curve plotting
2. **Medium Priority**: Mosaic analysis tools, source finding integration
3. **Low Priority**: Background estimation, quality metrics visualization

### 7.3 Key Takeaways

**Mosaic Creation:**
- ✅ DSA-110's approach matches VAST's best practices
- ✅ Sault weighting correctly implemented
- ✅ Proper validation and quality metrics

**Image/Mosaic Analysis:**
- ✅ DSA-110's forced photometry approach is appropriate for ESE detection
- ⚠️ Could benefit from additional variability metrics (η, Vs, M)
- ⚠️ Light curve visualization would enhance ESE candidate review
- 💡 VAST's analysis patterns provide good reference for enhancements

**Science Goals:**
- VAST: Transient detection (discovery-oriented)
- DSA-110: ESE detection (monitoring-oriented)
- Both approaches are valid for their respective goals

---

## 8. References

### 8.1 VAST Pipeline

- **Documentation:** https://vast-survey.org/vast-pipeline/
- **VAST Tools:** https://github.com/askap-vast/vast-tools
- **VAST Pipeline GitHub:** https://github.com/askap-vast/vast-pipeline

### 8.2 Scientific References

- **Mooley et al. (2016):** Variability metrics (Vs, M, η)
  - DOI: 10.3847/0004-637X/818/2/105
- **Sault et al. (1996):** Mosaicking weighting scheme
  - Primary beam weighting for optimal SNR

### 8.3 DSA-110 Documentation

- **Mosaic CLI:** `src/dsa110_contimg/mosaic/cli.py`
- **Streaming Mosaic:** `src/dsa110_contimg/mosaic/streaming_mosaic.py`
- **Photometry:** `src/dsa110_contimg/photometry/`

---

**Last Updated:** 2025-01-XX

