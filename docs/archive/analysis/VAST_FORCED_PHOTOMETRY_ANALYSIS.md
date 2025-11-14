# VAST Forced Photometry Utilities Analysis

## Executive Summary

The VAST `forced_phot` package provides a sophisticated forced photometry implementation with several features that could enhance our current `dsa110_contimg.photometry.forced` module. Key improvements include:

1. **Cluster fitting** for blended sources
2. **Numba-accelerated** kernel computation and convolution
3. **Separate background/noise maps** (vs. our annulus-based RMS)
4. **Chi-squared goodness-of-fit** metrics
5. **Source injection** for testing/validation
6. **Postage stamp** output for visualization

## Current Implementation (`dsa110_contimg.photometry.forced`)

### Strengths
- Simple, straightforward API
- Works with single FITS image (no separate background/noise maps required)
- Uses annulus-based RMS estimation (works when noise maps unavailable)
- Handles NaN/infinite values gracefully
- Returns pixel coordinates for debugging

### Limitations
- No cluster fitting for blended sources
- No chi-squared goodness-of-fit metric
- No source injection capability for testing
- No postage stamp output
- Single-source measurement only (no batch optimization)

## VAST Implementation (`forced_phot.ForcedPhot`)

### Key Features

#### 1. **Cluster Fitting** (`cluster()` method)
- Uses KDTree to identify sources within `threshold * BMAJ` of each other
- Default threshold: 1.5 × BMAJ (tested and validated)
- Simultaneously fits multiple sources using astropy `Gaussian2D` models
- Critical for accurate photometry of blended sources
- **Finding**: Sources closer than ~1.0 BMAJ show significant bias without cluster fitting

#### 2. **Numba Acceleration**
- `get_kernel()`: Numba-accelerated 2D Gaussian kernel computation
- `_convolution()`: Numba-accelerated weighted convolution
- `_meshgrid()`: Optimized meshgrid generation
- Provides 2-3× speedup for batch measurements
- Optional (`use_numba` flag) - falls back to pure Python

#### 3. **Separate Background/Noise Maps**
- Requires three FITS files: image, background, noise
- Background-subtracted data: `data = image - background`
- Noise map used directly (no annulus calculation needed)
- More accurate than annulus-based RMS when noise maps available
- Handles zero-valued noise pixels (converts to NaN)

#### 4. **Chi-Squared Goodness-of-Fit**
- Returns chi-squared value: `chisq = sum(((data - model) / noise)²)`
- Returns degrees of freedom: `DOF = n_pixels - n_sources`
- Useful for quality assessment and outlier detection
- Enables statistical validation of measurements

#### 5. **Source Injection** (`inject()` method)
- Injects fake sources into image for testing
- Uses same kernel generation as measurement
- Validated via injection/recovery tests
- Critical for systematic error analysis

#### 6. **Postage Stamp Output** (`stamps=True`)
- Returns data and model postage stamps for visualization
- Useful for debugging and quality assessment
- Single source only (for performance)

### Algorithm Details

#### Single Source Measurement (`_measure()`)
```python
# Weighted convolution (Condon 1997)
flux = sum((data * kernel / noise²)) / sum(kernel² / noise²)
flux_err = sum(noise * kernel / noise²) / sum(kernel / noise²)
chisq = sum(((data - kernel * flux) / noise)²)
DOF = n_pixels - 1
```

#### Cluster Measurement (`_measure_cluster()`)
- Uses astropy `Gaussian2D` models with fixed positions/shapes
- Only amplitude is free parameter
- Simultaneous fit using `LevMarLSQFitter`
- Each source gets its own amplitude parameter
- Error estimated from noise map at source position

#### Kernel Generation (`G2D` class)
- 2D Gaussian with FWHM → sigma conversion
- Position angle handling (E of N convention)
- Handles fractional pixel offsets correctly
- Numba-accelerated version available

## Recommended Enhancements

### High Priority

1. **Add Cluster Fitting**
   - Implement KDTree-based clustering (threshold = 1.5 × BMAJ)
   - Add `_measure_cluster()` method using astropy models
   - Update `measure_many()` to use clustering when enabled
   - **Benefit**: Accurate photometry for blended sources

2. **Add Chi-Squared Metric**
   - Return chi-squared and DOF in `ForcedPhotometryResult`
   - Calculate: `chisq = sum(((data - model) / noise)²)`
   - **Benefit**: Quality assessment and outlier detection

