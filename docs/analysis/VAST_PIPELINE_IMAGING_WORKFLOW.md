# VAST Pipeline Imaging Workflow Analysis

**Date:** 2025-01-XX  
**Purpose:** Analysis of VAST Pipeline imaging workflow as reference for DSA-110 pipeline development  
**Reference:** VAST Pipeline (https://vast-survey.org/vast-pipeline/)  
**Source:** Perplexity search results + VAST Tools codebase analysis

---

## Executive Summary

The VAST (Variables and Slow Transients) Pipeline is a production-grade transient detection pipeline for ASKAP data. This document analyzes VAST's imaging workflow, parameters, and strategies to inform DSA-110's ESE detection pipeline development.

**Key Findings:**
- VAST uses both **tclean** (CASA) and **WSClean** for imaging
- Two-tier imaging strategy: **deep continuum** + **snapshot transient** imaging
- Model subtraction workflow for transient detection
- Optimized parameters for speed vs. quality trade-offs
- Primary beam correction and source finding integration

---

## 1. VAST Pipeline Architecture Overview

### 1.1 High-Level Workflow

```
Raw ASKAP Data (36 beams)
    ↓
ASKAPsoft Pipeline (Pawsey)
    ├─ Calibration
    ├─ RFI Flagging
    └─ Initial Imaging
    ↓
VAST Pipeline
    ├─ Data Ingest
    ├─ Phase Centre Fixing
    ├─ Deep Sky Model Creation
    ├─ Model Subtraction
    ├─ Snapshot Imaging (transients)
    ├─ Background/Noise Estimation
    ├─ Source Finding (Selavy)
    ├─ Light Curve Generation
    └─ Variability/Transient Detection
```

### 1.2 Key Components

**Data Processing:**
- Processes 36 ASKAP beams independently
- Handles calibrated visibility data
- Fixes observation phase centres
- Creates deep sky models for subtraction

**Imaging Strategy:**
- **Deep Continuum Imaging**: High-quality images for source cataloging
- **Snapshot Imaging**: Fast, short-timescale images for transient detection
- **Model Subtraction**: Removes known sources to enhance transient sensitivity

**Source Detection:**
- Uses **Selavy** for source finding
- Creates light curves from measurements
- Identifies variable/transient candidates

---

## 2. Imaging Tools and Parameters

### 2.1 tclean (CASA) - Primary Tool

**Purpose:** Both deep continuum and transient snapshot imaging

#### Key Parameters

**Image Geometry:**
- `imsize`: Image size in pixels (varies by use case)
- `cell`: Angular pixel size (e.g., 10 arcsec)
- `uvrange`: UV range to image (e.g., '100~10000m')

**Gridding:**
- `gridder`: Type of gridder
  - `'standard'`: Fast, less accurate (for quick snapshots)
  - `'widefield'`: Spatially accurate (for deep imaging)
- `wprojplanes`: Number of w-planes for W-projection
  - `-1`: Automatic (for widefield)
  - `1`: No projection (for standard, faster)

**Imaging Mode:**
- `specmode`: `'mfs'` (multi-frequency synthesis) for continuum
- `specmode`: `'cube'` for spectral cubes

**Deconvolution:**
- `niter`: Number of cleaning iterations
- `threshold`: Cleaning threshold (e.g., '4mJy')
- `deconvolver`: Algorithm (e.g., 'hogbom', 'multiscale')

**Weighting:**
- `weighting`: Weighting scheme (`'briggs'`, `'natural'`, `'uniform'`)
- `robust`: Robustness parameter for Briggs weighting (typically 0-0.5)

**Primary Beam:**
- `pbcor`: Apply primary beam correction (True/False)

#### Example Configurations

**Deep Continuum Imaging:**
```python
tclean_params = {
    'imsize': [4096, 4096],
    'cell': '10arcsec',
    'uvrange': '100~10000m',
    'gridder': 'widefield',
    'wprojplanes': -1,
    'specmode': 'mfs',
    'niter': 10000,
    'threshold': '4mJy',
    'weighting': 'briggs',
    'robust': 0.0,
    'pbcor': True
}
```

**Transient Snapshot Imaging:**
```python
tclean_params = {
    'imsize': [2048, 2048],
    'cell': '10arcsec',
    'uvrange': '100~10000m',
    'gridder': 'standard',  # Faster
    'wprojplanes': 1,        # No projection
    'specmode': 'mfs',
    'niter': 1000,          # Fewer iterations
    'threshold': '10mJy',   # Higher threshold
    'weighting': 'briggs',
    'robust': 0.0,
    'pbcor': True
}
```

### 2.2 WSClean - Alternative Tool

**Purpose:** Efficient imaging for large datasets and cubes

#### Key Parameters

**Image Geometry:**
- `size`: Image size in pixels
- `scale`: Pixel scale (e.g., '10asec')

**Weighting:**
- `weighting`: Weighting scheme (`'briggs'`, `'uniform'`)

**Deconvolution:**
- `niter`: Number of cleaning iterations
- `threshold`: Cleaning threshold
- `auto-threshold`: Automatic thresholding
- `multiscale`: Use multiscale cleaning

**Masking:**
- `fits-mask`: Use a mask for cleaning

**Spectral Cubes:**
- `channels-out`: Number of output channels

**Output:**
- `name`: Output file name

#### Advantages

- **Speed**: 2-5x faster than tclean for large datasets
- **Memory**: More efficient memory usage
- **Cubes**: Better support for spectral cubes

#### Limitations

- Less flexible than tclean
- Fewer advanced features
- May require post-processing for some operations

---

## 3. VAST Imaging Workflow Details

### 3.1 Deep Continuum Imaging

**Purpose:** Create high-quality reference images for source cataloging

**Workflow:**
1. Combine all available data for a field
2. Use widefield gridding with W-projection
3. Deep cleaning (high niter, low threshold)
4. Primary beam correction
5. Source finding with Selavy
6. Create source catalog

**Key Characteristics:**
- High image quality
- Low noise
- Complete source catalog
- Used as reference for model subtraction

### 3.2 Snapshot Transient Imaging

**Purpose:** Fast imaging for transient detection on short timescales

**Workflow:**
1. Use short time intervals (e.g., 10 seconds)
2. Standard gridding (faster)
3. Shallow cleaning (lower niter, higher threshold)
4. Primary beam correction
5. Background/noise estimation
6. Source finding
7. Compare to deep model

**Key Characteristics:**
- Fast processing
- Optimized for speed vs. quality
- Suitable for real-time transient detection

### 3.3 Model Subtraction Workflow

**Purpose:** Enhance transient sensitivity by removing known sources

**Workflow:**
1. Create deep sky model from continuum imaging
2. Subtract model from visibility data
3. Image residual visibilities
4. Detect new/transient sources in residuals

**Benefits:**
- Reduces confusion from bright sources
- Enhances sensitivity to faint transients
- Enables detection of sources below confusion limit

---

## 4. Parameter Optimization Strategies

### 4.1 Speed vs. Quality Trade-offs

**For Speed (Transient Detection):**
- `gridder='standard'` (vs. 'widefield')
- `wprojplanes=1` (vs. -1)
- Lower `niter` (1000 vs. 10000)
- Higher `threshold` (10mJy vs. 4mJy)
- Smaller `imsize` (2048 vs. 4096)

**For Quality (Deep Imaging):**
- `gridder='widefield'` (vs. 'standard')
- `wprojplanes=-1` (automatic)
- Higher `niter` (10000+)
- Lower `threshold` (4mJy or lower)
- Larger `imsize` (4096+)

### 4.2 UV Range Selection

**Typical Ranges:**
- `'100~10000m'`: Standard range (removes very short/long baselines)
- `'>100m'`: Include all baselines above 100m
- `'<10000m'`: Include all baselines below 10000m

**Considerations:**
- Short baselines: Extended structure, low resolution
- Long baselines: High resolution, may miss extended sources
- DSA-110: Max baseline ~2.6 km (much shorter than ASKAP)

### 4.3 Weighting Schemes

**Briggs Weighting:**
- `robust=0.0`: Natural weighting (best sensitivity)
- `robust=0.5`: Balanced (good compromise)
- `robust=1.0`: Uniform weighting (best resolution)

**Natural Weighting:**
- Best sensitivity
- Poor resolution
- Good for faint sources

**Uniform Weighting:**
- Best resolution
- Poor sensitivity
- Good for bright, compact sources

---

## 5. DSA-110 Comparison and Adaptation

### 5.1 Key Differences

| Aspect | VAST (ASKAP) | DSA-110 |
|--------|--------------|---------|
| **Array** | 36 dishes, ~6 km max baseline | 110 stations, ~2.6 km max baseline |
| **Beams** | 36 independent beams | Single pointing |
| **Science Goal** | Transient detection | ESE detection (slow variability) |
| **Timescales** | Minutes to days | Weeks to months |
| **Imaging Frequency** | Frequent snapshots | Periodic epochs |
| **UV Range** | 100~10000m | Much shorter baselines |

### 5.2 Relevant Patterns for DSA-110

**1. Two-Tier Imaging Strategy**
- **Deep Imaging**: High-quality reference images (like VAST's deep continuum)
- **Quick Imaging**: Fast, periodic imaging for ESE monitoring (like VAST's snapshots, but slower cadence)

**2. Model Subtraction**
- Not directly applicable (ESEs are flux variations, not new sources)
- But could use for removing bright sources to enhance sensitivity

**3. Primary Beam Correction**
- **Critical** for DSA-110 (already implemented)
- VAST's approach validates DSA-110's implementation

**4. Source Finding Integration**
- VAST uses Selavy for source finding
- DSA-110 uses forced photometry (different approach, but similar goal)

**5. Parameter Optimization**
- VAST's speed vs. quality trade-offs are relevant
- DSA-110's "quick" mode aligns with VAST's snapshot imaging approach

### 5.3 Adaptation Recommendations

**For DSA-110 ESE Detection:**

**1. Deep Reference Imaging (Periodic)**
```python
# Similar to VAST's deep continuum imaging
deep_params = {
    'gridder': 'wproject',      # DSA-110 uses wproject
    'wprojplanes': -1,          # Automatic
    'niter': 10000,
    'threshold': '4mJy',
    'weighting': 'briggs',
    'robust': 0.0,
    'pbcor': True
}
```

**2. Quick Monitoring Imaging (Frequent)**
```python
# Similar to VAST's snapshot imaging
quick_params = {
    'gridder': 'wproject',
    'wprojplanes': -1,          # Still use wproject for accuracy
    'niter': 300,               # Fewer iterations
    'threshold': '10mJy',       # Higher threshold
    'weighting': 'briggs',
    'robust': 0.0,
    'pbcor': True
}
```

**3. WSClean Consideration**
- DSA-110 already uses WSClean as default backend
- VAST's WSClean usage validates this choice
- Consider optimizing WSClean parameters further

---

## 6. VAST Pipeline Output Structure

### 6.1 Image Products

**From VAST Tools Analysis:**
- Images stored as FITS files
- RMS images (background noise)
- Background images (sky background)
- Primary beam corrected images
- Both "TILES" (individual beams) and "COMBINED" (mosaicked) images

### 6.2 Pipeline Outputs (Parquet Files)

**From VAST Tools `PipeRun` class:**
- `images.parquet`: Image metadata (path, beam, noise, etc.)
- `measurements.parquet`: Source measurements (flux, errors, dates)
- `sources.parquet`: Aggregated source information
- `associations.parquet`: Source associations across epochs
- `relations.parquet`: Source relationships
- `skyregions.parquet`: Sky region information
- `bands.parquet`: Frequency band information

**DSA-110 Comparison:**
- DSA-110 uses SQLite (`products.sqlite3`) instead of Parquet
- Similar structure: `images` table, `photometry_timeseries` table
- DSA-110's approach is more database-centric

---

## 7. Key Lessons and Best Practices

### 7.1 Imaging Strategy

**1. Two-Tier Approach**
- Deep imaging for reference catalogs
- Quick imaging for monitoring
- Balance speed vs. quality based on use case

**2. Parameter Optimization**
- Use faster parameters for frequent imaging
- Use quality parameters for reference imaging
- Document parameter choices and trade-offs

**3. Primary Beam Correction**
- Always apply for accurate flux measurements
- Critical for variability studies

### 7.2 Workflow Integration

**1. Source Finding**
- Integrate source finding with imaging
- Use catalogs for forced photometry
- Track sources across epochs

**2. Quality Assurance**
- Background/noise estimation
- Image quality metrics
- Validation against catalogs

**3. Data Products**
- Consistent naming conventions
- Metadata tracking
- Database integration

---

## 8. References

### 8.1 VAST Pipeline

- **Documentation:** https://vast-survey.org/vast-pipeline/
- **GitHub:** https://github.com/askap-vast/vast-pipeline
- **VAST Tools:** https://github.com/askap-vast/vast-tools

### 8.2 Imaging Tools

- **CASA tclean:** https://casadocs.readthedocs.io/en/stable/api/tt/casatasks.imaging.tclean.html
- **WSClean:** https://gitlab.com/aroffringa/wsclean

### 8.3 Scientific References

- **VAST Transient Detection:** Radio variable and transient sources on minute time-scales (2023)
  - DOI: 10.1093/mnras/stad1685
- **VAST Pipeline Paper:** (when available)

---

## 9. Recommendations for DSA-110

### 9.1 Immediate Actions

**1. Review Current Imaging Parameters**
- Compare DSA-110's current parameters to VAST's recommendations
- Identify optimization opportunities
- Document parameter choices

**2. Implement Two-Tier Strategy**
- Ensure "quick" mode uses optimized parameters
- Ensure "standard" mode uses quality parameters
- Document when to use each mode

**3. WSClean Optimization**
- Review WSClean parameters against VAST's usage
- Optimize for DSA-110's specific use case
- Benchmark performance improvements

### 9.2 Future Enhancements

**1. Model Subtraction (Optional)**
- Consider implementing for bright source removal
- May enhance sensitivity to faint ESEs
- Lower priority (ESEs are flux variations, not new sources)

**2. Background/Noise Estimation**
- Implement systematic background estimation
- Use for quality assurance
- Integrate with variability analysis

**3. Image Quality Metrics**
- Implement comprehensive quality metrics
- Track image quality over time
- Use for pipeline optimization

---

## 10. Conclusion

VAST Pipeline's imaging workflow provides valuable insights for DSA-110:

**Key Takeaways:**
1. **Two-tier imaging strategy** (deep + quick) is validated approach
2. **Parameter optimization** is critical for balancing speed vs. quality
3. **Primary beam correction** is essential (already implemented)
4. **WSClean** is a good choice for speed (already default)
5. **Source finding integration** is important (DSA-110 uses forced photometry)

**DSA-110 Alignment:**
- Current imaging approach aligns well with VAST's patterns
- Quick mode similar to VAST's snapshot imaging
- Standard mode similar to VAST's deep imaging
- Primary beam correction already implemented

**Next Steps:**
1. Review and optimize current imaging parameters
2. Document parameter choices and trade-offs
3. Benchmark performance against VAST's recommendations
4. Consider implementing additional quality metrics

---

**Last Updated:** 2025-01-XX

