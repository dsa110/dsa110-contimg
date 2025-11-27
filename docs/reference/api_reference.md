# Pipeline API Reference

This document provides a comprehensive API reference for the DSA-110 Continuum
Imaging Pipeline.

## Core Classes

### PipelineStage

Base class for all pipeline stages.

**Location:** `dsa110_contimg.pipeline.stages.PipelineStage`

**Methods:**

#### `validate(context: PipelineContext) -> Tuple[bool, Optional[str]]`

Validate prerequisites for stage execution.

**Parameters:**

- `context`: Pipeline context to validate

**Returns:**

- `Tuple[bool, Optional[str]]`: `(is_valid, error_message)`. If `is_valid` is
  False, `error_message` explains why validation failed.

**Example:**

```python
is_valid, error_msg = stage.validate(context)
if not is_valid:
    print(f"Validation failed: {error_msg}")
```

#### `execute(context: PipelineContext) -> PipelineContext`

Execute stage and return updated context.

**Parameters:**

- `context`: Input context with configuration and inputs

**Returns:**

- `PipelineContext`: Updated context with new outputs

**Raises:**

- `Exception`: If stage execution fails

**Example:**

```python
result_context = stage.execute(context)
output = result_context.outputs["output_key"]
```

#### `cleanup(context: PipelineContext) -> None`

Cleanup resources after execution (optional).

**Parameters:**

- `context`: Context used during execution

**Example:**

```python
stage.cleanup(context)  # Called automatically by orchestrator
```

#### `validate_outputs(context: PipelineContext) -> Tuple[bool, Optional[str]]`

Validate stage outputs after execution (optional).

**Parameters:**

- `context`: Context with outputs to validate

**Returns:**

- `Tuple[bool, Optional[str]]`: `(is_valid, error_message)`. If `is_valid` is
  False, `error_message` explains what validation failed.

**Example:**

```python
is_valid, error_msg = stage.validate_outputs(context)
```

#### `get_name() -> str`

Get stage name for logging and tracking.

**Returns:**

- `str`: Stage name (snake_case)

**Example:**

```python
stage_name = stage.get_name()  # e.g., "conversion"
```

### PipelineContext

Immutable data structure for passing data between stages.

**Location:** `dsa110_contimg.pipeline.context.PipelineContext`

**Attributes:**

- `config: PipelineConfig` - Pipeline configuration
- `job_id: Optional[int]` - Job identifier
- `inputs: Dict[str, Any]` - Input data
- `outputs: Dict[str, Any]` - Output data
- `metadata: Dict[str, Any]` - Metadata
- `state_repository: Optional[Any]` - State repository

**Methods:**

#### `with_output(key: str, value: Any) -> PipelineContext`

Create new context with added output.

**Parameters:**

- `key`: Output key
- `value`: Output value

**Returns:**

- `PipelineContext`: New context with added output

**Example:**

```python
new_context = context.with_output("ms_path", "/data/converted.ms")
```

#### `with_outputs(outputs: Dict[str, Any]) -> PipelineContext`

Create new context with multiple outputs merged.

**Parameters:**

- `outputs`: Dictionary of outputs to add

**Returns:**

- `PipelineContext`: New context with merged outputs

**Example:**

```python
new_context = context.with_outputs({
    "ms_path": "/data/converted.ms",
    "calibration_tables": {"K": "/data/K.cal"}
})
```

#### `with_metadata(key: str, value: Any) -> PipelineContext`

Create new context with added metadata.

**Parameters:**

- `key`: Metadata key
- `value`: Metadata value

**Returns:**

- `PipelineContext`: New context with added metadata

**Example:**

```python
new_context = context.with_metadata("temp_file", "/tmp/temp.dat")
```

### PipelineOrchestrator

Manages pipeline execution, dependencies, and error handling.

**Location:** `dsa110_contimg.pipeline.orchestrator.PipelineOrchestrator`

**Methods:**

#### `__init__(stages: List[StageDefinition], observer: Optional[PipelineObserver] = None)`

Initialize orchestrator.

**Parameters:**

- `stages`: List of stage definitions
- `observer`: Optional pipeline observer for monitoring

**Example:**

```python
orchestrator = PipelineOrchestrator(stages, observer=observer)
```

#### `execute(context: PipelineContext) -> PipelineResult`

Execute pipeline with given context.

**Parameters:**

- `context`: Initial pipeline context

**Returns:**

- `PipelineResult`: Pipeline execution result

**Example:**

