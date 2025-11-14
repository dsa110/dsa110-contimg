# Forced Photometry Unit Tests

## Overview

Comprehensive unit tests for the enhanced forced photometry module (`dsa110_contimg.photometry.forced`).

**Test File**: `tests/unit/test_forced_photometry_enhanced.py`

## Test Coverage

### 1. G2D Kernel Tests (`TestG2DKernel`)
- ✅ Kernel creation and initialization
- ✅ Kernel evaluation at various positions
- ✅ Position angle handling (degrees and Quantity)

### 2. Weighted Convolution Tests (`TestWeightedConvolution`)
- ✅ Basic weighted convolution calculation
- ✅ Convolution with varying noise levels
- ✅ Chi-squared calculation validation

### 3. Basic Measurement Tests (`TestMeasureForcedPeak`)
- ✅ Basic peak measurement (without beam info)
- ✅ Weighted convolution mode (with beam info)
- ✅ Noise map support
- ✅ Background map subtraction
- ✅ Missing file handling
- ✅ Invalid coordinates handling
- ✅ NaN data handling
- ✅ Edge coordinate handling

### 4. Multiple Source Tests (`TestMeasureMany`)
- ✅ Measuring multiple sources
- ✅ Empty coordinates list
- ✅ Noise map support for multiple sources
- ✅ Cluster fitting disabled mode
- ✅ Cluster fitting enabled mode (requires scipy)
- ✅ Missing file handling

### 5. Cluster Identification Tests (`TestClusterIdentification`)
- ✅ Single source (no clustering)
- ✅ Two close sources (should cluster)
- ✅ Two distant sources (should not cluster)
- ✅ Zero threshold (clustering disabled)
- ✅ Graceful degradation without scipy

### 6. Source Injection Tests (`TestSourceInjection`)
- ✅ Basic source injection
- ✅ In-place injection
- ✅ Missing beam info error handling
- ✅ Invalid coordinates error handling

### 7. Injection/Recovery Validation (`TestInjectionRecovery`)
- ✅ Single source injection/recovery accuracy
- ✅ Multiple source injection/recovery

### 8. Result Dataclass Tests (`TestForcedPhotometryResult`)
- ✅ Result creation with required fields
- ✅ Result with optional fields (chisq, dof, cluster_id)

### 9. Edge Cases (`TestEdgeCases`)
- ✅ Noise map shape mismatch error handling
- ✅ Background map shape mismatch error handling
- ✅ Zero-valued noise pixels handling
- ✅ Small cutout size
- ✅ Large cutout size (boundary clipping)

## Test Fixtures

### `create_test_fits()`
Creates a basic test FITS file without beam information.

### `create_test_fits_with_beam()`
Creates a test FITS file with beam information (BMAJ, BMIN, BPA).

**Parameters:**
- `data_shape`: Image dimensions (default: 512x512)
- `crval1`, `crval2`: Reference pixel world coordinates
- `crpix1`, `crpix2`: Reference pixel coordinates
- `cdelts`: Pixel scale (degrees)
- `data`: Optional data array (default: random noise)
- `bmaj_deg`, `bmin_deg`, `bpa_deg`: Beam parameters
- Additional header keywords

## Running Tests

### Run all forced photometry tests:
```bash
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/test_forced_photometry_enhanced.py -v
```

### Run specific test class:
```bash
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/test_forced_photometry_enhanced.py::TestG2DKernel -v
```

### Run with coverage:
```bash
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/test_forced_photometry_enhanced.py --cov=dsa110_contimg.photometry.forced --cov-report=html
```

### Skip scipy-dependent tests (if scipy unavailable):
```bash
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/test_forced_photometry_enhanced.py -v -m "not scipy"
```

## Test Dependencies

- **Required**: `numpy`, `astropy`, `pytest`
- **Optional**: `scipy` (for cluster fitting tests)
  - Tests gracefully skip if scipy unavailable
  - All other tests run without scipy

## Test Patterns

### Temporary File Handling
All tests use temporary files created with `tempfile.NamedTemporaryFile()` and cleaned up in `finally` blocks.

### Error Handling
Tests verify graceful error handling:
- Missing files return NaN results (don't raise)
- Invalid coordinates return NaN pixel coordinates
- Shape mismatches raise `ValueError` with descriptive messages

### Validation
- Injection/recovery tests validate flux accuracy (50-150% tolerance)
- Cluster identification tests verify correct grouping behavior
- Chi-squared values are validated to be non-negative

## Known Limitations

1. **Injection/Recovery Accuracy**: Tests use 50-150% tolerance due to:
   - Random noise in test images
   - Pixelization effects
   - Numerical precision

2. **Cluster Threshold**: Exact clustering behavior depends on:
   - Beam size (BMAJ)
   - Pixel scale
   - Source separation

3. **scipy Dependency**: Cluster fitting tests require scipy but gracefully skip if unavailable.

## Future Test Additions

Potential additional tests:
- Performance benchmarks (timing tests)
- Memory usage tests for large images
- Multi-threaded measurement tests
- Extended source models (not just point sources)
- Comparison with VAST forced_phot results

