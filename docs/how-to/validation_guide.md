# DSA-110 Validation Guide

## Overview

The DSA-110 continuum imaging pipeline includes comprehensive validation capabilities for assessing image quality, astrometry, flux scale, and source completeness. This guide explains how to use the validation system.

## Quick Start

### Running Validation via API

The simplest way to run validation is through the API:

```bash
# Get HTML validation report
curl "http://localhost:8000/api/qa/images/{image_id}/validation-report.html?catalog=nvss"

# Run validation and get JSON results
curl -X POST "http://localhost:8000/api/qa/images/{image_id}/catalog-validation/run" \
  -H "Content-Type: application/json" \
  -d '{"catalog": "nvss", "validation_types": ["astrometry", "flux_scale", "source_counts"]}'
```

### Running Validation in Python

```python
from dsa110_contimg.qa.catalog_validation import run_full_validation

# Run all validation tests and generate HTML report
astrometry_result, flux_result, completeness_result = run_full_validation(
    image_path="/path/to/image.fits",
    catalog="nvss",
    validation_types=["astrometry", "flux_scale", "source_counts"],
    generate_html=True,
    html_output_path="/path/to/report.html"
)
```

## Validation Types

### 1. Astrometry Validation

Validates the positional accuracy of detected sources by comparing with reference catalogs.

**Metrics:**
- Mean RA/Dec offsets
- RMS offset
- Maximum offset
- Number of matched sources

**Configuration:**
```yaml
validation:
  min_snr: 5.0  # Minimum SNR for source detection
  search_radius_arcsec: 10.0  # Matching radius
```

**Example:**
```python
from dsa110_contimg.qa.catalog_validation import validate_astrometry

result = validate_astrometry(
    image_path="image.fits",
    catalog="nvss",
    min_snr=5.0,
    search_radius_arcsec=10.0
)

print(f"Mean offset: {result.mean_offset_ra*3600:.2f} arcsec RA, "
      f"{result.mean_offset_dec*3600:.2f} arcsec Dec")
print(f"RMS offset: {result.rms_offset_arcsec:.2f} arcsec")
```

### 2. Flux Scale Validation

Compares measured fluxes with reference catalog fluxes to assess calibration accuracy.

**Metrics:**
- Mean flux ratio (detected/catalog)
- RMS flux ratio
- Flux scale error percentage
- Number of matched sources

**Configuration:**
```yaml
validation:
  min_snr: 5.0
  search_radius_arcsec: 10.0
```

**Example:**
```python
from dsa110_contimg.qa.catalog_validation import validate_flux_scale

result = validate_flux_scale(
    image_path="image.fits",
    catalog="nvss",
    min_snr=5.0
)

print(f"Mean flux ratio: {result.mean_flux_ratio:.3f}")
print(f"Flux scale error: {result.flux_scale_error*100:.1f}%")
```

### 3. Source Counts Completeness Analysis

Evaluates the completeness and reliability of source detection vs. flux density.

**Metrics:**
- Overall completeness percentage
- Completeness limit (flux at which completeness drops below threshold)
- Completeness per flux bin
- Source counts per flux bin

**Configuration:**
```yaml
validation:
  completeness_threshold: 0.95  # 95% completeness threshold
  min_snr: 5.0
```

**Example:**
```python
from dsa110_contimg.qa.catalog_validation import validate_source_counts

result = validate_source_counts(
    image_path="image.fits",
    catalog="nvss",
    completeness_threshold=0.95
)

print(f"Overall completeness: {result.completeness*100:.1f}%")
print(f"Completeness limit: {result.completeness_limit_jy*1000:.2f} mJy")
```

## Configuration

### YAML Configuration File

Create a validation configuration file:

```yaml
validation:
  enabled: true
  catalog: "nvss"  # or "vlass"
  validation_types:
    - "astrometry"
    - "flux_scale"
    - "source_counts"
  generate_html_report: true
  min_snr: 5.0
  search_radius_arcsec: 10.0
  completeness_threshold: 0.95
```

Load configuration:

```python
from dsa110_contimg.pipeline.config import PipelineConfig

config = PipelineConfig.from_yaml("validation_config.yaml")
validation_config = config.validation
```

### Environment Variables

You can also configure validation via environment variables:

```bash
export PIPELINE_VALIDATION_ENABLED=true
export PIPELINE_VALIDATION_CATALOG=nvss
export PIPELINE_VALIDATION_MIN_SNR=5.0
```

## HTML Reports

Validation reports are generated as HTML files with:

- **Summary Dashboard**: Overview of all validation metrics
- **Data Type Banner**: Clear indication of test vs. real data
- **Image Visualization**: FITS image preview
- **Astrometry Section**: Positional accuracy metrics and plots
- **Flux Scale Section**: Flux comparison metrics and plots
- **Source Counts Section**: Completeness analysis and plots
- **Enhanced Visualizations**:
  - Spatial distribution plots
  - Flux vs. offset correlation
  - Validation summary dashboard

### Generating HTML Reports

**Via API:**
```bash
# Get HTML report (returns HTML directly)
curl "http://localhost:8000/api/qa/images/{image_id}/validation-report.html?save_to_file=true"

# Generate and save report
curl -X POST "http://localhost:8000/api/qa/images/{image_id}/validation-report/generate" \
  -H "Content-Type: application/json" \
  -d '{"catalog": "nvss", "output_path": "/path/to/report.html"}'
```

**Via Python:**
```python
from dsa110_contimg.qa.html_reports import generate_validation_report

generate_validation_report(
    image_path="image.fits",
    astrometry_result=astrometry_result,
    flux_scale_result=flux_result,
    source_counts_result=completeness_result,
    output_path="validation_report.html",
    catalog="nvss"
)
```

## Pipeline Integration

Validation is automatically integrated into the imaging pipeline:

```python
from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.workflows import standard_imaging_workflow

# Configure validation
config = PipelineConfig.from_env()
config.validation.enabled = True
config.validation.generate_html_report = True

# Run pipeline (validation runs automatically after imaging)
workflow = standard_imaging_workflow(config)
orchestrator = workflow.build()
context = orchestrator.execute(context)
```

Validation reports are saved to: `{output_dir}/qa/reports/{image_name}_validation_report.html`

## Reference Catalogs

### NVSS (NRAO VLA Sky Survey)

- Frequency: 1.4 GHz
- Coverage: δ > -40°
- Flux limit: ~2.5 mJy
- Use for: Northern hemisphere sources, low-frequency validation

### VLASS (VLA Sky Survey)

- Frequency: 3 GHz
- Coverage: δ > -40°
- Flux limit: ~1 mJy
- Use for: Higher frequency validation, better sensitivity

## Interpreting Results

### Astrometry Validation

- **Good**: RMS offset < 1 arcsec, mean offset < 0.5 arcsec
- **Acceptable**: RMS offset < 2 arcsec, mean offset < 1 arcsec
- **Poor**: RMS offset > 2 arcsec or systematic offsets

### Flux Scale Validation

- **Good**: Flux ratio 0.95-1.05, error < 5%
- **Acceptable**: Flux ratio 0.90-1.10, error < 10%
- **Poor**: Flux ratio outside 0.90-1.10 or error > 10%

### Source Counts Completeness

- **Good**: Completeness > 90% at target flux limit
- **Acceptable**: Completeness > 80% at target flux limit
- **Poor**: Completeness < 80% or no completeness limit found

## Troubleshooting

### No Matched Sources

- Check that catalog files are available
- Verify image coordinates are within catalog coverage
- Increase `search_radius_arcsec` if sources are slightly offset
- Check that `min_snr` is appropriate for your image

### Poor Astrometry

- Verify WCS information in FITS header
- Check for systematic offsets (may indicate calibration issues)
- Review spatial distribution plot for patterns

### Poor Flux Scale

- Verify frequency scaling is correct
- Check for systematic flux errors (may indicate calibration issues)
- Review flux ratio histogram for outliers

### Low Completeness

- Check that `min_snr` is appropriate
- Verify catalog coverage for your field
- Review completeness curve to identify flux range issues

## Advanced Usage

### Custom Validation Configuration

```python
from dsa110_contimg.qa.catalog_validation import validate_astrometry

# Custom validation with specific parameters
result = validate_astrometry(
    image_path="image.fits",
    catalog="nvss",
    min_snr=7.0,  # Higher SNR threshold
    search_radius_arcsec=5.0,  # Tighter matching
    min_flux_jy=0.01,  # Minimum flux threshold
    max_flux_jy=10.0  # Maximum flux threshold
)
```

### Accessing Raw Data

```python
# Access matched pairs for custom analysis
for pair in result.matched_pairs:
    detected_ra, detected_dec, catalog_ra, catalog_dec, offset = pair
    # Custom processing...

# Access matched fluxes
for flux_pair in result.matched_fluxes:
    detected_flux, catalog_flux, ratio = flux_pair
    # Custom processing...
```

## See Also

- [API Documentation](../reference/api.md#validation-endpoints)
- [Configuration Guide](../configuration.md)
- [Pipeline Documentation](../operations/pipeline.md)