```python
result = orchestrator.execute(context)
if result.status == PipelineStatus.COMPLETED:
    outputs = result.context.outputs
```

### PipelineConfig

Pipeline configuration using Pydantic.

**Location:** `dsa110_contimg.pipeline.config.PipelineConfig`

**Attributes:**

- `paths: PathsConfig` - Path configuration
- `conversion: ConversionConfig` - Conversion configuration
- `calibration: CalibrationConfig` - Calibration configuration
- `imaging: ImagingConfig` - Imaging configuration
- `validation: ValidationConfig` - Validation configuration
- `crossmatch: CrossMatchConfig` - Cross-match configuration
- `photometry: PhotometryConfig` - Photometry configuration

**Example:**

```python
config = PipelineConfig(
    paths=PathsConfig(
        input_dir=Path("/data/input"),
        output_dir=Path("/data/output")
    )
)
```

**Note (2025-11):** `CrossMatchConfig.catalog_types` now defaults to
`["nvss", "rax"]`, so the pipeline queries both NVSS (northern coverage) and
RACS (southern coverage) without extra configuration. Catalog resolution for
RACS strip databases accepts filenames up to ±6° from the requested declination
to match the 12° strip width produced by `build_rax_strip_db`.

## Pipeline Stages

### CatalogSetupStage

Build catalog databases if missing for observation declination.

**Location:** `dsa110_contimg.pipeline.stages_impl.CatalogSetupStage`

**Inputs:**

- `input_path` (str): Path to HDF5 observation file

**Outputs:**

- `catalog_setup_status` (str): Status of catalog setup operation

**Dependencies:** None

**Example:**

```python
stage = CatalogSetupStage(config)
context = PipelineContext(
    config=config,
    inputs={"input_path": "/data/observation.hdf5"}
)
result_context = stage.execute(context)
status = result_context.outputs["catalog_setup_status"]
```

### ConversionStage

Convert UVH5 files to CASA Measurement Sets.

**Location:** `dsa110_contimg.pipeline.stages_impl.ConversionStage`

**Inputs:**

- `input_path` (str): Path to UVH5 input file
- `start_time` (str): Start time for conversion window
- `end_time` (str): End time for conversion window

**Outputs:**

- `ms_path` (str): Path to converted Measurement Set file

**Dependencies:** None (or `catalog_setup`)

**Example:**

```python
stage = ConversionStage(config)
context = PipelineContext(
    config=config,
    inputs={
        "input_path": "/data/observation.hdf5",
        "start_time": "2025-01-01T00:00:00",
        "end_time": "2025-01-01T01:00:00"
    }
)
result_context = stage.execute(context)
ms_path = result_context.outputs["ms_path"]
```

### CalibrationSolveStage

Solve calibration solutions (K, BP, G).

**Location:** `dsa110_contimg.pipeline.stages_impl.CalibrationSolveStage`

**Inputs:**

- `ms_path` (str): Path to Measurement Set (from context.outputs)

**Outputs:**

- `calibration_tables` (dict): Dictionary of calibration table paths
  - Keys: "K", "BA", "BP", "GA", "GP", "2G" (depending on config)

**Dependencies:** `conversion`

**Example:**

```python
stage = CalibrationSolveStage(config)
context = PipelineContext(
    config=config,
    outputs={"ms_path": "/data/converted.ms"}
)
result_context = stage.execute(context)
cal_tables = result_context.outputs["calibration_tables"]
assert "K" in cal_tables
```

### CalibrationStage

Apply calibration solutions to MS.

**Location:** `dsa110_contimg.pipeline.stages_impl.CalibrationStage`

**Inputs:**

- `ms_path` (str): Path to uncalibrated Measurement Set (from context.outputs)
- `calibration_tables` (dict): Calibration tables from CalibrationSolveStage

**Outputs:**

- `ms_path` (str): Path to calibrated Measurement Set (same or updated path)

**Dependencies:** `calibration_solve`

**Example:**

```python
stage = CalibrationStage(config)
context = PipelineContext(
    config=config,
    outputs={
        "ms_path": "/data/converted.ms",
        "calibration_tables": {"K": "/data/K.cal", "BA": "/data/BA.cal"}
    }
)
result_context = stage.execute(context)
calibrated_ms = result_context.outputs["ms_path"]
```

### ImagingStage

Create images from calibrated MS.

**Location:** `dsa110_contimg.pipeline.stages_impl.ImagingStage`

**Inputs:**

- `ms_path` (str): Path to calibrated Measurement Set (from context.outputs)

**Outputs:**

- `image_path` (str): Path to output FITS image file