3. **Support Separate Noise Maps**
   - Add optional `noise_map` parameter to `measure_forced_peak()`
   - Use noise map directly if provided, otherwise use annulus RMS
   - **Benefit**: More accurate when noise maps available

### Medium Priority

4. **Add Source Injection**
   - Implement `inject()` method for testing
   - Use same kernel generation as measurement
   - **Benefit**: Systematic error analysis and validation

5. **Add Postage Stamp Output**
   - Optional `stamps=True` parameter
   - Return data and model cutouts
   - **Benefit**: Visualization and debugging

6. **Numba Acceleration** (Optional)
   - Add numba-accelerated kernel computation
   - Add numba-accelerated convolution
   - Make optional (fallback to pure Python)
   - **Benefit**: 2-3× speedup for batch measurements

### Low Priority

7. **Batch Optimization**
   - Optimize `measure_many()` for better performance
   - Consider vectorized operations where possible
   - **Benefit**: Faster processing of many sources

## Implementation Notes

### Cluster Fitting Algorithm
```python
def cluster(self, X0, Y0, threshold=1.5):
    """Identify clusters using KDTree."""
    threshold_pixels = threshold * (BMAJ / pixelscale).value
    tree = scipy.spatial.KDTree(np.c_[X0, Y0])
    # Find neighbors within threshold
    # Group into clusters
    # Store in self.clusters dict
```

### Chi-Squared Calculation
```python
# Single source
chisq = sum(((data - kernel * flux) / noise)²)
DOF = n_pixels - 1

# Cluster
chisq = sum(((data - model) / noise)²)
DOF = n_pixels - n_sources
```

### Noise Map Handling
```python
# Zero-valued noise pixels → NaN
noise_map[noise_map == 0] = np.nan

# Filter NaN pixels
good = np.isfinite(noise) & np.isfinite(data)
noise = noise[good]
data = data[good]
kernel = kernel[good]
```

## Compatibility Considerations

### Dependencies
- VAST uses: `numpy`, `scipy`, `astropy`, `numba` (optional)
- We already have: `numpy`, `astropy`
- Would need to add: `scipy` (for KDTree), `numba` (optional)

### API Compatibility
- VAST API: `ForcedPhot(image, background, noise).measure(positions, ...)`
- Our API: `measure_forced_peak(fits_path, ra, dec, ...)`
- **Recommendation**: Keep our API, add optional parameters for new features

### Data Format
- VAST expects: Separate background and noise FITS files
- We currently: Use single FITS image with annulus RMS
- **Recommendation**: Support both modes (backward compatible)

## Testing Recommendations

1. **Injection/Recovery Tests**
   - Inject sources at known positions/fluxes
   - Measure and compare recovered vs. injected
   - Validate cluster fitting improves accuracy for blended sources

2. **Cluster Threshold Validation**
   - Test various thresholds (1.0, 1.5, 2.0 × BMAJ)
   - Validate default of 1.5 × BMAJ is optimal

3. **Chi-Squared Distribution**
   - Verify chi-squared follows expected distribution
   - Use for outlier detection

## Code Structure Recommendations

### Enhanced `ForcedPhotometryResult`
```python
@dataclass
class ForcedPhotometryResult:
    ra_deg: float
    dec_deg: float
    peak_jyb: float
    peak_err_jyb: float
    pix_x: float
    pix_y: float
    box_size_pix: int
    chisq: Optional[float] = None  # NEW
    dof: Optional[int] = None      # NEW
    cluster_id: Optional[int] = None  # NEW (if clustered)
```

### Enhanced `measure_forced_peak()`
```python
def measure_forced_peak(
    fits_path: str,
    ra_deg: float,
    dec_deg: float,
    *,
    box_size_pix: int = 5,
    annulus_pix: Tuple[int, int] = (12, 20),
    noise_map_path: Optional[str] = None,  # NEW
    background_map_path: Optional[str] = None,  # NEW
    use_cluster_fitting: bool = False,  # NEW
    cluster_threshold: float = 1.5,  # NEW
    stamps: bool = False,  # NEW
) -> ForcedPhotometryResult:
    ...
```

## References

- VAST forced_phot: `/data/dsa110-contimg/archive/references/VAST/forced_phot/`
- Test files: `test_forced_phot_inject.py`, `test_clusterphot.py`
- Key finding: Cluster fitting critical for sources < 1.5 × BMAJ separation
- Condon (1997): Weighted convolution formula for flux measurement

