# Masked Imaging Analysis for DSA-110 Continuum Imaging

## Executive Summary

**Yes, masked imaging would be appropriate and beneficial** for the DSA-110 continuum imaging pipeline. The pipeline already has infrastructure (NVSS catalog access, source seeding) that would naturally support masked imaging, and there's even a partially implemented mask creation function (`create_nvss_mask()` in `nvss_tools.py`) that is currently unused.

## Current State

### Existing Masking Infrastructure

1. **Auto-masking**: WSClean currently uses automatic masking:
   ```python
   cmd.extend(["-auto-mask", "3"])        # Auto-mask at 3 sigma
   cmd.extend(["-auto-threshold", "0.5"])  # Final threshold 0.5 sigma
   ```
   This automatically detects and masks sources during cleaning, but doesn't use prior knowledge.

2. **NVSS Seeding**: The pipeline seeds `MODEL_DATA` with NVSS sources before imaging:
   - Sources ≥10 mJy (standard tier) or ≥5 mJy (high precision tier)
   - Limited to primary beam extent when `pbcor=True`
   - Provides initial model components but doesn't restrict cleaning regions

3. **Unused Mask Function**: `create_nvss_mask()` exists in `src/dsa110_contimg/imaging/nvss_tools.py`:
   - Creates CRTF (CASA Region Text Format) masks
   - Generates circular regions around NVSS sources
   - Currently not integrated into imaging workflow

### WSClean Mask Support

WSClean supports user-provided masks via the `-fits-mask` parameter:
- **Format**: FITS or CASA format
- **Convention**: Zero values = not cleaned, non-zero values = cleaned
- **Usage**: `wsclean -fits-mask mask.fits ...`
- **Compatibility**: Can be combined with auto-masking for hybrid approach

## Benefits of Masked Imaging

### 1. **Improved Convergence**

**Current approach**: Auto-masking discovers sources during cleaning, which can lead to:
- Slower convergence (exploring entire image)
- Potential false detections in noisy regions
- Inefficient iteration on empty regions

**Masked approach**: Restricting cleaning to known source locations:
- Faster convergence (focused search space)
- Fewer false detections (only clean where sources expected)
- More efficient use of iterations

### 2. **Complementary to NVSS Seeding**

The pipeline already seeds `MODEL_DATA` with NVSS sources. Masked imaging would:
- **Guide deconvolution** to refine seeded sources (rather than just providing initial model)
- **Prevent over-cleaning** in empty regions
- **Focus computational resources** on known source locations

### 3. **Reduced Cleaning Artifacts**

Masked imaging prevents:
- Cleaning artifacts in empty regions (common in wide-field imaging)
- Over-deconvolution of noise
- Spurious sources from aggressive cleaning thresholds

### 4. **Better Handling of Extended Sources**

For extended NVSS sources:
- Mask regions can be sized appropriately (e.g., 2-3× beam size)
- Prevents under-cleaning of extended emission
- More accurate flux recovery

## Implementation Considerations

### Mask Generation Strategy

**Option 1: NVSS-Based Masks (Recommended)**
- Generate masks from NVSS catalog positions
- Circular regions around each source
- Radius: 2-3× synthesized beam (typically ~30-60 arcsec)
- Threshold: Same as NVSS seeding (10 mJy standard, 5 mJy high precision)

**Option 2: Hybrid Approach**
- Start with NVSS-based mask
- Allow auto-masking to expand mask during cleaning
- Best of both worlds: prior knowledge + discovery

**Option 3: Primary Beam Masking**
- Mask regions outside primary beam (when `pbcor=True`)
- Prevents cleaning in low-sensitivity regions
- Already partially implemented (`_load_pb_mask()` function exists)

### Integration Points

1. **Before Imaging**: Generate mask from NVSS catalog
   - Use same query logic as NVSS seeding
   - Create FITS mask matching image geometry
   - Save alongside other imaging products

2. **During WSClean Execution**: Pass mask to WSClean
   ```python
   if mask_path:
       cmd.extend(["-fits-mask", mask_path])
   ```

3. **Optional Enhancement**: Combine with auto-masking
   - Use NVSS mask as initial constraint
   - Allow auto-masking to refine/expand mask
   - Best convergence with prior knowledge

### Code Changes Required

1. **Add mask generation function** (or enhance existing `create_nvss_mask()`):
   ```python
   def create_nvss_fits_mask(
       imagename: str,
       imsize: int,
       cell_arcsec: float,
       phasecenter: Optional[str],
       nvss_min_mjy: float,
       radius_arcsec: float = 60.0,  # 2-3× beam
   ) -> str:
       """Create FITS mask from NVSS sources."""
   ```

