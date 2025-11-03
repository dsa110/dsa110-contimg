# Professional Radio Astronomy Pipeline Review: End-to-End Through Mosaicking

**Date:** 2025-11-02  
**Reviewer:** Professional Radio Astronomer & Software Developer (with Perplexity co-analysis)  
**Scope:** Complete pipeline from HDF5 ingestion through mosaicking  
**Status:** COMPREHENSIVE REVIEW

## Executive Summary

This pipeline demonstrates solid engineering practices with comprehensive precondition checks, systematic calibration workflows, and thoughtful architecture. However, **critical gaps exist in the mosaicking stage** that could introduce systematic errors compromising scientific validity. The pipeline would benefit from enhanced validation, proper primary beam handling, and mosaic-specific quality control checks before image combination.

**Overall Assessment:** Good foundation, but mosaicking requires significant enhancements to meet professional standards.

---

## Strengths Identified

### 1. Precondition Checking Philosophy ("Measure Twice, Cut Once")
- ✅ Comprehensive validation at every pipeline stage
- ✅ Post-solve validation ensures calibration tables have solutions
- ✅ Post-applycal validation ensures CORRECTED_DATA is populated
- ✅ MS validation before imaging operations
- ✅ Disk space checks prevent partial failures

### 2. Calibration Workflow
- ✅ Proper K → BP → G calibration sequence
- ✅ MODEL_DATA population before K-calibration (critical fix implemented)
- ✅ Reference antenna validation with outrigger fallback
- ✅ Calibration table compatibility checks
- ✅ Post-solve validation prevents proceeding with failed solutions

### 3. Conversion Pipeline
- ✅ Phase coherence fix for direct-subband conversion
- ✅ File existence/readability validation before processing
- ✅ Disk space checks prevent partial MS creation
- ✅ MS write validation after creation

### 4. Imaging Implementation
- ✅ Primary beam correction enabled (`pbcor=True`)
- ✅ Wide-field gridding support (wproject/wgridder)
- ✅ NVSS model seeding for guided deconvolution
- ✅ CORRECTED_DATA detection and fallback to DATA

---

## Critical Issues Identified

### 🔴 CRITICAL: Inadequate Mosaicking Validation

**Issue:** The mosaic builder (`mosaic/cli.py`) performs minimal validation before combining images.

**Current Implementation:**
```python
def _check_consistent_tiles(tiles: List[str]) -> Tuple[bool, Optional[str]]:
    # Only checks: shape, cdelt1, cdelt2 consistency
    # Does NOT check:
    # - Primary beam correction status
    # - Calibration quality
    # - Astrometric registration
    # - Image quality metrics
    # - Weighting consistency
```

**Professional Requirement:**
Before combining images into a mosaic, the following checks should be performed:

1. **Primary Beam Correction Verification**
   - Verify all images are primary-beam corrected (`.pbcor` images)
   - Check that primary beam models are consistent across tiles
   - Verify primary beam correction was applied correctly (not double-corrected)

2. **Calibration Quality Verification**
   - Verify all tiles were calibrated with consistent calibration tables
   - Check that calibration solutions are within expected ranges
   - Verify flux density scale consistency across tiles

3. **Astrometric Registration Verification**
   - Check for systematic pointing errors between tiles
   - Verify WCS alignment is consistent
   - Detect any coordinate system misregistrations

4. **Image Quality Metrics**
   - Measure RMS noise in empty regions for each tile
   - Compute dynamic range for each tile
   - Check for artifacts (negative bowls, stripes, rings)
   - Verify synthesized beam consistency

5. **Weighting Consistency**
   - Verify weights scale appropriately with sensitivity
   - Check for unexpected weight variations between tiles
   - Verify primary beam weighting is correctly applied

**Impact:** Without these checks, systematic errors can propagate into the final mosaic, compromising:
- Flux density accuracy (errors >10% possible)
- Astrometric accuracy (arcsecond-level errors)
- Spectral index measurements (artifacts from beam variations)
- Source detection completeness (seam effects)

**Evidence from Perplexity Research:**
- Systematic pointing errors are ~10x more damaging than random errors
- Primary beam correction errors can cause 40% flux errors at beam edges
- Calibration inconsistencies can limit dynamic range to <100:1
- Missing astrometric checks can cause arcsecond-level position errors

### 🔴 CRITICAL: Simple Mean Combination Without Proper Weighting

**Issue:** Current mosaic builder uses simple arithmetic mean:
```python
expr = f"({'+'.join([f'IM{i}' for i in range(len(tiles))])})/{len(tiles)}"
```