**Dependencies:** `calibration`

**Example:**

```python
stage = ImagingStage(config)
context = PipelineContext(
    config=config,
    outputs={"ms_path": "/data/calibrated.ms"}
)
result_context = stage.execute(context)
image_path = result_context.outputs["image_path"]
```

### OrganizationStage

Organize MS files into date-based directory structure.

**Location:** `dsa110_contimg.pipeline.stages_impl.OrganizationStage`

**Inputs:**

- `ms_path` (str) or `ms_paths` (list): MS file(s) to organize (from
  context.outputs)

**Outputs:**

- `ms_path` (str) or `ms_paths` (list): Updated paths to organized MS files

**Dependencies:** `conversion`

**Example:**

```python
stage = OrganizationStage(config)
context = PipelineContext(
    config=config,
    outputs={"ms_path": "/data/raw/observation.ms"}
)
result_context = stage.execute(context)
organized_path = result_context.outputs["ms_path"]
```

### ValidationStage

Run catalog-based validation on images.

**Location:** `dsa110_contimg.pipeline.stages_impl.ValidationStage`

**Inputs:**

- `image_path` (str): Path to FITS image file (from context.outputs)

**Outputs:**

- `validation_results` (dict): Validation results with status, metrics, and
  report_path

**Dependencies:** `imaging`

**Example:**

```python
stage = ValidationStage(config)
context = PipelineContext(
    config=config,
    outputs={"image_path": "/data/image.fits"}
)
result_context = stage.execute(context)
validation_results = result_context.outputs["validation_results"]
assert validation_results["status"] in ["passed", "warning", "failed"]
```

### CrossMatchStage

Match detected sources with reference catalogs.

**Location:** `dsa110_contimg.pipeline.stages_impl.CrossMatchStage`

**Inputs:**

- `detected_sources` (DataFrame): Detected sources from photometry/validation
- `image_path` (str): Path to image (used if detected_sources not available)

**Outputs:**

- `crossmatch_results` (dict): Cross-match results with matches, offsets, flux
  scales

**Dependencies:** `validation` or `photometry`

**Example:**

```python
config.crossmatch.enabled = True
stage = CrossMatchStage(config)
context = PipelineContext(
    config=config,
    outputs={
        "image_path": "/data/image.fits",
        "detected_sources": pd.DataFrame([...])  # Optional
    }
)
result_context = stage.execute(context)
crossmatch_results = result_context.outputs["crossmatch_results"]
```

### AdaptivePhotometryStage

Measure photometry using adaptive channel binning.

**Location:** `dsa110_contimg.pipeline.stages_impl.AdaptivePhotometryStage`

**Inputs:**

- `ms_path` (str): Path to calibrated Measurement Set (from context.outputs)
- `image_path` (str): Optional path to image for source detection

**Outputs:**

- `photometry_results` (DataFrame): Photometry results with adaptive binning

**Dependencies:** `calibration`

**Example:**

```python
config.photometry.enabled = True
stage = AdaptivePhotometryStage(config)
context = PipelineContext(
    config=config,
    outputs={
        "ms_path": "/data/calibrated.ms",
        "image_path": "/data/image.fits"  # Optional
    }
)
result_context = stage.execute(context)
photometry_results = result_context.outputs["photometry_results"]
```

## Enums

### StageStatus

Stage execution status.

**Location:** `dsa110_contimg.pipeline.stages.StageStatus`

**Values:**

- `PENDING`: Stage not yet started
- `RUNNING`: Stage currently executing
- `COMPLETED`: Stage completed successfully
- `FAILED`: Stage failed
- `SKIPPED`: Stage skipped

### PipelineStatus

Pipeline execution status.

**Location:** `dsa110_contimg.pipeline.orchestrator.PipelineStatus`

**Values:**

- `COMPLETED`: All stages completed successfully
- `FAILED`: Pipeline failed
- `PARTIAL`: Some stages completed, some failed

### ExecutionMode

Stage execution mode.

**Location:** `dsa110_contimg.pipeline.stages.ExecutionMode`

**Values:**

- `DIRECT`: In-process execution (default, faster)
- `SUBPROCESS`: Isolated subprocess (for memory safety)
- `REMOTE`: Distributed execution (future)

## Related Documentation

- [Pipeline Stage Architecture](../architecture/pipeline/pipeline_stage_architecture.md)
- [Creating Pipeline Stages](../architecture/pipeline/pipeline_patterns.md)
- Testing Guide
- [Real-World Examples](../examples/real_world_examples.md)