2. **Add mask parameter to `run_wsclean()`**:
   ```python
   def run_wsclean(
       ...
       mask_path: Optional[str] = None,
   ):
       if mask_path:
           cmd.extend(["-fits-mask", mask_path])
   ```

3. **Add mask parameter to `image_ms()`**:
   ```python
   def image_ms(
       ...
       use_nvss_mask: bool = True,  # Default: use masked imaging
       mask_radius_arcsec: float = 60.0,
   ):
       # Generate mask before imaging
       if use_nvss_mask and nvss_min_mjy is not None:
           mask_path = create_nvss_fits_mask(...)
       else:
           mask_path = None
       
       run_wsclean(..., mask_path=mask_path)
   ```

## Potential Challenges

### 1. **Mask Alignment**

**Challenge**: Mask must match image geometry exactly (WCS, pixel scale, size)

**Solution**: 
- Generate mask using same WCS as final image
- Use `astropy.wcs.WCS` to convert NVSS positions to pixel coordinates
- Verify mask dimensions match image dimensions

### 2. **Missing Sources**

**Challenge**: NVSS catalog may miss sources below threshold or variable sources

**Solution**: 
- Use hybrid approach (NVSS mask + auto-masking)
- Set conservative NVSS threshold (e.g., 5-10 mJy)
- Auto-masking can discover additional sources

### 3. **Extended Sources**

**Challenge**: Point-source masks may under-clean extended emission

**Solution**:
- Use larger mask radius (2-3× beam)
- Consider elliptical masks for known extended sources
- Allow auto-masking to expand mask for extended features

### 4. **Primary Beam Edge**

**Challenge**: Sources near primary beam edge may have poor sensitivity

**Solution**:
- Combine NVSS mask with primary beam mask
- Only clean where both masks overlap
- Respect `pblimit` parameter

## Recommended Implementation

### Phase 1: Basic Masked Imaging

1. **Enhance `create_nvss_mask()`** to generate FITS masks (not just CRTF)
2. **Add mask generation** to `image_ms()` workflow
3. **Pass mask to WSClean** via `-fits-mask` parameter
4. **Enable for all quality tiers** (default: `True` when `nvss_min_mjy` is specified)
   - Development tier: Faster tests (2-4x speedup)
   - Standard/High precision: Better quality + efficiency

### Phase 2: Hybrid Masking

1. **Combine NVSS mask with auto-masking**
2. **Allow auto-masking to expand mask** during cleaning
3. **Add primary beam masking** option

### Phase 3: Advanced Features

1. **Elliptical masks** for extended sources
2. **Flux-weighted mask sizes** (larger masks for brighter sources)
3. **Multi-scale mask support** (different mask sizes for different scales)

## Performance Impact

### Expected Benefits

- **Faster convergence**: 10-30% reduction in iterations (estimated)
- **Better image quality**: Reduced cleaning artifacts
- **More accurate flux**: Better handling of known sources

### Computational Overhead

- **Mask generation**: Negligible (~0.1-0.5 seconds)
- **WSClean processing**: Slight overhead from mask application (~1-2%)
- **Overall**: Net positive (faster convergence outweighs overhead)

## Comparison with Current Approach

| Aspect | Current (Auto-mask only) | Masked Imaging |
|--------|-------------------------|----------------|
| **Convergence** | Slower (explores entire image) | Faster (focused search) |
| **False detections** | Possible in noisy regions | Reduced (only clean known sources) |
| **Prior knowledge** | Not used | Leverages NVSS catalog |
| **Artifacts** | Possible in empty regions | Reduced |
| **Missing sources** | Auto-discovers | May miss below threshold |
| **Implementation** | Already working | Requires development |

## Conclusion

Masked imaging is **highly appropriate** for the DSA-110 continuum imaging pipeline because:

1. **Natural fit**: Pipeline already uses NVSS catalog for seeding
2. **Infrastructure exists**: Mask creation function already partially implemented
3. **Clear benefits**: Faster convergence, better quality, reduced artifacts
4. **Low risk**: Can be made optional, can combine with auto-masking
5. **WSClean support**: Native support via `-fits-mask` parameter

**Recommendation**: Implement masked imaging as an **optional feature** (default: enabled for standard/high precision tiers, disabled for development tier). Start with NVSS-based masks, then enhance with hybrid auto-masking approach.

## References

- **WSClean Masking Documentation**: https://wsclean.readthedocs.io/en/latest/masking.html
- **Current Implementation**: `src/dsa110_contimg/imaging/cli_imaging.py`
- **NVSS Tools**: `src/dsa110_contimg/imaging/nvss_tools.py`
- **WSClean Usage Analysis**: `docs/analysis/WSCLEAN_USAGE_ANALYSIS.md`