**Professional Requirement:**
Mosaics should use **primary beam-weighted combination** that accounts for:
1. Individual tile sensitivities (system temperature, integration time)
2. Primary beam response at each pixel location
3. Noise variance weighting

**Correct Approach:**
```python
# Weight each tile by: 1 / (noise_variance * primary_beam_response^2)
# For each pixel (i,j):
#   mosaic[i,j] = sum(weight[k] * tile[k][i,j]) / sum(weight[k])
# where weight[k] = pb_response[k][i,j]^2 / noise_variance[k]
```

**Impact:** 
- Simple mean produces suboptimal noise characteristics
- Doesn't account for varying sensitivity across tiles
- Creates systematic flux errors at mosaic edges
- Fails to properly weight overlapping regions

**Evidence from Perplexity Research:**
- Sault weighting scheme is standard for professional mosaics
- Proper weighting can improve sensitivity by factors of 2-3
- Simple mean introduces systematic errors at overlapping regions

### 🔴 CRITICAL: No Primary Beam Pattern Verification

**Issue:** No verification that primary beam models are consistent or correct.

**Missing Checks:**
- Are primary beam models frequency-dependent? (Critical for wideband)
- Are beam models consistent across tiles?
- Do beam models match empirical measurements?
- Are far sidelobe effects accounted for?

**Impact:**
- Frequency-dependent beam variations can introduce spurious spectral indices
- Inconsistent beam models cause flux errors at mosaic edges
- Missing beam verification can cause 10-40% flux errors

**Evidence from Perplexity Research:**
- Primary beam solid angle scales as Ω_B ∝ ν^-2
- Wideband mosaics require frequency-weighted beam averaging
- Beam model errors cause systematic flux errors, especially at edges

### 🔴 CRITICAL: No Astrometric Registration Checks

**Issue:** No verification that tiles are properly aligned before combination.

**Missing Checks:**
- Compare source positions with catalog positions
- Detect systematic pointing offsets between tiles
- Verify WCS coordinate system consistency
- Check for frequency-dependent or time-dependent pointing variations

**Impact:**
- Systematic pointing errors cause misalignment artifacts
- Position errors propagate to multi-wavelength cross-matching
- Proper motion measurements become unreliable

**Evidence from Perplexity Research:**
- Systematic pointing errors are ~10x more damaging than random errors
- Even 1 arcsecond pointing errors limit dynamic range to <1000:1
- Astrometric errors can exceed several arcseconds without correction

---

## Medium Priority Issues

### ⚠️ MEDIUM: No Image Quality Metrics Before Mosaicking

**Missing Checks:**
- RMS noise measurement in empty regions
- Dynamic range calculation per tile
- Artifact detection (negative bowls, stripes, rings)
- Synthesized beam consistency verification

**Impact:** Poor-quality tiles can degrade entire mosaic quality.

### ⚠️ MEDIUM: No Calibration Consistency Verification

**Missing Checks:**
- Verify calibration tables used are consistent across tiles
- Check calibration solution quality metrics
- Verify flux density scale consistency
- Detect calibration outliers

**Impact:** Inconsistent calibration introduces systematic flux errors.

### ⚠️ MEDIUM: No Weighting Scheme Validation

**Missing Checks:**
- Verify weights scale appropriately with sensitivity
- Check for unexpected weight variations
- Verify primary beam weighting implementation

**Impact:** Improper weighting degrades sensitivity and introduces artifacts.

---

## Low Priority Issues

### ℹ️ LOW: Limited Error Handling in Mosaic Builder

**Current:** Basic try/except catches all errors generically.

**Recommendation:** More granular error handling with specific checks for:
- CASA imhead failures
- Image file corruption
- Missing primary beam images
- Incompatible image formats

### ℹ️ LOW: No Documentation of Mosaic Metadata

**Missing:** Documentation of:
- Which tiles contributed to each pixel
- Effective integration time per pixel
- Primary beam response per pixel
- Noise variance per pixel

**Recommendation:** Generate mosaic metadata image showing effective sensitivity map.

---

## Recommendations

### Priority 1: Implement Pre-Mosaicking Validation

**Action Items:**
1. Add `_validate_tile_quality()` function checking:
   - Primary beam correction status
   - RMS noise levels
   - Dynamic range
   - Artifact detection
   - Calibration consistency

2. Add `_verify_astrometric_registration()` function:
   - Compare source positions with catalog
   - Detect systematic offsets
   - Verify WCS consistency

