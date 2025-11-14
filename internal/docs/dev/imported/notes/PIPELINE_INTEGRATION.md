# Pipeline Integration Implementation

## Overview

This document describes the integration of catalog-based validation and HTML report generation into the DSA-110 imaging pipeline.

## What Was Implemented

### 1. Validation Configuration (`pipeline/config.py`)

**New `ValidationConfig` class**:
- `enabled`: Enable/disable validation stage (default: True)
- `catalog`: Catalog to use ("nvss" or "vlass", default: "nvss")
- `validation_types`: List of validation types to run (default: all three)
- `generate_html_report`: Generate HTML report (default: True)
- `min_snr`: Minimum SNR for source detection (default: 5.0)
- `search_radius_arcsec`: Search radius for matching (default: 10.0)
- `completeness_threshold`: Completeness threshold (default: 0.95)

**Integration with `PipelineConfig`**:
- Added `validation: ValidationConfig` field to `PipelineConfig`
- Automatically initialized with defaults

### 2. Validation Stage (`pipeline/stages_impl.py`)

**New `ValidationStage` class**:
- Runs after imaging stage completes
- Performs comprehensive validation:
  - Astrometry validation (positional accuracy)
  - Flux scale validation (calibration accuracy)
  - Source counts completeness analysis
- Optionally generates HTML validation reports with diagnostic plots
- Non-fatal: Validation failures log warnings but don't stop pipeline
- Stores validation results in pipeline context

**Key Features**:
- Automatically finds FITS images (prefers PB-corrected)
- Configurable validation types
- HTML report generation with embedded plots
- Results stored in pipeline context for downstream stages

### 3. Workflow Integration (`pipeline/workflows.py`)

**Updated Workflows**:
- `standard_imaging_workflow`: Added validation stage after imaging
- `quicklook_workflow`: Added validation stage after imaging
- `reprocessing_workflow`: Added validation stage after imaging

**Conditional Addition**:
- Validation stage only added if `config.validation.enabled == True`
- Allows workflows to run with or without validation

## Usage

### Basic Usage

Validation runs automatically after imaging if enabled:

```python
from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.workflows import standard_imaging_workflow

# Create config (validation enabled by default)
config = PipelineConfig.from_env()

# Build workflow (includes validation stage)
workflow = standard_imaging_workflow(config)

# Execute pipeline
orchestrator = workflow
# ... run pipeline ...
```

### Configuration

**Enable/Disable Validation**:
```python
config = PipelineConfig.from_env()
config.validation.enabled = True  # or False to disable
```

**Customize Validation Types**:
```python
config.validation.validation_types = ["astrometry", "flux_scale"]  # Skip source_counts
```

**Disable HTML Reports**:
```python
config.validation.generate_html_report = False
```

**Change Catalog**:
```python
config.validation.catalog = "vlass"  # Use VLASS instead of NVSS
```

### Programmatic Configuration

```python
from dsa110_contimg.pipeline.config import PipelineConfig, ValidationConfig, PathsConfig

config = PipelineConfig(
    paths=PathsConfig(
        input_dir=Path("/data/input"),
        output_dir=Path("/data/output")
    ),
    validation=ValidationConfig(
        enabled=True,
        catalog="nvss",
        validation_types=["astrometry", "flux_scale", "source_counts"],
        generate_html_report=True,
        min_snr=5.0,
        search_radius_arcsec=10.0,
        completeness_threshold=0.95
    )
)
```

### Accessing Validation Results

Validation results are stored in pipeline context:

```python
# After pipeline execution
context = orchestrator.execute(context)

# Access validation results
astrometry_result = context.outputs.get("astrometry_result")
flux_scale_result = context.outputs.get("flux_scale_result")
source_counts_result = context.outputs.get("source_counts_result")
validation_report_path = context.outputs.get("validation_report_path")

if validation_report_path:
    print(f"HTML report: {validation_report_path}")
```

## Pipeline Flow

### Standard Imaging Workflow (with validation)

