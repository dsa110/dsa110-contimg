# Forced Photometry Enhancements - Implementation Summary

## Overview

Successfully implemented all recommended enhancements from VAST forced_phot analysis:

1. ✅ **Cluster fitting** (high priority) - COMPLETE
2. ✅ **Chi-squared metric** (high priority) - COMPLETE  
3. ✅ **Optional noise maps** (medium priority) - COMPLETE
4. ✅ **Source injection** (medium priority) - COMPLETE

## Implementation Details

### 1. Enhanced `ForcedPhotometryResult` Dataclass

Added three new optional fields:
- `chisq: Optional[float]` - Chi-squared goodness-of-fit
- `dof: Optional[int]` - Degrees of freedom
- `cluster_id: Optional[int]` - Cluster ID if part of blended source group

### 2. Weighted Convolution (Condon 1997)

Implemented `_weighted_convolution()` function that calculates:
- Flux: `sum((data * kernel / noise²)) / sum(kernel² / noise²)`
- Flux error: `sum(noise * kernel / noise²) / sum(kernel / noise²)`
- Chi-squared: `sum(((data - kernel * flux) / noise)²)`

### 3. 2D Gaussian Kernel (`G2D` class)

- Generates 2D Gaussian kernels with FWHM and position angle
- Handles fractional pixel offsets correctly
- Uses E of N convention for position angle (matches VAST)

### 4. Cluster Fitting

- `_identify_clusters()`: Uses KDTree to identify sources within threshold
- `_measure_cluster()`: Simultaneously fits multiple sources using astropy `Gaussian2D` models
- Default threshold: 1.5 × BMAJ (validated by VAST)
- Requires `scipy` for KDTree (gracefully degrades if unavailable)

### 5. Enhanced `measure_forced_peak()`

New parameters:
- `noise_map_path: Optional[str]` - Path to noise map FITS file
- `background_map_path: Optional[str]` - Path to background map FITS file
- `nbeam: float = 3.0` - Size of cutout in units of beam major axis
- `use_weighted_convolution: bool = True` - Enable weighted convolution

**Behavior:**
- Uses weighted convolution when beam info (BMAJ, BMIN, BPA) is available
- Falls back to simple peak measurement if beam info missing
- Supports separate noise/background maps (more accurate)
- Falls back to annulus-based RMS if noise map not provided

### 6. Enhanced `measure_many()`

New parameters:
- `use_cluster_fitting: bool = False` - Enable cluster fitting
- `cluster_threshold: float = 1.5` - Cluster threshold in units of BMAJ
- `noise_map_path: Optional[str]` - Path to noise map FITS file
- `background_map_path: Optional[str]` - Path to background map FITS file
- `nbeam: float = 3.0` - Size of cutout in units of beam major axis

**Behavior:**
- Loads data once for efficiency
- Identifies clusters using KDTree
- Measures individual sources separately
- Measures clusters using simultaneous fitting
- Returns results in original coordinate order

### 7. Source Injection (`inject_source()`)

New function for testing:
- Injects fake sources into FITS images
- Uses same kernel generation as measurement
- Supports in-place modification or output to new file
- Useful for validation and systematic error analysis

## Backward Compatibility

✅ **Fully backward compatible:**
- All new parameters are optional with sensible defaults
- Existing code continues to work without changes
- Falls back gracefully when dependencies unavailable (scipy)
- Falls back to simple peak measurement when beam info missing

## Dependencies

- **Required**: `numpy`, `astropy` (already in use)
- **Optional**: `scipy` (for cluster fitting via KDTree)
  - Cluster fitting gracefully disabled if scipy unavailable
  - Other features work without scipy

## Usage Examples

### Basic Usage (Unchanged)
```python
from dsa110_contimg.photometry import measure_forced_peak

result = measure_forced_peak("image.fits", ra_deg=128.725, dec_deg=55.573)
print(f"Flux: {result.peak_jyb:.6f} Jy/beam")
print(f"Error: {result.peak_err_jyb:.6f} Jy/beam")
```

### With Noise Map
```python
result = measure_forced_peak(
    "image.fits",
    ra_deg=128.725,
    dec_deg=55.573,
    noise_map_path="noise.fits",
    background_map_path="background.fits",
)
print(f"Chi-squared: {result.chisq:.2f} ({result.dof} DOF)")
```

### Cluster Fitting for Blended Sources
```python
from dsa110_contimg.photometry import measure_many

coords = [(128.725, 55.573), (128.726, 55.574)]  # Close sources
results = measure_many(
    "image.fits",
    coords,
    use_cluster_fitting=True,
    cluster_threshold=1.5,  # 1.5 × BMAJ
    noise_map_path="noise.fits",
)

for r in results:
    print(f"Source at ({r.ra_deg:.6f}, {r.dec_deg:.6f}):")
    print(f"  Flux: {r.peak_jyb:.6f} Jy/beam")
    print(f"  Cluster ID: {r.cluster_id}")
    print(f"  Chi-squared: {r.chisq:.2f}")
```

### Source Injection for Testing
```python
from dsa110_contimg.photometry import inject_source

# Inject source and save to new file
inject_source(
    "image.fits",
    ra_deg=128.725,
    dec_deg=55.573,
    flux_jy=0.01,  # 10 mJy
    output_path="image_with_injection.fits",
)

# Measure injected source
result = measure_forced_peak("image_with_injection.fits", 128.725, 55.573)
print(f"Recovered flux: {result.peak_jyb:.6f} Jy/beam")
```

## Testing Recommendations

1. **Injection/Recovery Tests**
   - Inject sources at known positions/fluxes
   - Measure and compare recovered vs. injected
   - Validate weighted convolution accuracy

2. **Cluster Fitting Validation**
   - Test with sources at various separations
   - Verify cluster fitting improves accuracy for blended sources
   - Test threshold sensitivity (1.0, 1.5, 2.0 × BMAJ)

3. **Chi-Squared Distribution**
   - Verify chi-squared follows expected distribution
   - Use for outlier detection

4. **Noise Map Comparison**
   - Compare results with/without noise maps
   - Validate noise map improves accuracy

## Performance Notes

- Weighted convolution is slightly slower than simple peak measurement
- Cluster fitting adds overhead but improves accuracy for blended sources
- Data loading optimized in `measure_many()` (loads once, not per source)
- KDTree clustering is fast even for many sources

## Future Enhancements (Optional)

- Numba acceleration for kernel computation (2-3× speedup)
- Postage stamp output for visualization
- Batch optimization for very large source lists
- Support for extended source models (not just point sources)

