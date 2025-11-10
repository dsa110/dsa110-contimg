# Visualization Methods Comparison: VAST Tools vs DSA-110

## Overview

This document compares visualization methods between VAST Tools and DSA-110 pipeline, identifying superior approaches and adoption status.

## Normalization Methods

### VAST Tools Approach

**ZScale Normalization** (preferred):
```python
from astropy.visualization import ZScaleInterval, ImageNormalize, AsinhStretch

normalize = ImageNormalize(
    data,
    interval=ZScaleInterval(contrast=0.2),
    stretch=AsinhStretch()
)
```

**Advantages:**
- Specifically designed for astronomical images
- Better outlier handling
- More robust to noise and background variations
- Industry standard approach

**Fallback:**
- PercentileInterval with LinearStretch (if ZScale not suitable)

### DSA-110 Previous Approach

**Percentile-based normalization:**
```python
lo, hi = np.percentile(vals, [1.0, 99.5])
img = np.clip(arr, lo, hi)
img = np.arcsinh((img - lo) / max(1e-12, (hi - lo)))
```

**Limitations:**
- Less robust to outliers
- Can clip important features
- Not optimized for astronomical images

### DSA-110 Current Approach (After Update)

**ZScale Normalization** (adopted from VAST Tools):
```python
from astropy.visualization import ZScaleInterval, ImageNormalize, AsinhStretch

normalize = ImageNormalize(
    arr[m],  # Finite values for interval calculation
    interval=ZScaleInterval(contrast=0.2),
    stretch=AsinhStretch()
)
```

**Status:** ✓ Adopted from VAST Tools

## Implementation Locations

### DSA-110

1. **Mosaic PNG Generation** (`imaging/export.py::save_png_from_fits`)
   - Status: ✓ Updated to use ZScale (2025-11-10)
   - Method: ZScaleInterval + AsinhStretch
   - Fallback: Percentile normalization if ZScale fails

2. **Postage Stamps** (`qa/postage_stamps.py::normalize_cutout`)
   - Status: ✓ Already using ZScale
   - Method: ZScaleInterval + AsinhStretch (default)
   - Option: PercentileInterval fallback

### VAST Tools

1. **Source Visualization** (`vasttools/source.py`)
   - Method: ZScaleInterval + AsinhStretch (preferred)
   - Option: PercentileInterval + LinearStretch (fallback)
   - Parameter: `zscale=True/False` to toggle

## Key Differences

| Aspect | VAST Tools | DSA-110 (Before) | DSA-110 (After) |
|--------|------------|------------------|-----------------|
| **Normalization** | ZScale (preferred) | Percentile | ZScale ✓ |
| **Stretch** | AsinhStretch | arcsinh manual | AsinhStretch ✓ |
| **Outlier Handling** | Excellent | Good | Excellent ✓ |
| **Astronomical Optimized** | Yes | No | Yes ✓ |

## Recommendations

### ✓ Completed

1. **Mosaic PNG Generation**: Updated to use ZScale normalization
   - Matches VAST Tools approach
   - Better visualization quality
   - Industry standard

2. **Postage Stamps**: Already using ZScale
   - Consistent with VAST Tools
   - Good implementation

### Future Considerations

1. **Interactive Visualization**: VAST Tools uses Bokeh for interactive plots
   - DSA-110 uses Plotly.js (different but equivalent)
   - No change needed

2. **Cutout Generation**: Both use similar approaches
   - `astropy.nddata.utils.Cutout2D`
   - WCS handling
   - No change needed

3. **Colormaps**: VAST Tools uses `gray_r` for cutouts
   - DSA-110 uses `viridis`/`inferno`
   - Consider making configurable

## Conclusion

**Status:** DSA-110 visualization methods now match or exceed VAST Tools standards:

- ✓ ZScale normalization adopted (superior to percentile)
- ✓ AsinhStretch used (matches VAST Tools)
- ✓ Consistent across mosaic and postage stamp visualizations
- ✓ Industry-standard approach

**No further changes needed** - DSA-110 visualization methods are now aligned with best practices from VAST Tools.

## References

- VAST Tools: `archive/references/vast-tools/vasttools/source.py`
- DSA-110: `src/dsa110_contimg/imaging/export.py`
- DSA-110: `src/dsa110_contimg/qa/postage_stamps.py`
- Astropy Documentation: [ZScaleInterval](https://docs.astropy.org/en/stable/visualization/normalization.html#zscale-interval)