```
Convert → Calibrate (Solve) → Calibrate (Apply) → Image → Validate
                                                              │
                                                              ├─ Astrometry
                                                              ├─ Flux Scale
                                                              ├─ Source Counts
                                                              └─ HTML Report
```

### Without Validation

If `config.validation.enabled = False`:
```
Convert → Calibrate (Solve) → Calibrate (Apply) → Image
```

## Output Files

**HTML Reports**:
- Location: `{output_dir}/qa/reports/{image_name}_validation_report.html`
- Contains: All validation results, metrics, plots, issues, warnings
- Format: Self-contained HTML with embedded base64 plots

**Example**:
```
/data/output/qa/reports/test_image.validation_report.html
```

## Error Handling

**Non-Fatal Failures**:
- Validation failures don't stop the pipeline
- Errors are logged as warnings
- Pipeline continues even if validation fails

**Common Issues**:
1. **FITS image not found**: Validation skipped, warning logged
2. **Catalog query failure**: Individual validation skipped, warning logged
3. **HTML generation failure**: Validation runs but report not generated

## Configuration Examples

### Minimal Validation (Flux Scale Only)

```python
config.validation.validation_types = ["flux_scale"]
config.validation.generate_html_report = False
```

### Full Validation with Custom Parameters

```python
config.validation.validation_types = ["astrometry", "flux_scale", "source_counts"]
config.validation.min_snr = 7.0  # Higher SNR threshold
config.validation.search_radius_arcsec = 15.0  # Larger search radius
config.validation.completeness_threshold = 0.90  # Lower completeness threshold
config.validation.generate_html_report = True
```

### Disable Validation Entirely

```python
config.validation.enabled = False
```

## Integration Points

### Existing Integration

The `ImagingStage` already had basic flux scale validation via `_run_catalog_validation()`. This is still available via `config.imaging.run_catalog_validation`.

**Difference**:
- `ImagingStage._run_catalog_validation()`: Basic flux scale only, no HTML reports
- `ValidationStage`: Comprehensive validation with all types, HTML reports, plots

**Recommendation**: Use `ValidationStage` for production workflows. The basic validation in `ImagingStage` can be disabled:

```python
config.imaging.run_catalog_validation = False
config.validation.enabled = True
```

## Testing

### Manual Testing

1. Run pipeline with validation enabled
2. Check for HTML report in `{output_dir}/qa/reports/`
3. Verify validation results in pipeline context
4. Check logs for validation output

### Example Test

```python
from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.workflows import standard_imaging_workflow
from dsa110_contimg.pipeline.context import PipelineContext

# Create config
config = PipelineConfig.from_env()
config.validation.enabled = True

# Build workflow
workflow = standard_imaging_workflow(config)

# Create initial context
context = PipelineContext(
    config=config,
    outputs={"ms_path": "/path/to/ms"}
)

# Execute pipeline
context = workflow.execute(context)

# Check validation results
if "validation_report_path" in context.outputs:
    print(f"Validation report: {context.outputs['validation_report_path']}")
```

## Benefits

1. **Automated Validation**: Runs automatically after imaging
2. **Comprehensive**: All three validation types in one stage
3. **Configurable**: Enable/disable, customize parameters
4. **Non-Fatal**: Doesn't break pipeline on failures
5. **Integrated Reports**: HTML reports with plots automatically generated
6. **Pipeline Context**: Results available to downstream stages

## Files Modified/Created

- **Modified**: `pipeline/config.py` - Added `ValidationConfig`
- **Modified**: `pipeline/stages_impl.py` - Added `ValidationStage`
- **Modified**: `pipeline/workflows.py` - Integrated validation into workflows

## Future Enhancements

1. **Validation Thresholds**: Add pass/fail thresholds that can fail pipeline
2. **Custom Report Paths**: Allow custom HTML report locations
3. **Validation Caching**: Cache validation results for reprocessing
4. **Parallel Validation**: Run validation types in parallel
5. **Validation Metrics**: Store metrics in database for tracking over time

