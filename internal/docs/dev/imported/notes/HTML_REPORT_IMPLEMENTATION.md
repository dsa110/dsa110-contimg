# HTML Report Generation Implementation

## Overview

This document describes the implementation of HTML validation report generation for the DSA-110 continuum imaging pipeline, inspired by ASKAP's validation framework.

## What Was Implemented

### 1. HTML Report Generation Module (`qa/html_reports.py`)

**New Classes:**
- `ValidationReport`: Unified validation report dataclass that combines all validation test results
  - Calculates overall status (PASS/WARNING/FAIL)
  - Computes validation score (0.0 to 1.0)
  - Aggregates issues and warnings from all tests

**New Functions:**
- `generate_html_report()`: Generates comprehensive HTML validation report
  - Professional styling with color-coded status badges
  - Summary dashboard with overall status and score
  - Detailed sections for each validation test
  - Image metadata display
  - Issues and warnings highlighting

- `generate_validation_report()`: Convenience function to create ValidationReport and optionally generate HTML

### 2. Enhanced Catalog Validation (`qa/catalog_validation.py`)

**New Function:**
- `run_full_validation()`: Runs all validation tests and optionally generates HTML report
  - Supports selective validation types
  - Can generate HTML report automatically
  - Returns tuple of validation results

### 3. API Endpoints (`api/routes.py`)

**New Endpoints:**

1. **GET `/api/qa/images/{image_id}/validation-report.html`**
   - Generates and returns HTML validation report
   - Query parameters:
     - `catalog`: Reference catalog ("nvss" or "vlass", default: "nvss")
     - `validation_types`: List of validation types (default: all)
     - `save_to_file`: Whether to save HTML to file (default: false)
   - Returns: HTMLResponse with validation report

2. **POST `/api/qa/images/{image_id}/validation-report/generate`**
   - Generates HTML validation report and saves to file
   - Body parameters:
     - `catalog`: Reference catalog
     - `validation_types`: List of validation types
     - `output_path`: Optional custom output path
   - Returns: JSON with report path and status

## Usage Examples

### Python API

```python
from dsa110_contimg.qa.catalog_validation import run_full_validation
from dsa110_contimg.qa.html_reports import generate_validation_report

# Run all validations and generate HTML report
astrometry, flux_scale, source_counts = run_full_validation(
    image_path="/path/to/image.fits",
    catalog="nvss",
    validation_types=["astrometry", "flux_scale", "source_counts"],
    generate_html=True,
    html_output_path="/path/to/report.html"
)

# Or generate report from existing results
from dsa110_contimg.qa.catalog_validation import (
    validate_astrometry,
    validate_flux_scale,
    validate_source_counts
)

astrometry_result = validate_astrometry("/path/to/image.fits")
flux_scale_result = validate_flux_scale("/path/to/image.fits")
source_counts_result = validate_source_counts("/path/to/image.fits")

report = generate_validation_report(
    image_path="/path/to/image.fits",
    astrometry_result=astrometry_result,
    flux_scale_result=flux_scale_result,
    source_counts_result=source_counts_result,
    output_path="/path/to/report.html"
)
```

### REST API

**Get HTML report (view in browser):**
```bash
curl "http://localhost:8000/api/qa/images/123/validation-report.html?catalog=nvss" \
  -o validation_report.html
```

**Generate and save report:**
```bash
curl -X POST "http://localhost:8000/api/qa/images/123/validation-report/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "catalog": "nvss",
    "validation_types": ["astrometry", "flux_scale", "source_counts"]
  }'
```

**View report in browser:**
```bash
# Open the generated HTML file
open state/qa/reports/image_name_validation_report.html
```

## Report Structure

The HTML report includes:

1. **Header Section**
   - Image name
   - Generation timestamp
   - DSA-110 branding

2. **Summary Dashboard**
   - Overall status badge (PASS/WARNING/FAIL)
   - Validation score (0-100%)
   - Image metadata table
   - Overall issues and warnings

3. **Validation Sections** (one per test type)
   - **Astrometry Validation**
     - Catalog used
     - Source counts (detected, catalog, matched)
     - Offset metrics (mean, RMS, max, RA, Dec)
     - Issues and warnings
   
   - **Flux Scale Validation**
     - Catalog used
     - Valid measurements count
     - Flux ratio statistics
     - Flux scale error
     - Issues and warnings
   
   - **Source Counts Validation**
     - Catalog used
     - Source counts
     - Completeness percentage
     - Issues and warnings

4. **Footer**
   - Generation timestamp
   - Pipeline attribution

## Styling

The HTML report uses:
- Modern, responsive design
- Color-coded status badges:
  - Green: PASS
  - Yellow/Orange: WARNING
  - Red: FAIL
  - Gray: UNKNOWN
- Professional gradient header
- Clean table layouts
- Highlighted issues and warnings sections

## File Locations

- **HTML Reports**: Saved to `{PIPELINE_STATE_DIR}/qa/reports/` by default
- **Module**: `src/dsa110_contimg/qa/html_reports.py`
- **API Endpoints**: `src/dsa110_contimg/api/routes.py`

## Integration with Pipeline

The HTML report generation can be integrated into the imaging stage:

```python
# In pipeline/stages_impl.py ImagingStage
from dsa110_contimg.qa.catalog_validation import run_full_validation

# After imaging completes
if context.config.imaging.run_catalog_validation:
    qa_dir = context.config.paths.state_dir / "qa" / "reports"
    qa_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = qa_dir / f"{ms_name}_validation_report.html"
    
    run_full_validation(
        image_path=primary_image,
        catalog=context.config.imaging.catalog_validation_catalog,
        generate_html=True,
        html_output_path=str(report_path)
    )
```

## Future Enhancements

1. **Plot Integration**: Embed diagnostic plots (astrometry scatter, flux ratio histogram)
2. **Interactive Elements**: Add JavaScript for expandable sections
3. **Comparison Reports**: Compare multiple images side-by-side
4. **PDF Export**: Generate PDF versions of reports
5. **Email Notifications**: Send reports via email on validation failures

## Testing

To test the implementation:

```python
# Test HTML generation
from dsa110_contimg.qa.html_reports import generate_validation_report
from dsa110_contimg.qa.catalog_validation import CatalogValidationResult

# Create mock results
astrometry = CatalogValidationResult(
    validation_type="astrometry",
    image_path="/test/image.fits",
    catalog_used="nvss",
    n_matched=10,
    n_catalog=15,
    n_detected=12,
    mean_offset_arcsec=1.5,
    rms_offset_arcsec=2.0,
    max_offset_arcsec=5.0,
    has_issues=False,
    has_warnings=True,
    warnings=["Some sources have large offsets"]
)

report = generate_validation_report(
    image_path="/test/image.fits",
    astrometry_result=astrometry,
    output_path="/tmp/test_report.html"
)

# Open in browser to verify
```

## Notes

- HTML reports are self-contained (no external dependencies)
- Reports can be shared via email or web server
- Compatible with existing validation functions
- No breaking changes to existing API

