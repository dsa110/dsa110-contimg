# Synthetic Data Generation Capabilities

## Overview

The DSA-110 continuum imaging pipeline has several synthetic data generation capabilities for testing and development:

1. **Synthetic UVH5 Visibility Data** - For end-to-end pipeline testing
2. **Synthetic FITS Images** - For dashboard/SkyView testing
3. **Mock Database Data** - For dashboard UI testing

## 1. Synthetic UVH5 Visibility Data

### Purpose
Generate realistic multi-subband UVH5 visibility data that matches the DSA-110 correlator format for end-to-end pipeline testing.

### Location
- **Script:** `src/dsa110_contimg/simulation/make_synthetic_uvh5.py`
- **Documentation:** `docs/tutorials/simulation-tutorial.md`
- **Config:** `src/dsa110_contimg/simulation/config/`

### Capabilities
- Generates 16 subbands (matching DSA-110 correlator output)
- Creates realistic antenna positions from ITRF coordinates
- Phased visibility data toward specified sky positions
- Configurable duration, frequency coverage, and source flux
- Requires a template UVH5 file as input

### Usage
```bash
python -m dsa110_contimg.simulation.make_synthetic_uvh5 \
    --output /tmp/synthetic_subbands \
    --start-time "2025-10-06T12:00:00" \
    --subbands 16 \
    --duration-minutes 5.0
```

### Status
✅ **Fully Functional** - Used in integration tests and end-to-end pipeline validation.

## 2. Synthetic FITS Images

### Purpose
Generate simple 2D FITS images with point sources and noise for SkyView testing and dashboard development.

### Location
- **Script:** `scripts/create_synthetic_images.py`
- **Output Directory:** `/data/dsa110-contimg/state/images/`

### Capabilities
- Creates valid FITS files with proper WCS headers
- Adds Gaussian point sources with configurable flux
- Includes realistic noise and beam parameters
- Automatically adds images to `products.sqlite3` database
- Supports multiple image types (image, pbcor, pb)

### Usage
```bash
python scripts/create_synthetic_images.py
```

### Features
- **Image Size:** 512x512 pixels (configurable)
- **Pixel Scale:** 2.0 arcsec/pixel (configurable)
- **Point Sources:** 3-8 sources per image with random positions and fluxes
- **Noise:** Configurable RMS noise level (default ~1 mJy)
- **Beam:** Realistic beam parameters (FWHM ~10 pixels)
- **WCS:** Proper astropy WCS headers for coordinate transformation

### Generated Images
The script creates 11 synthetic images:
- 5 dirty images (`.img.image.fits`)
- 5 primary beam corrected images (`.img.image.pbcor.fits`)
- 1 primary beam image (`.img.pb.fits`)

All images are added to the `products.sqlite3` database with appropriate metadata.

### Status
✅ **Fully Functional** - Ready for SkyView testing.

## 3. Mock Database Data

### Purpose
Generate mock database entries for dashboard UI testing without requiring real pipeline data.

### Location
- **Script:** `scripts/create_mock_dashboard_data.py`
- **Database:** `state/products.sqlite3`

### Capabilities
- Creates mock variability statistics
- Generates ESE candidate entries
- Creates photometry timeseries data
- Adds mosaic entries
- Generates alert history

### Usage
```bash
python scripts/create_mock_dashboard_data.py
```

### Status
✅ **Fully Functional** - Used for dashboard development and testing.

## Integration with Pipeline

### Synthetic UVH5 → MS → Images
The full pipeline can be tested with synthetic data:

1. **Generate UVH5:** `make_synthetic_uvh5.py`
2. **Convert to MS:** `hdf5_orchestrator.py`
3. **Calibrate:** `cli_calibrate.py`
4. **Image:** `cli_imaging.py`
5. **View in SkyView:** Images appear in dashboard

### Synthetic FITS for Quick Testing
For rapid SkyView testing without running the full pipeline:

1. **Generate FITS:** `create_synthetic_images.py`
2. **View in SkyView:** Images immediately available in dashboard

## Test Scripts

### End-to-End Pipeline Test
```bash
bash tests/integration/test_pipeline_end_to_end.sh
```
- Generates synthetic UVH5 data
- Runs full pipeline (conversion → calibration → imaging)
- Validates outputs

### Synthetic Calibration Test
```bash
python tests/scripts/run_synthetic_calibration.py
```
- Tests calibration workflow with synthetic data

### SkyView Test
```bash
python scripts/test_skyview.py
python scripts/test_skyview_direct.py
```
- Tests SkyView functionality with synthetic images

## Limitations

### Synthetic UVH5
- Requires a template UVH5 file (from real observations)
- Simplified source model (point sources only)
- Does not include realistic RFI or calibration errors
- Limited to basic visibility structure

### Synthetic FITS Images
- Simple 2D images (no frequency/Stokes axes)
- Point sources only (no extended sources)
- Simplified noise model (Gaussian only)
- No realistic calibration artifacts

### Mock Database Data
- No actual image files (paths may not exist)
- Simplified source models
- No realistic temporal correlations

## Recommendations

### For Development
- Use `create_synthetic_images.py` for rapid SkyView UI testing
- Use `create_mock_dashboard_data.py` for dashboard component testing

### For Integration Testing
- Use `make_synthetic_uvh5.py` for full pipeline validation
- Combine with real calibration tables when available

### For Production Validation
- Always validate with real observational data
- Use synthetic data for regression testing only

## Future Enhancements

Potential improvements to synthetic data generation:

1. **Extended Sources:** Add Gaussian and disk source models
2. **Realistic RFI:** Include time/frequency-dependent RFI patterns
3. **Calibration Errors:** Add realistic gain and phase errors
4. **Multi-frequency:** Support multi-frequency synthesis images
5. **Polarization:** Add full Stokes parameter support
6. **Temporal Variability:** Add realistic source variability

## Related Documentation

- **Simulation Tutorial:** `docs/tutorials/simulation-tutorial.md`
- **Pipeline Testing Guide:** `docs/how-to/PIPELINE_TESTING_GUIDE.md`
- **SkyView Implementation:** `docs/SKYVIEW_IMPLEMENTATION_PLAN.md`