3. Add `_check_primary_beam_consistency()` function:
   - Verify beam models are consistent
   - Check frequency-dependent effects
   - Validate beam correction application

### Priority 2: Implement Proper Weighted Mosaic Combination

**Action Items:**
1. Replace simple mean with primary beam-weighted combination
2. Read primary beam images for each tile
3. Compute proper weights accounting for:
   - Primary beam response
   - Noise variance
   - Integration time

4. Implement Sault weighting scheme or equivalent

### Priority 3: Add Mosaic Quality Metrics

**Action Items:**
1. Generate mosaic metadata image showing:
   - Effective integration time per pixel
   - Primary beam response per pixel
   - Noise variance per pixel
   - Number of tiles contributing per pixel

2. Compute mosaic-wide quality metrics:
   - RMS noise map
   - Dynamic range map
   - Sensitivity variations

### Priority 4: Enhanced Documentation

**Action Items:**
1. Document mosaic combination methodology
2. Document primary beam handling
3. Document any limitations or known issues
4. Provide usage examples with quality checks

---

## Specific Code Recommendations

### 1. Enhanced Tile Validation

```python
def _validate_tile_quality(tile_path: str, products_db: Path) -> Dict[str, Any]:
    """Validate tile quality before mosaicking.
    
    Returns:
        dict with quality metrics and validation flags
    """
    metrics = {}
    
    # Check primary beam correction
    pbcor_path = tile_path.replace('.image', '.pbcor')
    if not os.path.exists(pbcor_path):
        raise ValueError(f"Primary beam corrected image not found: {pbcor_path}")
    
    # Read calibration info from products DB
    # Check RMS noise
    # Check dynamic range
    # Check for artifacts
    
    return metrics
```

### 2. Proper Weighted Combination

```python
def _build_weighted_mosaic(tiles: List[str], pb_images: List[str], 
                          noise_vars: List[float]) -> str:
    """Build mosaic using proper primary beam weighting."""
    
    # For each pixel:
    #   weight[i] = pb_response[i]^2 / noise_var[i]
    #   mosaic = sum(weight[i] * tile[i]) / sum(weight[i])
    
    # Use CASA immath with proper weighting expression
    pass
```

### 3. Astrometric Registration Check

```python
def _verify_astrometric_registration(tiles: List[str], 
                                    catalog_path: Optional[str] = None) -> List[float]:
    """Verify tiles are properly registered.
    
    Returns:
        List of offset corrections (ra_offset, dec_offset) per tile
    """
    # Compare source positions with catalog
    # Detect systematic offsets
    # Return correction offsets
    pass
```

---

## Comparison with Professional Standards

### VLASS SE Continuum Pipeline (Reference)
- ✅ Comprehensive pre-combination quality checks
- ✅ Primary beam-weighted combination
- ✅ Astrometric registration verification
- ✅ Calibration consistency checks
- ✅ Dynamic range verification
- ✅ Artifact detection and flagging

**Our Pipeline:**
- ❌ Minimal pre-combination checks
- ❌ Simple mean combination (not weighted)
- ❌ No astrometric verification
- ❌ No calibration consistency checks
- ❌ No quality metrics computation

**Gap Analysis:** Our pipeline lacks ~80% of standard pre-combination validation.

---

## Conclusion

The DSA-110 continuum imaging pipeline demonstrates **excellent engineering practices** in the conversion, calibration, and imaging stages. The "measure twice, cut once" philosophy is well-implemented throughout these stages.

However, the **mosaicking stage requires significant enhancement** to meet professional radio astronomy standards. The current implementation is too simplistic and lacks critical validation steps that could introduce systematic errors compromising scientific validity.

**Recommended Action:** Prioritize implementation of pre-mosaicking validation and proper weighted combination before using mosaics for scientific analysis.

**Estimated Effort:** 
- Priority 1 fixes: 2-3 weeks
- Priority 2 fixes: 1-2 weeks  
- Priority 3 fixes: 1 week
- Priority 4 fixes: 1 week

**Total:** ~5-7 weeks to bring mosaicking to professional standards.

---

## References

1. Perplexity Research: "Critical Issues in Radio Astronomy Mosaicking"
2. VLASS SE Continuum Users Guide: https://science.nrao.edu/vlass/vlass-se-continuum-users-guide
3. NRAO VLA Mosaicking Guide: https://science.nrao.edu/facilities/vla/docs/manuals/obsguide/modes/mosaicking
4. CASA Mosaicking Documentation: https://casa.nrao.edu/aips2_docs/cookbook/cbvol2/node5.html

