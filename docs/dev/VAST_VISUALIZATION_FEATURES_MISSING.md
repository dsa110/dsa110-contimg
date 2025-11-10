# VAST Tools Visualization Features Not Yet Adopted

## Overview

This document identifies visualization features and settings used by VAST Tools that are not currently implemented in DSA-110.

## Missing Features

### 1. Colormap Choice: `gray_r` vs `viridis`/`inferno`

**VAST Tools:**
- Uses `gray_r` (grayscale reversed) for postage stamp cutouts
- Provides better contrast for radio astronomy images
- Standard for astronomical cutouts

**DSA-110:**
- Uses `viridis`/`inferno` for cutouts
- Uses `inferno` for mosaic PNGs

**Recommendation:** Make colormap configurable, default to `gray_r` for cutouts to match VAST Tools standard.

### 2. Data Scaling: mJy Conversion

**VAST Tools:**
- Multiplies cutout data by `1.e3` (converts Jy to mJy) for display
- Example: `cutout_row.data * 1.e3`
- Provides better numerical precision for display

**DSA-110:**
- Displays data in original units (Jy/beam)
- No unit conversion for display

**Recommendation:** Add optional mJy conversion for display (configurable).

### 3. Shared Normalization Across Cutouts

**VAST Tools:**
- `disable_autoscaling` parameter (default: `False`)
- When `False`: Uses shared normalization from first detection across all cutouts
- Ensures consistent brightness/contrast across epochs
- Critical for comparing variability visually

**DSA-110:**
- Currently creates normalization per cutout
- No shared normalization option

**Status:** ⚠️ **IMPORTANT** - This affects visual comparison of variability

**Recommendation:** Implement shared normalization option for `show_all_cutouts()`.

### 4. Contrast Parameter Defaults

**VAST Tools:**
- `show_all_png_cutouts()`: `contrast=0.1` (default)
- `show_png_cutout()`: `contrast=0.2` (default)
- Lower contrast for grid view (better for multiple images)

**DSA-110:**
- Uses `contrast=0.2` for all cases

**Recommendation:** Use `contrast=0.1` for grid views (`show_all_cutouts`).

### 5. Offset Axes for Postage Stamps

**VAST Tools:**
- `offset_axes` parameter (default: `True`)
- Offsets coordinate axes to avoid overlapping with image
- Uses `offset_postagestamp_axes()` utility function

**DSA-110:**
- No offset axes feature
- Axes may overlap with image content

**Recommendation:** Add offset axes option (low priority).

### 6. Overlay Features

**VAST Tools:**
- **Selavy overlay**: Overlays source detection components
- **Crossmatch overlay**: Overlays crossmatched catalog sources
- Uses `filter_selavy_components()` and `read_selavy()` utilities

**DSA-110:**
- No overlay features
- No source detection overlay
- No catalog crossmatch overlay

**Recommendation:** Add overlay features for source verification (medium priority).

### 7. Percentile Default

**VAST Tools:**
- Uses `percentile=99.9` (default) for normalization

**DSA-110:**
- Uses `percentile=99.5` in some places
- Uses `percentile=99.9` in postage stamps (matches VAST)

**Recommendation:** Standardize to `99.9` everywhere.

### 8. Stretch Function Options

**VAST Tools:**
- Uses `LinearStretch()` with `PercentileInterval` (when not using ZScale)
- Uses `AsinhStretch()` with `ZScaleInterval` (when using ZScale)

**DSA-110:**
- Uses `AsinhStretch()` with both ZScale and percentile
- More consistent approach

**Status:** ✓ Our approach is actually better (more consistent)

## Priority Recommendations

### High Priority

1. **Shared Normalization** (`disable_autoscaling=False`)
   - Critical for visual variability comparison
   - Ensures consistent brightness across epochs
   - **Impact:** High - affects scientific interpretation

2. **Colormap: `gray_r` for cutouts**
   - Standard for astronomical cutouts
   - Better contrast for radio images
   - **Impact:** Medium - visual quality improvement

### Medium Priority

3. **Contrast: 0.1 for grid views**
   - Better for multiple images
   - Matches VAST Tools standard
   - **Impact:** Low-Medium - visual quality improvement

4. **Percentile: Standardize to 99.9**
   - Consistency with VAST Tools
   - **Impact:** Low - minor improvement

### Low Priority

5. **mJy conversion for display**
   - Better numerical precision
   - **Impact:** Low - convenience feature

6. **Offset axes**
   - Avoids overlap with image
   - **Impact:** Low - visual polish

7. **Overlay features**
   - Source detection overlay
   - Catalog crossmatch overlay
   - **Impact:** Medium - useful for verification, but requires additional dependencies

## Implementation Notes

### Shared Normalization Implementation

```python
# In show_all_cutouts()
if not disable_autoscaling:
    # Use first detection for normalization
    first_data = None
    shared_norm = None
    
    for idx, (_, row) in enumerate(valid_measurements.iterrows()):
        if idx == 0:
            # Create normalization from first cutout
            shared_norm = normalize_cutout(first_cutout_data, ...)
            first_data = first_cutout_data
        
        # Use shared normalization for all cutouts
        plot_cutout(..., normalize=shared_norm)
else:
    # Create normalization per cutout (current behavior)
    for idx, (_, row) in enumerate(valid_measurements.iterrows()):
        norm = normalize_cutout(cutout_data, ...)
        plot_cutout(..., normalize=norm)
```

### Colormap Configuration

```python
# Add to function signatures
cmap: str = 'gray_r'  # Default for cutouts
# Or make it configurable:
# - 'gray_r' for cutouts (VAST standard)
# - 'viridis'/'inferno' for mosaics (current)
```

## Summary

**Most Important Missing Feature:** Shared normalization (`disable_autoscaling=False`)

This is critical for visual variability analysis - without it, brightness differences between epochs may be due to normalization differences rather than actual flux changes.

**Quick Wins:**
1. Change default colormap to `gray_r` for cutouts
2. Use `contrast=0.1` for grid views
3. Standardize percentile to `99.9`

## References

- VAST Tools: `archive/references/vast-tools/vasttools/source.py`
- DSA-110: `src/dsa110_contimg/qa/postage_stamps.py`
- DSA-110: `src/dsa110_contimg/imaging/export.py`

