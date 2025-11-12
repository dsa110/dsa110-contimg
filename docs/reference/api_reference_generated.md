# Pipeline API Reference

> **Generated:** This document is auto-generated from docstrings.
> **Last Updated:** Run `scripts/generate_api_reference.py` to regenerate.

## Table of Contents

- [Pipeline.Stages](#pipelinestages)
- [Pipeline.Stages Impl](#pipelinestages-impl)
- [Pipeline.Orchestrator](#pipelineorchestrator)
- [Pipeline.Config](#pipelineconfig)
- [Pipeline.Context](#pipelinecontext)
- [Pipeline.Workflows](#pipelineworkflows)
- [Conversion.Uvh5 To Ms](#conversionuvh5-to-ms)
- [Conversion.Streaming.Streaming Converter](#conversionstreamingstreaming-converter)
- [Calibration.Calibration](#calibrationcalibration)
- [Imaging.Spw Imaging](#imagingspw-imaging)
- [Qa.Base](#qabase)
- [Qa.Fast Validation](#qafast-validation)
- [Photometry.Forced](#photometryforced)
- [Catalog.Crossmatch](#catalogcrossmatch)

---

## Pipeline.Stages

**Module:** `pipeline.stages`

### Module Description

Base classes for pipeline stages.

A pipeline stage is a unit of work that transforms a PipelineContext into
a new PipelineContext with additional outputs.

### Classes

#### `ExecutionMode`

Execution mode for a pipeline stage.

#### `PipelineStage`

Base class for all pipeline stages.

A stage transforms a PipelineContext by executing work and returning
an updated context with new outputs.

Example:
    class ConversionStage(PipelineStage):
        def execute(self, context: PipelineContext) -> PipelineContext:
            ms_path = convert_uvh5_to_ms(context.inputs["input_path"])
            return context.with_output("ms_path", ms_path)

        def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
            if "input_path" not in context.inputs:
                return False, "input_path required"
            return True, None

**Methods:**

- `cleanup(self, context: 'PipelineContext') -> 'None'`
  - Cleanup resources after execution (optional).
- `execute(self, context: 'PipelineContext') -> 'PipelineContext'`
  - Execute stage and return updated context.
- `get_name(self) -> 'str'`
  - Get stage name for logging and tracking.
- `validate(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate prerequisites for stage execution.
- `validate_outputs(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate stage outputs after execution (optional).

#### `StageStatus`

Status of a pipeline stage execution.

---

## Pipeline.Stages Impl

**Module:** `pipeline.stages_impl`

### Module Description

Concrete pipeline stage implementations.

These stages wrap existing conversion, calibration, and imaging functions
to provide a unified pipeline interface.

### Classes

#### `AdaptivePhotometryStage`

Adaptive binning photometry stage: Measure photometry using adaptive channel binning.

This stage runs adaptive binning photometry on sources in the field, either
from a provided list of coordinates or by querying the NVSS catalog.

Example:
    >>> config = PipelineConfig(paths=PathsConfig(...))
    >>> config.photometry.enabled = True
    >>> stage = AdaptivePhotometryStage(config)
    >>> # Context should have ms_path and optionally image_path
    >>> context = PipelineContext(
    ...     config=config,
    ...     outputs={
    ...         "ms_path": "/data/calibrated.ms",
    ...         "image_path": "/data/image.fits"  # Optional
    ...     }
    ... )
    >>> # Validate prerequisites
    >>> is_valid, error = stage.validate(context)
    >>> if is_valid:
    ...     # Execute adaptive photometry
    ...     result_context = stage.execute(context)
    ...     # Get photometry results
    ...     photometry_results = result_context.outputs["photometry_results"]
    ...     # Results include flux measurements with adaptive binning

Inputs:
    - `ms_path` (str): Path to calibrated Measurement Set (from context.outputs)
    - `image_path` (str): Optional path to image for source detection

Outputs:
    - `photometry_results` (DataFrame): Photometry results with adaptive binning

**Methods:**

- `cleanup(self, context: 'PipelineContext') -> 'None'`
  - Cleanup partial adaptive photometry outputs on failure.
- `execute(self, context: 'PipelineContext') -> 'PipelineContext'`
  - Execute adaptive photometry stage.
- `get_name(self) -> 'str'`
  - Get stage name.
- `validate(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate prerequisites for adaptive photometry.
- `validate_outputs(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate adaptive photometry outputs.

#### `CalibrationSolveStage`

Calibration solve stage: Solve calibration solutions (K, BP, G).

This stage solves calibration tables (delay/K, bandpass/BP, gains/G)
for a calibrator Measurement Set. This wraps the calibration CLI
functions directly without subprocess overhead.

Example:
    >>> config = PipelineConfig(paths=PathsConfig(...))
    >>> stage = CalibrationSolveStage(config)
    >>> # Context should have ms_path from conversion stage
    >>> context = PipelineContext(
    ...     config=config,
    ...     outputs={"ms_path": "/data/converted.ms"}
    ... )
    >>> # Validate prerequisites
    >>> is_valid, error = stage.validate(context)
    >>> if is_valid:
    ...     # Execute calibration solving
    ...     result_context = stage.execute(context)
    ...     # Get calibration tables
    ...     cal_tables = result_context.outputs["calibration_tables"]
    ...     # Tables include: K, BA, BP, GA, GP, 2G
    ...     assert "K" in cal_tables

Inputs:
    - `ms_path` (str): Path to Measurement Set (from context.outputs)

Outputs:
    - `calibration_tables` (dict): Dictionary of calibration table paths
      Keys: "K", "BA", "BP", "GA", "GP", "2G" (depending on config)

**Methods:**

- `cleanup(self, context: 'PipelineContext') -> 'None'`
  - Cleanup partial calibration tables on failure.
- `execute(self, context: 'PipelineContext') -> 'PipelineContext'`
  - Execute calibration solve stage.
- `get_name(self) -> 'str'`
  - Get stage name.
- `validate(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate prerequisites for calibration solving.
- `validate_outputs(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate calibration solve outputs.

#### `CalibrationStage`

Calibration stage: Apply calibration solutions to MS.

This stage applies calibration solutions (bandpass, gain) to the
Measurement Set. In the current implementation, this wraps the
existing calibration service.

Example:
    >>> config = PipelineConfig(paths=PathsConfig(...))
    >>> stage = CalibrationStage(config)
    >>> # Context should have ms_path and calibration_tables
    >>> context = PipelineContext(
    ...     config=config,
    ...     outputs={
    ...         "ms_path": "/data/converted.ms",
    ...         "calibration_tables": {"K": "/data/K.cal", "BA": "/data/BA.cal"}
    ...     }
    ... )
    >>> # Validate prerequisites
    >>> is_valid, error = stage.validate(context)
    >>> if is_valid:
    ...     # Execute calibration application
    ...     result_context = stage.execute(context)
    ...     # Calibrated MS path available for imaging
    ...     calibrated_ms = result_context.outputs.get("ms_path")
    ...     # Same MS path, now calibrated

Inputs:
    - `ms_path` (str): Path to uncalibrated Measurement Set (from context.outputs)
    - `calibration_tables` (dict): Calibration tables from CalibrationSolveStage

Outputs:
    - `ms_path` (str): Path to calibrated Measurement Set (same or updated path)

**Methods:**

- `cleanup(self, context: 'PipelineContext') -> 'None'`
  - Cleanup resources after execution (optional).
- `execute(self, context: 'PipelineContext') -> 'PipelineContext'`
  - Execute calibration stage.
- `get_name(self) -> 'str'`
  - Get stage name.
- `validate(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate prerequisites for calibration.
- `validate_outputs(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate calibration application outputs.

#### `CatalogSetupStage`

Catalog setup stage: Build catalog databases if missing for observation declination.

This stage runs before other stages to ensure catalog databases (NVSS, FIRST, RAX)
are available for the declination strip being observed. Since DSA-110 only slews
in elevation and changes declination rarely, catalogs need to be updated when
declination changes.

The stage:
1. Extracts declination from the observation (HDF5 file)
2. Checks if catalog databases exist for that declination strip
3. Builds missing catalogs automatically
4. Logs catalog status for downstream stages

Example:
    >>> config = PipelineConfig(paths=PathsConfig(...))
    >>> stage = CatalogSetupStage(config)
    >>> context = PipelineContext(
    ...     config=config,
    ...     inputs={"input_path": "/data/observation.hdf5"}
    ... )
    >>> # Validate prerequisites
    >>> is_valid, error = stage.validate(context)
    >>> if is_valid:
    ...     # Execute stage
    ...     result_context = stage.execute(context)
    ...     # Check catalog setup status
    ...     status = result_context.outputs["catalog_setup_status"]
    ...     # Status can be: "completed", "skipped_no_dec", "skipped_error"

Inputs:
    - `input_path` (str): Path to HDF5 observation file

Outputs:
    - `catalog_setup_status` (str): Status of catalog setup operation

**Methods:**

- `cleanup(self, context: 'PipelineContext') -> 'None'`
  - Cleanup on failure (nothing to clean up for catalog setup).
- `execute(self, context: 'PipelineContext') -> 'PipelineContext'`
  - Execute catalog setup: build databases if missing.
- `get_name(self) -> 'str'`
  - Get stage name.
- `validate(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate prerequisites for catalog setup.
- `validate_outputs(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate stage outputs after execution (optional).

#### `ConversionStage`

Conversion stage: UVH5 → MS.

Discovers complete subband groups in the specified time window and
converts them to CASA Measurement Sets.

Example:
    >>> config = PipelineConfig(paths=PathsConfig(...))
    >>> stage = ConversionStage(config)
    >>> context = PipelineContext(
    ...     config=config,
    ...     inputs={
    ...         "input_path": "/data/observation.hdf5",
    ...         "start_time": "2025-01-01T00:00:00",
    ...         "end_time": "2025-01-01T01:00:00"
    ...     }
    ... )
    >>> # Validate prerequisites
    >>> is_valid, error = stage.validate(context)
    >>> if is_valid:
    ...     # Execute conversion
    ...     result_context = stage.execute(context)
    ...     # Get converted MS path
    ...     ms_path = result_context.outputs["ms_path"]
    ...     # MS path is now available for calibration stages

Inputs:
    - `input_path` (str): Path to UVH5 input file
    - `start_time` (str): Start time for conversion window
    - `end_time` (str): End time for conversion window

Outputs:
    - `ms_path` (str): Path to converted Measurement Set file

**Methods:**

- `cleanup(self, context: 'PipelineContext') -> 'None'`
  - Cleanup partial conversion outputs on failure.
- `execute(self, context: 'PipelineContext') -> 'PipelineContext'`
  - Execute conversion stage.
- `get_name(self) -> 'str'`
  - Get stage name.
- `validate(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate prerequisites for conversion.
- `validate_outputs(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate conversion outputs.

#### `CrossMatchStage`

Cross-match stage: Match detected sources with reference catalogs.

This stage cross-matches detected sources from images with reference catalogs
(NVSS, FIRST, RACS) to:
- Identify known sources
- Calculate astrometric offsets
- Calculate flux scale corrections
- Store cross-match results in database

The stage supports both basic (nearest neighbor) and advanced (all matches)
matching methods.

Example:
    >>> config = PipelineConfig(paths=PathsConfig(...))
    >>> config.crossmatch.enabled = True
    >>> stage = CrossMatchStage(config)
    >>> # Context should have detected_sources or image_path
    >>> context = PipelineContext(
    ...     config=config,
    ...     outputs={
    ...         "image_path": "/data/image.fits",
    ...         "detected_sources": pd.DataFrame([...])  # Optional
    ...     }
    ... )
    >>> # Validate prerequisites
    >>> is_valid, error = stage.validate(context)
    >>> if is_valid:
    ...     # Execute cross-matching
    ...     result_context = stage.execute(context)
    ...     # Get cross-match results
    ...     crossmatch_results = result_context.outputs["crossmatch_results"]
    ...     # Results include matches, offsets, flux scales

Inputs:
    - `detected_sources` (DataFrame): Detected sources from photometry/validation
    - `image_path` (str): Path to image (used if detected_sources not available)

Outputs:
    - `crossmatch_results` (dict): Cross-match results with matches, offsets, flux scales

**Methods:**

- `cleanup(self, context: 'PipelineContext') -> 'None'`
  - Cleanup on failure (nothing to clean up for cross-match).
- `execute(self, context: 'PipelineContext') -> 'PipelineContext'`
  - Execute cross-match stage.
- `get_name(self) -> 'str'`
  - Get stage name.
- `validate(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate prerequisites for cross-matching.
- `validate_outputs(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate stage outputs after execution (optional).

#### `ImagingStage`

Imaging stage: Create images from calibrated MS.

This stage runs imaging on the calibrated Measurement Set to produce
continuum images using CASA's tclean algorithm.

Example:
    >>> config = PipelineConfig(paths=PathsConfig(...))
    >>> stage = ImagingStage(config)
    >>> # Context should have ms_path from previous calibration stage
    >>> context = PipelineContext(
    ...     config=config,
    ...     outputs={"ms_path": "/data/calibrated.ms"}
    ... )
    >>> # Validate prerequisites
    >>> is_valid, error = stage.validate(context)
    >>> if is_valid:
    ...     # Execute imaging
    ...     result_context = stage.execute(context)
    ...     # Get image path
    ...     image_path = result_context.outputs["image_path"]
    ...     # Image is now available for validation/photometry stages

Inputs:
    - `ms_path` (str): Path to calibrated Measurement Set (from context.outputs)

Outputs:
    - `image_path` (str): Path to output FITS image file

**Methods:**

- `cleanup(self, context: 'PipelineContext') -> 'None'`
  - Cleanup partial image files on failure.
- `execute(self, context: 'PipelineContext') -> 'PipelineContext'`
  - Execute imaging stage.
- `get_name(self) -> 'str'`
  - Get stage name.
- `validate(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate prerequisites for imaging.
- `validate_outputs(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate imaging outputs.

#### `OrganizationStage`

Organization stage: Organize MS files into date-based directory structure.

Moves MS files into organized subdirectories:
- Calibrator MS → ms/calibrators/YYYY-MM-DD/
- Science MS → ms/science/YYYY-MM-DD/
- Failed MS → ms/failed/YYYY-MM-DD/

Updates database paths to reflect new locations.

Example:
    >>> config = PipelineConfig(paths=PathsConfig(...))
    >>> stage = OrganizationStage(config)
    >>> # Context should have ms_path or ms_paths from previous stages
    >>> context = PipelineContext(
    ...     config=config,
    ...     outputs={"ms_path": "/data/raw/observation.ms"}
    ... )
    >>> # Validate prerequisites
    >>> is_valid, error = stage.validate(context)
    >>> if is_valid:
    ...     # Execute organization
    ...     result_context = stage.execute(context)
    ...     # MS file moved to organized location
    ...     organized_path = result_context.outputs.get("ms_path")
    ...     # Path now in: ms/science/2025-01-01/observation.ms

Inputs:
    - `ms_path` (str) or `ms_paths` (list): MS file(s) to organize (from context.outputs)

Outputs:
    - `ms_path` (str) or `ms_paths` (list): Updated paths to organized MS files

**Methods:**

- `cleanup(self, context: 'PipelineContext') -> 'None'`
  - Cleanup resources after execution (optional).
- `execute(self, context: 'PipelineContext') -> 'PipelineContext'`
  - Execute organization stage.
- `get_name(self) -> 'str'`
  - Get stage name.
- `validate(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate organization stage prerequisites.
- `validate_outputs(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate organization outputs.

#### `ValidationStage`

Validation stage: Run catalog-based validation on images.

This stage performs comprehensive validation of images including:
- Astrometry validation (positional accuracy)
- Flux scale validation (calibration accuracy)
- Source counts completeness analysis

Optionally generates HTML validation reports with diagnostic plots.

Example:
    >>> config = PipelineConfig(paths=PathsConfig(...))
    >>> stage = ValidationStage(config)
    >>> # Context should have image_path from imaging stage
    >>> context = PipelineContext(
    ...     config=config,
    ...     outputs={"image_path": "/data/image.fits"}
    ... )
    >>> # Validate prerequisites
    >>> is_valid, error = stage.validate(context)
    >>> if is_valid:
    ...     # Execute validation
    ...     result_context = stage.execute(context)
    ...     # Get validation results
    ...     validation_results = result_context.outputs["validation_results"]
    ...     # Results include: status, metrics, report_path
    ...     assert validation_results["status"] in ["passed", "warning", "failed"]

Inputs:
    - `image_path` (str): Path to FITS image file (from context.outputs)

Outputs:
    - `validation_results` (dict): Validation results with status, metrics, and report_path

**Methods:**

- `cleanup(self, context: 'PipelineContext') -> 'None'`
  - Cleanup resources after execution (optional).
- `execute(self, context: 'PipelineContext') -> 'PipelineContext'`
  - Execute validation stage.
- `get_name(self) -> 'str'`
  - Get stage name.
- `validate(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate prerequisites for validation.
- `validate_outputs(self, context: 'PipelineContext') -> 'Tuple[bool, Optional[str]]'`
  - Validate stage outputs after execution (optional).

---

## Pipeline.Orchestrator

**Module:** `pipeline.orchestrator`

### Module Description

Pipeline orchestrator with dependency resolution.

Executes pipeline stages in the correct order based on dependencies,
with support for retry policies, error handling, and observability.

### Classes

#### `PipelineOrchestrator`

Orchestrates multi-stage pipeline with dependency resolution.

Example:
    stages = [
        StageDefinition("convert", ConversionStage(), []),
        StageDefinition("calibrate", CalibrationStage(), ["convert"]),
        StageDefinition("image", ImagingStage(), ["calibrate"]),
    ]
    orchestrator = PipelineOrchestrator(stages)
    result = orchestrator.execute(initial_context)

**Methods:**

- `execute(self, initial_context: 'PipelineContext') -> 'PipelineResult'`
  - Execute pipeline respecting dependencies.

#### `PipelineResult`

Result of pipeline execution.

#### `PipelineStatus`

Overall pipeline execution status.

#### `StageDefinition`

Definition of a pipeline stage with metadata.

#### `StageResult`

Result of executing a single stage.

---

## Pipeline.Config

**Module:** `pipeline.config`

### Module Description

Unified configuration system for pipeline execution.

Provides type-safe, validated configuration using Pydantic with support for
multiple configuration sources (environment variables, files, dictionaries).

### Classes

#### `CalibrationConfig`

Configuration for calibration stage.

**Methods:**

- `construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
- `from_orm(obj: 'Any') -> 'Self'`
- `model_construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
  - Creates a new instance of the `Model` class with validated data.
- `model_json_schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', schema_generator: 'type[GenerateJsonSchema]' = <class 'pydantic.json_schema.GenerateJsonSchema'>, mode: 'JsonSchemaMode' = 'validation') -> 'dict[str, Any]'`
  - Generates a JSON schema for a model class.
- `model_parametrized_name(params: 'tuple[type[Any], ...]') -> 'str'`
  - Compute the class name for parametrizations of generic classes.
- `model_rebuild(*, force: 'bool' = False, raise_errors: 'bool' = True, _parent_namespace_depth: 'int' = 2, _types_namespace: 'MappingNamespace | None' = None) -> 'bool | None'`
  - Try to rebuild the pydantic-core schema for the model.
- `model_validate(obj: 'Any', *, strict: 'bool | None' = None, from_attributes: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate a pydantic model instance.
- `model_validate_json(json_data: 'str | bytes | bytearray', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_validate_strings(obj: 'Any', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate the given object with string data against the Pydantic model.
- `parse_file(path: 'str | Path', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `parse_obj(obj: 'Any') -> 'Self'`
- `parse_raw(b: 'str | bytes', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}') -> 'Dict[str, Any]'`
- `schema_json(*, by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', **dumps_kwargs: 'Any') -> 'str'`
- `update_forward_refs(**localns: 'Any') -> 'None'`
- `validate(value: 'Any') -> 'Self'`
- `copy(self, *, include: 'AbstractSetIntStr | MappingIntStrAny | None' = None, exclude: 'AbstractSetIntStr | MappingIntStrAny | None' = None, update: 'Dict[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - Returns a copy of the model.
- `dict(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False) -> 'Dict[str, Any]'`
- `json(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, encoder: 'Callable[[Any], Any] | None' = PydanticUndefined, models_as_dict: 'bool' = PydanticUndefined, **dumps_kwargs: 'Any') -> 'str'`
- `model_copy(self, *, update: 'Mapping[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_dump(self, *, mode: "Literal['json', 'python'] | str" = 'python', include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'dict[str, Any]'`
  - !!! abstract "Usage Documentation"
- `model_dump_json(self, *, indent: 'int | None' = None, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'str'`
  - !!! abstract "Usage Documentation"
- `model_post_init(self, context: 'Any', /) -> 'None'`
  - Override this method to perform additional initialization after `__init__` and `model_construct`.

#### `ConversionConfig`

Configuration for conversion stage (UVH5 → MS).

**Methods:**

- `construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
- `from_orm(obj: 'Any') -> 'Self'`
- `model_construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
  - Creates a new instance of the `Model` class with validated data.
- `model_json_schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', schema_generator: 'type[GenerateJsonSchema]' = <class 'pydantic.json_schema.GenerateJsonSchema'>, mode: 'JsonSchemaMode' = 'validation') -> 'dict[str, Any]'`
  - Generates a JSON schema for a model class.
- `model_parametrized_name(params: 'tuple[type[Any], ...]') -> 'str'`
  - Compute the class name for parametrizations of generic classes.
- `model_rebuild(*, force: 'bool' = False, raise_errors: 'bool' = True, _parent_namespace_depth: 'int' = 2, _types_namespace: 'MappingNamespace | None' = None) -> 'bool | None'`
  - Try to rebuild the pydantic-core schema for the model.
- `model_validate(obj: 'Any', *, strict: 'bool | None' = None, from_attributes: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate a pydantic model instance.
- `model_validate_json(json_data: 'str | bytes | bytearray', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_validate_strings(obj: 'Any', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate the given object with string data against the Pydantic model.
- `parse_file(path: 'str | Path', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `parse_obj(obj: 'Any') -> 'Self'`
- `parse_raw(b: 'str | bytes', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}') -> 'Dict[str, Any]'`
- `schema_json(*, by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', **dumps_kwargs: 'Any') -> 'str'`
- `update_forward_refs(**localns: 'Any') -> 'None'`
- `validate(value: 'Any') -> 'Self'`
- `copy(self, *, include: 'AbstractSetIntStr | MappingIntStrAny | None' = None, exclude: 'AbstractSetIntStr | MappingIntStrAny | None' = None, update: 'Dict[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - Returns a copy of the model.
- `dict(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False) -> 'Dict[str, Any]'`
- `json(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, encoder: 'Callable[[Any], Any] | None' = PydanticUndefined, models_as_dict: 'bool' = PydanticUndefined, **dumps_kwargs: 'Any') -> 'str'`
- `model_copy(self, *, update: 'Mapping[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_dump(self, *, mode: "Literal['json', 'python'] | str" = 'python', include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'dict[str, Any]'`
  - !!! abstract "Usage Documentation"
- `model_dump_json(self, *, indent: 'int | None' = None, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'str'`
  - !!! abstract "Usage Documentation"
- `model_post_init(self, context: 'Any', /) -> 'None'`
  - Override this method to perform additional initialization after `__init__` and `model_construct`.

#### `CrossMatchConfig`

Configuration for cross-matching stage.

**Methods:**

- `construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
- `from_orm(obj: 'Any') -> 'Self'`
- `model_construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
  - Creates a new instance of the `Model` class with validated data.
- `model_json_schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', schema_generator: 'type[GenerateJsonSchema]' = <class 'pydantic.json_schema.GenerateJsonSchema'>, mode: 'JsonSchemaMode' = 'validation') -> 'dict[str, Any]'`
  - Generates a JSON schema for a model class.
- `model_parametrized_name(params: 'tuple[type[Any], ...]') -> 'str'`
  - Compute the class name for parametrizations of generic classes.
- `model_rebuild(*, force: 'bool' = False, raise_errors: 'bool' = True, _parent_namespace_depth: 'int' = 2, _types_namespace: 'MappingNamespace | None' = None) -> 'bool | None'`
  - Try to rebuild the pydantic-core schema for the model.
- `model_validate(obj: 'Any', *, strict: 'bool | None' = None, from_attributes: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate a pydantic model instance.
- `model_validate_json(json_data: 'str | bytes | bytearray', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_validate_strings(obj: 'Any', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate the given object with string data against the Pydantic model.
- `parse_file(path: 'str | Path', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `parse_obj(obj: 'Any') -> 'Self'`
- `parse_raw(b: 'str | bytes', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}') -> 'Dict[str, Any]'`
- `schema_json(*, by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', **dumps_kwargs: 'Any') -> 'str'`
- `update_forward_refs(**localns: 'Any') -> 'None'`
- `validate(value: 'Any') -> 'Self'`
- `copy(self, *, include: 'AbstractSetIntStr | MappingIntStrAny | None' = None, exclude: 'AbstractSetIntStr | MappingIntStrAny | None' = None, update: 'Dict[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - Returns a copy of the model.
- `dict(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False) -> 'Dict[str, Any]'`
- `json(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, encoder: 'Callable[[Any], Any] | None' = PydanticUndefined, models_as_dict: 'bool' = PydanticUndefined, **dumps_kwargs: 'Any') -> 'str'`
- `model_copy(self, *, update: 'Mapping[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_dump(self, *, mode: "Literal['json', 'python'] | str" = 'python', include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'dict[str, Any]'`
  - !!! abstract "Usage Documentation"
- `model_dump_json(self, *, indent: 'int | None' = None, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'str'`
  - !!! abstract "Usage Documentation"
- `model_post_init(self, context: 'Any', /) -> 'None'`
  - Override this method to perform additional initialization after `__init__` and `model_construct`.

#### `ImagingConfig`

Configuration for imaging stage.

**Methods:**

- `construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
- `from_orm(obj: 'Any') -> 'Self'`
- `model_construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
  - Creates a new instance of the `Model` class with validated data.
- `model_json_schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', schema_generator: 'type[GenerateJsonSchema]' = <class 'pydantic.json_schema.GenerateJsonSchema'>, mode: 'JsonSchemaMode' = 'validation') -> 'dict[str, Any]'`
  - Generates a JSON schema for a model class.
- `model_parametrized_name(params: 'tuple[type[Any], ...]') -> 'str'`
  - Compute the class name for parametrizations of generic classes.
- `model_rebuild(*, force: 'bool' = False, raise_errors: 'bool' = True, _parent_namespace_depth: 'int' = 2, _types_namespace: 'MappingNamespace | None' = None) -> 'bool | None'`
  - Try to rebuild the pydantic-core schema for the model.
- `model_validate(obj: 'Any', *, strict: 'bool | None' = None, from_attributes: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate a pydantic model instance.
- `model_validate_json(json_data: 'str | bytes | bytearray', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_validate_strings(obj: 'Any', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate the given object with string data against the Pydantic model.
- `parse_file(path: 'str | Path', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `parse_obj(obj: 'Any') -> 'Self'`
- `parse_raw(b: 'str | bytes', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}') -> 'Dict[str, Any]'`
- `schema_json(*, by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', **dumps_kwargs: 'Any') -> 'str'`
- `update_forward_refs(**localns: 'Any') -> 'None'`
- `validate(value: 'Any') -> 'Self'`
- `copy(self, *, include: 'AbstractSetIntStr | MappingIntStrAny | None' = None, exclude: 'AbstractSetIntStr | MappingIntStrAny | None' = None, update: 'Dict[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - Returns a copy of the model.
- `dict(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False) -> 'Dict[str, Any]'`
- `json(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, encoder: 'Callable[[Any], Any] | None' = PydanticUndefined, models_as_dict: 'bool' = PydanticUndefined, **dumps_kwargs: 'Any') -> 'str'`
- `model_copy(self, *, update: 'Mapping[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_dump(self, *, mode: "Literal['json', 'python'] | str" = 'python', include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'dict[str, Any]'`
  - !!! abstract "Usage Documentation"
- `model_dump_json(self, *, indent: 'int | None' = None, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'str'`
  - !!! abstract "Usage Documentation"
- `model_post_init(self, context: 'Any', /) -> 'None'`
  - Override this method to perform additional initialization after `__init__` and `model_construct`.

#### `PathsConfig`

Path configuration for pipeline execution.

**Methods:**

- `construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
- `from_orm(obj: 'Any') -> 'Self'`
- `model_construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
  - Creates a new instance of the `Model` class with validated data.
- `model_json_schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', schema_generator: 'type[GenerateJsonSchema]' = <class 'pydantic.json_schema.GenerateJsonSchema'>, mode: 'JsonSchemaMode' = 'validation') -> 'dict[str, Any]'`
  - Generates a JSON schema for a model class.
- `model_parametrized_name(params: 'tuple[type[Any], ...]') -> 'str'`
  - Compute the class name for parametrizations of generic classes.
- `model_rebuild(*, force: 'bool' = False, raise_errors: 'bool' = True, _parent_namespace_depth: 'int' = 2, _types_namespace: 'MappingNamespace | None' = None) -> 'bool | None'`
  - Try to rebuild the pydantic-core schema for the model.
- `model_validate(obj: 'Any', *, strict: 'bool | None' = None, from_attributes: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate a pydantic model instance.
- `model_validate_json(json_data: 'str | bytes | bytearray', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_validate_strings(obj: 'Any', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate the given object with string data against the Pydantic model.
- `parse_file(path: 'str | Path', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `parse_obj(obj: 'Any') -> 'Self'`
- `parse_raw(b: 'str | bytes', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}') -> 'Dict[str, Any]'`
- `schema_json(*, by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', **dumps_kwargs: 'Any') -> 'str'`
- `update_forward_refs(**localns: 'Any') -> 'None'`
- `validate(value: 'Any') -> 'Self'`
- `copy(self, *, include: 'AbstractSetIntStr | MappingIntStrAny | None' = None, exclude: 'AbstractSetIntStr | MappingIntStrAny | None' = None, update: 'Dict[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - Returns a copy of the model.
- `dict(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False) -> 'Dict[str, Any]'`
- `json(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, encoder: 'Callable[[Any], Any] | None' = PydanticUndefined, models_as_dict: 'bool' = PydanticUndefined, **dumps_kwargs: 'Any') -> 'str'`
- `model_copy(self, *, update: 'Mapping[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_dump(self, *, mode: "Literal['json', 'python'] | str" = 'python', include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'dict[str, Any]'`
  - !!! abstract "Usage Documentation"
- `model_dump_json(self, *, indent: 'int | None' = None, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'str'`
  - !!! abstract "Usage Documentation"
- `model_post_init(self, context: 'Any', /) -> 'None'`
  - Override this method to perform additional initialization after `__init__` and `model_construct`.

#### `PhotometryConfig`

Configuration for adaptive binning photometry stage.

**Methods:**

- `construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
- `from_orm(obj: 'Any') -> 'Self'`
- `model_construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
  - Creates a new instance of the `Model` class with validated data.
- `model_json_schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', schema_generator: 'type[GenerateJsonSchema]' = <class 'pydantic.json_schema.GenerateJsonSchema'>, mode: 'JsonSchemaMode' = 'validation') -> 'dict[str, Any]'`
  - Generates a JSON schema for a model class.
- `model_parametrized_name(params: 'tuple[type[Any], ...]') -> 'str'`
  - Compute the class name for parametrizations of generic classes.
- `model_rebuild(*, force: 'bool' = False, raise_errors: 'bool' = True, _parent_namespace_depth: 'int' = 2, _types_namespace: 'MappingNamespace | None' = None) -> 'bool | None'`
  - Try to rebuild the pydantic-core schema for the model.
- `model_validate(obj: 'Any', *, strict: 'bool | None' = None, from_attributes: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate a pydantic model instance.
- `model_validate_json(json_data: 'str | bytes | bytearray', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_validate_strings(obj: 'Any', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate the given object with string data against the Pydantic model.
- `parse_file(path: 'str | Path', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `parse_obj(obj: 'Any') -> 'Self'`
- `parse_raw(b: 'str | bytes', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}') -> 'Dict[str, Any]'`
- `schema_json(*, by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', **dumps_kwargs: 'Any') -> 'str'`
- `update_forward_refs(**localns: 'Any') -> 'None'`
- `validate(value: 'Any') -> 'Self'`
- `copy(self, *, include: 'AbstractSetIntStr | MappingIntStrAny | None' = None, exclude: 'AbstractSetIntStr | MappingIntStrAny | None' = None, update: 'Dict[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - Returns a copy of the model.
- `dict(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False) -> 'Dict[str, Any]'`
- `json(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, encoder: 'Callable[[Any], Any] | None' = PydanticUndefined, models_as_dict: 'bool' = PydanticUndefined, **dumps_kwargs: 'Any') -> 'str'`
- `model_copy(self, *, update: 'Mapping[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_dump(self, *, mode: "Literal['json', 'python'] | str" = 'python', include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'dict[str, Any]'`
  - !!! abstract "Usage Documentation"
- `model_dump_json(self, *, indent: 'int | None' = None, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'str'`
  - !!! abstract "Usage Documentation"
- `model_post_init(self, context: 'Any', /) -> 'None'`
  - Override this method to perform additional initialization after `__init__` and `model_construct`.

#### `PipelineConfig`

Complete pipeline configuration.

This is the single source of truth for all pipeline configuration.
Supports loading from environment variables, files, or dictionaries.

**Methods:**

- `construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
- `from_dict(data: 'Dict[str, Any]') -> 'PipelineConfig'`
  - Load configuration from dictionary (e.g., API request).
- `from_env(validate_paths: 'bool' = True, required_disk_gb: 'float' = 50.0) -> 'PipelineConfig'`
  - Load configuration from environment variables.
- `from_orm(obj: 'Any') -> 'Self'`
- `from_yaml(yaml_path: 'Path | str', validate_paths: 'bool' = True, required_disk_gb: 'float' = 50.0) -> 'PipelineConfig'`
  - Load configuration from YAML file.
- `model_construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
  - Creates a new instance of the `Model` class with validated data.
- `model_json_schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', schema_generator: 'type[GenerateJsonSchema]' = <class 'pydantic.json_schema.GenerateJsonSchema'>, mode: 'JsonSchemaMode' = 'validation') -> 'dict[str, Any]'`
  - Generates a JSON schema for a model class.
- `model_parametrized_name(params: 'tuple[type[Any], ...]') -> 'str'`
  - Compute the class name for parametrizations of generic classes.
- `model_rebuild(*, force: 'bool' = False, raise_errors: 'bool' = True, _parent_namespace_depth: 'int' = 2, _types_namespace: 'MappingNamespace | None' = None) -> 'bool | None'`
  - Try to rebuild the pydantic-core schema for the model.
- `model_validate(obj: 'Any', *, strict: 'bool | None' = None, from_attributes: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate a pydantic model instance.
- `model_validate_json(json_data: 'str | bytes | bytearray', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_validate_strings(obj: 'Any', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate the given object with string data against the Pydantic model.
- `parse_file(path: 'str | Path', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `parse_obj(obj: 'Any') -> 'Self'`
- `parse_raw(b: 'str | bytes', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}') -> 'Dict[str, Any]'`
- `schema_json(*, by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', **dumps_kwargs: 'Any') -> 'str'`
- `update_forward_refs(**localns: 'Any') -> 'None'`
- `validate(value: 'Any') -> 'Self'`
- `copy(self, *, include: 'AbstractSetIntStr | MappingIntStrAny | None' = None, exclude: 'AbstractSetIntStr | MappingIntStrAny | None' = None, update: 'Dict[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - Returns a copy of the model.
- `dict(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False) -> 'Dict[str, Any]'`
- `json(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, encoder: 'Callable[[Any], Any] | None' = PydanticUndefined, models_as_dict: 'bool' = PydanticUndefined, **dumps_kwargs: 'Any') -> 'str'`
- `model_copy(self, *, update: 'Mapping[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_dump(self, *, mode: "Literal['json', 'python'] | str" = 'python', include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'dict[str, Any]'`
  - !!! abstract "Usage Documentation"
- `model_dump_json(self, *, indent: 'int | None' = None, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'str'`
  - !!! abstract "Usage Documentation"
- `model_post_init(self, context: 'Any', /) -> 'None'`
  - Override this method to perform additional initialization after `__init__` and `model_construct`.
- `to_dict(self) -> 'Dict[str, Any]'`
  - Convert configuration to dictionary.
- `to_yaml(self, yaml_path: 'Path | str') -> 'None'`
  - Save configuration to YAML file.

#### `ValidationConfig`

Configuration for validation stage.

**Methods:**

- `construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
- `from_orm(obj: 'Any') -> 'Self'`
- `model_construct(_fields_set: 'set[str] | None' = None, **values: 'Any') -> 'Self'`
  - Creates a new instance of the `Model` class with validated data.
- `model_json_schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', schema_generator: 'type[GenerateJsonSchema]' = <class 'pydantic.json_schema.GenerateJsonSchema'>, mode: 'JsonSchemaMode' = 'validation') -> 'dict[str, Any]'`
  - Generates a JSON schema for a model class.
- `model_parametrized_name(params: 'tuple[type[Any], ...]') -> 'str'`
  - Compute the class name for parametrizations of generic classes.
- `model_rebuild(*, force: 'bool' = False, raise_errors: 'bool' = True, _parent_namespace_depth: 'int' = 2, _types_namespace: 'MappingNamespace | None' = None) -> 'bool | None'`
  - Try to rebuild the pydantic-core schema for the model.
- `model_validate(obj: 'Any', *, strict: 'bool | None' = None, from_attributes: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate a pydantic model instance.
- `model_validate_json(json_data: 'str | bytes | bytearray', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_validate_strings(obj: 'Any', *, strict: 'bool | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, by_name: 'bool | None' = None) -> 'Self'`
  - Validate the given object with string data against the Pydantic model.
- `parse_file(path: 'str | Path', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `parse_obj(obj: 'Any') -> 'Self'`
- `parse_raw(b: 'str | bytes', *, content_type: 'str | None' = None, encoding: 'str' = 'utf8', proto: 'DeprecatedParseProtocol | None' = None, allow_pickle: 'bool' = False) -> 'Self'`
- `schema(by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}') -> 'Dict[str, Any]'`
- `schema_json(*, by_alias: 'bool' = True, ref_template: 'str' = '#/$defs/{model}', **dumps_kwargs: 'Any') -> 'str'`
- `update_forward_refs(**localns: 'Any') -> 'None'`
- `validate(value: 'Any') -> 'Self'`
- `copy(self, *, include: 'AbstractSetIntStr | MappingIntStrAny | None' = None, exclude: 'AbstractSetIntStr | MappingIntStrAny | None' = None, update: 'Dict[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - Returns a copy of the model.
- `dict(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False) -> 'Dict[str, Any]'`
- `json(self, *, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, by_alias: 'bool' = False, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, encoder: 'Callable[[Any], Any] | None' = PydanticUndefined, models_as_dict: 'bool' = PydanticUndefined, **dumps_kwargs: 'Any') -> 'str'`
- `model_copy(self, *, update: 'Mapping[str, Any] | None' = None, deep: 'bool' = False) -> 'Self'`
  - !!! abstract "Usage Documentation"
- `model_dump(self, *, mode: "Literal['json', 'python'] | str" = 'python', include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'dict[str, Any]'`
  - !!! abstract "Usage Documentation"
- `model_dump_json(self, *, indent: 'int | None' = None, include: 'IncEx | None' = None, exclude: 'IncEx | None' = None, context: 'Any | None' = None, by_alias: 'bool | None' = None, exclude_unset: 'bool' = False, exclude_defaults: 'bool' = False, exclude_none: 'bool' = False, round_trip: 'bool' = False, warnings: "bool | Literal['none', 'warn', 'error']" = True, fallback: 'Callable[[Any], Any] | None' = None, serialize_as_any: 'bool' = False) -> 'str'`
  - !!! abstract "Usage Documentation"
- `model_post_init(self, context: 'Any', /) -> 'None'`
  - Override this method to perform additional initialization after `__init__` and `model_construct`.

---

## Pipeline.Context

**Module:** `pipeline.context`

### Module Description

Pipeline context for passing data between stages.

The PipelineContext is an immutable data structure that carries configuration,
inputs, outputs, and metadata through the pipeline execution.

### Classes

#### `PipelineContext`

Immutable context passed between pipeline stages.

The context is immutable to prevent accidental mutations. Use `with_output()`
to create new contexts with additional outputs.

Attributes:
    config: Pipeline configuration
    job_id: Optional job ID for tracking
    inputs: Stage inputs (e.g., time ranges, file paths)
    outputs: Stage outputs (e.g., created MS paths, image paths)
    metadata: Additional metadata (e.g., execution timestamps, metrics)
    state_repository: Optional state repository for persistence

**Methods:**

- `with_metadata(self, key: 'str', value: 'Any') -> 'PipelineContext'`
  - Return new context with added metadata.
- `with_output(self, key: 'str', value: 'Any') -> 'PipelineContext'`
  - Return new context with added output.
- `with_outputs(self, outputs: 'Dict[str, Any]') -> 'PipelineContext'`
  - Return new context with multiple outputs added.

---

## Pipeline.Workflows

**Module:** `pipeline.workflows`

### Module Description

Workflow composition and reusable workflow definitions.

Provides builders and standard workflows for common pipeline patterns.

### Classes

#### `WorkflowBuilder`

Builder for creating reusable workflows.

Example:
    workflow = (WorkflowBuilder()
        .add_stage("convert", ConversionStage())
        .add_stage("calibrate", CalibrationStage(), depends_on=["convert"])
        .add_stage("image", ImagingStage(), depends_on=["calibrate"])
        .build())

**Methods:**

- `add_stage(self, name: 'str', stage: 'PipelineStage', depends_on: 'Optional[List[str]]' = None, retry_policy: 'Optional[RetryPolicy]' = None, timeout: 'Optional[float]' = None) -> 'WorkflowBuilder'`
  - Add stage to workflow.
- `build(self) -> 'PipelineOrchestrator'`
  - Build pipeline orchestrator.

### Functions

#### `quicklook_workflow(config: 'PipelineConfig') -> 'PipelineOrchestrator'`

Quicklook workflow: Convert → Image (no calibration).

Args:
    config: Pipeline configuration

Returns:
    PipelineOrchestrator for quicklook workflow

#### `reprocessing_workflow(config: 'PipelineConfig') -> 'PipelineOrchestrator'`

Reprocessing workflow: Calibrate → Image (MS already exists).

Args:
    config: Pipeline configuration

Returns:
    PipelineOrchestrator for reprocessing workflow

#### `standard_imaging_workflow(config: 'PipelineConfig') -> 'PipelineOrchestrator'`

Standard workflow: Convert → Solve Calibration → Apply Calibration → Image.

This workflow performs a complete end-to-end pipeline:
1. Convert UVH5 files to Measurement Sets
2. Solve calibration tables (delay/K, bandpass/BP, gains/G)
3. Apply calibration solutions to the MS
4. Image the calibrated MS

Args:
    config: Pipeline configuration

Returns:
    PipelineOrchestrator for standard imaging workflow

---

## Conversion.Uvh5 To Ms

**Module:** `conversion.uvh5_to_ms`

### Module Description

UVH5 to CASA Measurement Set Converter.

This module provides a single-file/directory writer for converting UVH5 data
to a CASA Measurement Set (MS). It leverages shared helpers for phasing and
finalization to ensure consistency with the main conversion pipeline.

### Functions

#### `add_args(parser: 'argparse.ArgumentParser') -> 'None'`

Add arguments to the parser.

#### `convert_directory(input_dir: 'str', output_dir: 'str', pattern: 'str' = '*.hdf5', add_imaging_columns: 'bool' = True, create_time_binned_fields: 'bool' = False, field_time_bin_minutes: 'float' = 5.0, write_recommendations: 'bool' = True, enable_phasing: 'bool' = True, phase_reference_time: 'Optional[float]' = None) -> 'None'`

Convert all UVH5 files in a directory to MS format.

Parameters
----------
input_dir : str
    Input directory containing UVH5 files
output_dir : str
    Output directory for MS files
pattern : str
    File pattern to match
add_imaging_columns : bool
    Whether to add imaging columns
create_time_binned_fields : bool
    Whether to create time-binned fields for drift scans
field_time_bin_minutes : float
    Time bin size in minutes for field creation

Raises
------
ValueError
    If input parameters are invalid
FileNotFoundError
    If input directory does not exist
RuntimeError
    If directory conversion fails

#### `convert_single_file(input_file: 'str', output_file: 'str', add_imaging_columns: 'bool' = True, create_time_binned_fields: 'bool' = False, field_time_bin_minutes: 'float' = 5.0, write_recommendations: 'bool' = True, enable_phasing: 'bool' = True, phase_reference_time: 'Optional[float]' = None) -> 'None'`

Convert a single UVH5 file to CASA Measurement Set (MS) format.

This is the main entry point for converting individual UVH5 files to MS
format. The function handles the complete conversion pipeline including
phasing, antenna position setup, and MS configuration.

**Conversion Process:**

1. Reads UVH5 file using pyuvdata
2. Sets antenna positions and telescope metadata
3. Phases data to meridian (if enabled)
4. Writes to CASA MS format
5. Configures MS for imaging (if add_imaging_columns=True)

Parameters
----------
input_file : str
    Path to input UVH5 file. Must exist and be readable.
output_file : str
    Path to output MS file (directory). Will be created if it doesn't
    exist. Parent directory must exist.
add_imaging_columns : bool, optional
    Whether to add imaging columns (MODEL_DATA, CORRECTED_DATA) and
    configure MS for imaging. Default: True
create_time_binned_fields : bool, optional
    Whether to create time-binned fields for drift scans. If True,
    creates separate fields for each time bin. Default: False
field_time_bin_minutes : float, optional
    Time bin size in minutes for field creation (if
    create_time_binned_fields=True). Default: 5.0
write_recommendations : bool, optional
    Whether to write conversion recommendations to a file.
    Default: True
enable_phasing : bool, optional
    Whether to phase data to meridian. Default: True
phase_reference_time : float, optional
    Reference time for phasing (MJD). If None, uses observation mid-time.
    Default: None

Raises
------
ValueError
    If input parameters are invalid (e.g., negative time bin size)
FileNotFoundError
    If input file does not exist
PermissionError
    If input file is not readable or output directory is not writable
ConversionError
    If conversion fails (e.g., invalid UVH5 format, write errors)

Examples
--------
Basic conversion:

>>> from dsa110_contimg.conversion import convert_single_file
>>> convert_single_file(
...     "observation.uvh5",
...     "observation.ms"
... )

Convert with time-binned fields for drift scan:

>>> convert_single_file(
...     "drift_scan.uvh5",
...     "drift_scan.ms",
...     create_time_binned_fields=True,
...     field_time_bin_minutes=10.0
... )

Convert without phasing (for testing):

>>> convert_single_file(
...     "test.uvh5",
...     "test.ms",
...     enable_phasing=False
... )

Notes
-----
- The output MS will be a directory, not a single file
- If the output directory already exists, it will be overwritten
- For production use, prefer `convert_subband_groups_to_ms()` which
  handles complete subband groups
- After conversion, the MS is ready for calibration and imaging

#### `create_parser() -> 'argparse.ArgumentParser'`

Create the parser for the converter.

#### `find_uvh5_files(input_dir: 'str', pattern: 'str' = '*.hdf5') -> 'List[str]'`

Find UVH5 files in a directory.

Parameters
----------
input_dir : str
    Directory to search
pattern : str
    File pattern to match

Returns
-------
List[str]
    List of UVH5 file paths

#### `main(args: 'argparse.Namespace' = None) -> 'int'`

Main function for the converter.

#### `read_uvh5_file(filepath: 'str', create_time_binned_fields: 'bool' = False, field_time_bin_minutes: 'float' = 5.0) -> 'UVData'`

Read a UVH5 file using pyuvdata.

Parameters
----------
filepath : str
    Path to the UVH5 file
create_time_binned_fields : bool
    Whether to create time-binned fields for drift scans
field_time_bin_minutes : float
    Time bin size in minutes for field creation
    (if create_time_binned_fields=True)

Returns
-------
UVData
    UVData object containing the data

Raises
------
FileNotFoundError
    If the UVH5 file does not exist
ValueError
    If the file is not a valid UVH5 file or has critical data issues
RuntimeError
    If there are unrecoverable errors during processing

#### `write_ms_file(uvd: 'UVData', output_path: 'str', add_imaging_columns: 'bool' = True) -> 'None'`

Write UVData to CASA Measurement Set.

Parameters
----------
uvd : UVData
    UVData object to write
output_path : str
    Path for the output MS file
add_imaging_columns : bool
    Whether to add imaging columns (MODEL_DATA, CORRECTED_DATA)

Raises
------
ValueError
    If input parameters are invalid
RuntimeError
    If MS writing fails
PermissionError
    If output directory cannot be created or written to

---

## Conversion.Streaming.Streaming Converter

**Module:** `conversion.streaming.streaming_converter`

### Module Description

Streaming converter service for DSA-110 UVH5 subband groups.

This daemon watches an ingest directory for new *_sb??.hdf5 files, queues
complete 16-subband groups, and invokes the existing batch converter on each
group using a scratch directory for staging.

The queue is persisted in SQLite so the service can resume after restarts.

### Classes

#### `QueueDB`

SQLite-backed queue tracking subband arrivals and processing state.

**Methods:**

- `acquire_next_pending(self) -> Optional[str]`
  - Acquire the next pending group atomically.
- `bootstrap_directory(self, input_dir: pathlib.Path) -> None`
- `close(self) -> None`
- `group_files(self, group_id: str) -> List[str]`
  - Get list of file paths for a group.
- `record_metrics(self, group_id: str, **kwargs) -> None`
  - Record performance metrics for a group.
- `record_subband(self, group_id: str, subband_idx: int, file_path: pathlib.Path) -> None`
  - Record a subband file arrival.
- `update_state(self, group_id: str, state: str, error: Optional[str] = None) -> None`
  - Update the state of a group in the queue.

#### `_FSHandler`

Watchdog handler to record arriving subband files.

**Methods:**

- `dispatch(self, event: 'FileSystemEvent') -> 'None'`
  - Dispatches events to the appropriate methods.
- `on_any_event(self, event: 'FileSystemEvent') -> 'None'`
  - Catch-all event handler.
- `on_closed(self, event: 'FileClosedEvent') -> 'None'`
  - Called when a file opened for writing is closed.
- `on_closed_no_write(self, event: 'FileClosedNoWriteEvent') -> 'None'`
  - Called when a file opened for reading is closed.
- `on_created(self, event)`
  - Called when a file or directory is created.
- `on_deleted(self, event: 'DirDeletedEvent | FileDeletedEvent') -> 'None'`
  - Called when a file or directory is deleted.
- `on_modified(self, event: 'DirModifiedEvent | FileModifiedEvent') -> 'None'`
  - Called when a file or directory is modified.
- `on_moved(self, event)`
  - Called when a file or a directory is moved or renamed.
- `on_opened(self, event: 'FileOpenedEvent') -> 'None'`
  - Called when a file is opened.

### Functions

#### `build_parser() -> argparse.ArgumentParser`

#### `main(argv: Optional[List[str]] = None) -> int`

#### `override_env(values: Dict[str, str]) -> Iterator[NoneType]`

Temporarily override environment variables.

#### `parse_subband_info(path: pathlib.Path) -> Optional[Tuple[str, int]]`

Extract (group_id, subband_idx) from a filename, or None if not matched.

#### `setup_logging(level: str) -> None`

---

## Calibration.Calibration

**Module:** `calibration.calibration`

### Functions

#### `solve_bandpass(ms: str, cal_field: str, refant: str, ktable: Optional[str], table_prefix: Optional[str] = None, set_model: bool = True, model_standard: str = 'Perley-Butler 2017', combine_fields: bool = False, combine_spw: bool = False, minsnr: float = 5.0, uvrange: str = '', prebandpass_phase_table: Optional[str] = None, bp_smooth_type: Optional[str] = None, bp_smooth_window: Optional[int] = None, peak_field_idx: Optional[int] = None, combine: Optional[str] = None) -> List[str]`

Solve bandpass using CASA bandpass task with bandtype='B'.

This solves for frequency-dependent bandpass correction using the dedicated
bandpass task, which properly handles per-channel solutions. The bandpass task
requires a source model (smodel) which is provided via MODEL_DATA column.

**PRECONDITION**: MODEL_DATA must be populated before calling this function.
This ensures consistent, reliable calibration results across all calibrators
(bright or faint). The calling code should verify MODEL_DATA exists and is
populated before invoking solve_bandpass().

**NOTE**: `ktable` parameter is kept for API compatibility but is NOT used
(K-calibration is not used for DSA-110 connected-element array).

#### `solve_delay(ms: str, cal_field: str, refant: str, table_prefix: Optional[str] = None, combine_spw: bool = False, t_slow: str = 'inf', t_fast: Optional[str] = '60s', uvrange: str = '', minsnr: float = 5.0, skip_slow: bool = False) -> List[str]`

Solve delay (K) on slow and optional fast timescales using CASA gaincal.

Uses casatasks.gaincal with gaintype='K' to avoid explicit casatools
calibrater usage, which can be unstable in some notebook environments.

**PRECONDITION**: MODEL_DATA must be populated before calling this function.
This ensures consistent, reliable calibration results across all calibrators
(bright or faint). The calling code should verify MODEL_DATA exists and is
populated before invoking solve_delay().

#### `solve_gains(ms: str, cal_field: str, refant: str, ktable: Optional[str], bptables: List[str], table_prefix: Optional[str] = None, t_short: str = '60s', combine_fields: bool = False, *, phase_only: bool = False, uvrange: str = '', solint: str = 'inf', minsnr: float = 5.0, peak_field_idx: Optional[int] = None) -> List[str]`

Solve gain amplitude and phase; optionally short-timescale.

**PRECONDITION**: MODEL_DATA must be populated before calling this function.
This ensures consistent, reliable calibration results across all calibrators
(bright or faint). The calling code should verify MODEL_DATA exists and is
populated before invoking solve_gains().

**PRECONDITION**: If `bptables` are provided, they must exist and be
compatible with the MS. This ensures consistent, reliable calibration results.

**NOTE**: `ktable` parameter is kept for API compatibility but is NOT used
(K-calibration is not used for DSA-110 connected-element array).

#### `solve_prebandpass_phase(ms: str, cal_field: str, refant: str, table_prefix: Optional[str] = None, combine_fields: bool = False, combine_spw: bool = False, uvrange: str = '', solint: str = 'inf', minsnr: float = 5.0, peak_field_idx: Optional[int] = None, minblperant: Optional[int] = None, spw: Optional[str] = None, table_name: Optional[str] = None) -> str`

Solve phase-only calibration before bandpass to correct phase drifts in raw data.

This phase-only calibration step is critical for uncalibrated raw data. It corrects
for time-dependent phase variations that cause decorrelation and low SNR in bandpass
calibration. This should be run BEFORE bandpass calibration.

**PRECONDITION**: MODEL_DATA must be populated before calling this function.

Returns:
    Path to phase-only calibration table (to be passed to bandpass via gaintable)

---

## Imaging.Spw Imaging

**Module:** `imaging.spw_imaging`

### Module Description

SPW selection and per-SPW imaging for adaptive binning.

This module provides functions to:
1. Query SPW information from Measurement Sets
2. Image individual SPWs
3. Image all SPWs and return paths for adaptive binning

### Classes

#### `SPWInfo`

Information about a spectral window.

### Functions

#### `get_spw_info(ms_path: 'str') -> 'List[SPWInfo]'`

Get SPW information from Measurement Set.

Args:
    ms_path: Path to Measurement Set

Returns:
    List of SPWInfo objects, one per SPW

Raises:
    RuntimeError: If casacore.tables is not available or MS cannot be read

#### `image_all_spws(ms_path: 'str', output_dir: 'Path', base_name: 'str' = 'spw', spw_ids: 'Optional[List[int]]' = None, parallel: 'bool' = False, max_workers: 'Optional[int]' = None, serialize_ms_access: 'bool' = False, **imaging_kwargs) -> 'List[Tuple[int, Path]]'`

Image all SPWs (or specified subset) and return paths.

Args:
    ms_path: Path to Measurement Set
    output_dir: Directory for output images
    base_name: Base name for output images (will append spw_id)
    spw_ids: Optional list of SPW IDs to image. If None, images all SPWs.
    parallel: If True, image SPWs in parallel (default: False)
    max_workers: Maximum number of parallel workers (default: CPU count)
    serialize_ms_access: If True, serialize MS access using file locking to
                       prevent CASA table lock conflicts when multiple
                       processes access the same MS (default: False)
    **imaging_kwargs: Additional arguments passed to image_ms()

Returns:
    List of (spw_id, image_path) tuples, sorted by SPW ID

Example:
    >>> spw_images = image_all_spws(
    ...     ms_path="data.ms",
    ...     output_dir=Path("images/"),
    ...     imsize=1024,
    ...     quality_tier="standard",
    ...     parallel=True,
    ...     max_workers=4,
    ...     serialize_ms_access=True,
    ... )
    >>> print(f"Imaged {len(spw_images)} SPWs")
    >>> for spw_id, img_path in spw_images:
    ...     print(f"SPW {spw_id}: {img_path}")

#### `image_spw(ms_path: 'str', spw_id: 'int', output_dir: 'Path', base_name: 'str' = 'spw', **imaging_kwargs) -> 'Path'`

Image a single SPW.

Args:
    ms_path: Path to Measurement Set
    spw_id: SPW ID to image (0-indexed)
    output_dir: Directory for output images
    base_name: Base name for output images (will append spw_id)
    **imaging_kwargs: Additional arguments passed to image_ms()

Returns:
    Path to primary beam corrected FITS image

Example:
    >>> image_path = image_spw(
    ...     ms_path="data.ms",
    ...     spw_id=0,
    ...     output_dir=Path("images/"),
    ...     imsize=1024,
    ...     quality_tier="standard",
    ... )
    >>> print(image_path)
    Path('images/spw0.img-image-pbcor.fits')

---

## Qa.Base

**Module:** `qa.base`

### Module Description

Base classes and protocols for QA validation system.

Provides abstraction layer for consistent validation patterns.

### Classes

#### `ValidationConfigurationError`

Raised when validation configuration is invalid.

#### `ValidationContext`

Context object passed to validators.

Contains all inputs and configuration needed for validation.

#### `ValidationError`

Base exception for validation errors.

#### `ValidationExecutionError`

Raised when validation execution fails.

#### `ValidationInputError`

Raised when validation inputs are invalid or missing.

#### `ValidationResult`

Base class for validation results.

All validation results should inherit from this or follow its structure.

**Methods:**

- `add_error(self, error: str)`
  - Add an error message.
- `add_warning(self, warning: str)`
  - Add a warning message.
- `to_dict(self) -> Dict[str, Any]`
  - Convert result to dictionary.

#### `Validator`

Protocol for validation functions.

All validators should follow this interface for consistency.

**Methods:**

- `validate(self, context: 'ValidationContext') -> 'ValidationResult'`
  - Run validation and return result.

---

## Qa.Fast Validation

**Module:** `qa.fast_validation`

### Module Description

Fast validation module for sub-60-second pipeline validation.

Implements tiered validation architecture with parallel execution and aggressive sampling.

### Classes

#### `TieredValidationResult`

Results from tiered validation.

**Methods:**

- `to_dict(self) -> Dict[str, Any]`
  - Convert to dictionary.

#### `ValidationMode`

Validation mode enumeration.

### Functions

#### `get_fast_config_for_mode(mode: dsa110_contimg.qa.fast_validation.ValidationMode) -> dsa110_contimg.qa.config.FastValidationConfig`

Get FastValidationConfig optimized for a specific validation mode.

Args:
    mode: ValidationMode enum value.

Returns:
    FastValidationConfig instance optimized for the mode.

#### `validate_pipeline_fast(ms_path: Optional[str] = None, caltables: Optional[List[str]] = None, image_paths: Optional[List[str]] = None, config: Optional[dsa110_contimg.qa.config.QAConfig] = None, fast_config: Optional[dsa110_contimg.qa.config.FastValidationConfig] = None, mode: Optional[dsa110_contimg.qa.fast_validation.ValidationMode] = None) -> dsa110_contimg.qa.fast_validation.TieredValidationResult`

Fast pipeline validation with tiered architecture and parallel execution.

Target: <60 seconds for standard mode, <30 seconds for fast mode.

Args:
    ms_path: Path to Measurement Set (optional).
    caltables: List of calibration table paths (optional).
    image_paths: List of image paths (optional).
    config: QAConfig instance (uses default if not provided).
    fast_config: FastValidationConfig instance (uses default if not provided).
    mode: ValidationMode enum (FAST/STANDARD/COMPREHENSIVE). If provided,
          overrides fast_config with mode-optimized settings.

Returns:
    TieredValidationResult with tier1, tier2, tier3 results and timing.

---

## Photometry.Forced

**Module:** `photometry.forced`

### Module Description

Forced photometry utilities on FITS images (PB-corrected mosaics or tiles).

Enhanced implementation with features from VAST forced_phot:
- Cluster fitting for blended sources
- Chi-squared goodness-of-fit metrics
- Optional noise maps (separate FITS files)
- Source injection for testing
- Weighted convolution (Condon 1997) for accurate flux measurement

### Classes

#### `ForcedPhotometryResult`

Result from forced photometry measurement.

#### `G2D`

2D Gaussian kernel for forced photometry.

Generates a 2D Gaussian kernel with specified FWHM and position angle.
Used for weighted convolution flux measurement (Condon 1997).

### Functions

#### `inject_source(fits_path: 'str', ra_deg: 'float', dec_deg: 'float', flux_jy: 'float', *, output_path: 'Optional[str]' = None, nbeam: 'float' = 15.0) -> 'str'`

Inject a fake source into a FITS image for testing.

Args:
    fits_path: Path to input FITS image
    ra_deg: Right ascension (degrees)
    dec_deg: Declination (degrees)
    flux_jy: Flux to inject (Jy/beam)
    output_path: Optional output path (default: overwrites input)
    nbeam: Size of injection region in units of beam major axis

Returns:
    Path to modified FITS file

#### `measure_forced_peak(fits_path: 'str', ra_deg: 'float', dec_deg: 'float', *, box_size_pix: 'int' = 5, annulus_pix: 'Tuple[int, int]' = (12, 20), noise_map_path: 'Optional[str]' = None, background_map_path: 'Optional[str]' = None, nbeam: 'float' = 3.0, use_weighted_convolution: 'bool' = True) -> 'ForcedPhotometryResult'`

Measure flux using forced photometry with optional weighted convolution.

Uses weighted convolution (Condon 1997) when beam information is available,
otherwise falls back to simple peak measurement.

Args:
    fits_path: Path to FITS image
    ra_deg: Right ascension (degrees)
    dec_deg: Declination (degrees)
    box_size_pix: Size of measurement box (pixels) - used for simple peak mode
    annulus_pix: Annulus for RMS estimation (r_in, r_out) pixels
    noise_map_path: Optional path to noise map FITS file
    background_map_path: Optional path to background map FITS file
    nbeam: Size of cutout in units of beam major axis (for weighted convolution)
    use_weighted_convolution: Use weighted convolution if beam info available

Returns:
    ForcedPhotometryResult with flux measurements and quality metrics

#### `measure_many(fits_path: 'str', coords: 'List[Tuple[float, float]]', *, box_size_pix: 'int' = 5, annulus_pix: 'Tuple[int, int]' = (12, 20), noise_map_path: 'Optional[str]' = None, background_map_path: 'Optional[str]' = None, use_cluster_fitting: 'bool' = False, cluster_threshold: 'float' = 1.5, nbeam: 'float' = 3.0) -> 'List[ForcedPhotometryResult]'`

Measure flux for multiple sources with optional cluster fitting.

Args:
    fits_path: Path to FITS image
    coords: List of (ra_deg, dec_deg) tuples
    box_size_pix: Size of measurement box (for simple peak mode)
    annulus_pix: Annulus for RMS estimation
    noise_map_path: Optional path to noise map FITS file
    background_map_path: Optional path to background map FITS file
    use_cluster_fitting: Enable cluster fitting for blended sources
    cluster_threshold: Cluster threshold in units of BMAJ (default 1.5)
    nbeam: Size of cutout in units of beam major axis

Returns:
    List of ForcedPhotometryResult objects

---

## Catalog.Crossmatch

**Module:** `catalog.crossmatch`

### Module Description

Cross-match sources in DSA-110 images with reference catalogs.

This module provides general-purpose cross-matching utilities for matching
detected sources with reference catalogs (NVSS, FIRST, RACS, etc.).

Based on VAST Post-Processing crossmatch.py patterns.

### Functions

#### `calculate_flux_scale(matches_df: pandas.core.frame.DataFrame, flux_ratio_col: str = 'flux_ratio') -> Tuple[uncertainties.core.AffineScalarFunc, uncertainties.core.AffineScalarFunc]`

Calculate flux scale correction factor.

Uses median flux ratio as a simple flux scale estimate.
For robust fitting, see calculate_flux_scale_robust().

Args:
    matches_df: DataFrame with cross-matched sources containing flux_ratio
    flux_ratio_col: Column name for flux ratio

Returns:
    Tuple of:
    - Flux correction factor (multiplicative)
    - Flux correction error

#### `calculate_positional_offsets(matches_df: pandas.core.frame.DataFrame) -> Tuple[astropy.units.quantity.Quantity, astropy.units.quantity.Quantity, astropy.units.quantity.Quantity, astropy.units.quantity.Quantity]`

Calculate median positional offsets and MAD between matched sources.

Args:
    matches_df: DataFrame with cross-matched sources containing:
        - dra_arcsec: RA offsets (arcsec)
        - ddec_arcsec: Dec offsets (arcsec)

Returns:
    Tuple of:
    - Median RA offset (Quantity)
    - Median Dec offset (Quantity)
    - MAD of RA offsets (Quantity)
    - MAD of Dec offsets (Quantity)

#### `cross_match_dataframes(detected_df: pandas.core.frame.DataFrame, catalog_df: pandas.core.frame.DataFrame, radius_arcsec: float = 10.0, detected_ra_col: str = 'ra_deg', detected_dec_col: str = 'dec_deg', catalog_ra_col: str = 'ra_deg', catalog_dec_col: str = 'dec_deg', detected_flux_col: Optional[str] = None, catalog_flux_col: Optional[str] = None, detected_id_col: Optional[str] = None, catalog_id_col: Optional[str] = None) -> pandas.core.frame.DataFrame`

Cross-match two DataFrames containing source positions.

Convenience wrapper around cross_match_sources for DataFrame inputs.

Args:
    detected_df: DataFrame with detected sources
    catalog_df: DataFrame with catalog sources
    radius_arcsec: Matching radius in arcseconds
    detected_ra_col: Column name for detected RA
    detected_dec_col: Column name for detected Dec
    catalog_ra_col: Column name for catalog RA
    catalog_dec_col: Column name for catalog Dec
    detected_flux_col: Column name for detected flux (optional)
    catalog_flux_col: Column name for catalog flux (optional)
    detected_id_col: Column name for detected ID (optional)
    catalog_id_col: Column name for catalog ID (optional)

Returns:
    DataFrame with cross-matched sources

#### `cross_match_sources(detected_ra: numpy.ndarray, detected_dec: numpy.ndarray, catalog_ra: numpy.ndarray, catalog_dec: numpy.ndarray, radius_arcsec: float = 10.0, detected_flux: Optional[numpy.ndarray] = None, catalog_flux: Optional[numpy.ndarray] = None, detected_flux_err: Optional[numpy.ndarray] = None, catalog_flux_err: Optional[numpy.ndarray] = None, detected_ids: Optional[numpy.ndarray] = None, catalog_ids: Optional[numpy.ndarray] = None) -> pandas.core.frame.DataFrame`

General-purpose cross-matching utility.

Matches detected sources with catalog sources using nearest-neighbor matching.

Args:
    detected_ra: RA of detected sources (degrees)
    detected_dec: Dec of detected sources (degrees)
    catalog_ra: RA of catalog sources (degrees)
    catalog_dec: Dec of catalog sources (degrees)
    radius_arcsec: Matching radius in arcseconds
    detected_flux: Flux of detected sources (optional)
    catalog_flux: Flux of catalog sources (optional)
    detected_flux_err: Flux error of detected sources (optional)
    catalog_flux_err: Flux error of catalog sources (optional)
    detected_ids: IDs of detected sources (optional)
    catalog_ids: IDs of catalog sources (optional)

Returns:
    DataFrame with cross-matched sources containing:
    - detected_idx: Index of detected source
    - catalog_idx: Index of catalog source
    - separation_arcsec: Separation distance (arcsec)
    - dra_arcsec: RA offset (arcsec)
    - ddec_arcsec: Dec offset (arcsec)
    - detected_flux, catalog_flux: Flux values (if provided)
    - detected_flux_err, catalog_flux_err: Flux errors (if provided)
    - detected_id, catalog_id: Source IDs (if provided)
    - flux_ratio: Flux ratio (if both fluxes provided)

#### `identify_duplicate_catalog_sources(catalog_matches: Dict[str, pandas.core.frame.DataFrame], deduplication_radius_arcsec: float = 2.0) -> Dict[str, str]`

Identify when multiple catalog entries refer to the same physical source.

This function analyzes matches from multiple catalogs and identifies when
different catalog entries (e.g., NVSS J123456+012345 and FIRST J123456+012345)
refer to the same physical source based on their positions.

Args:
    catalog_matches: Dictionary mapping catalog names to DataFrames with matches.
        Each DataFrame should contain columns: 'catalog_ra_deg', 'catalog_dec_deg', 'catalog_source_id'
    deduplication_radius_arcsec: Maximum separation to consider sources as duplicates

Returns:
    Dictionary mapping catalog entries to master catalog IDs.
    Format: {f"{catalog_type}:{catalog_source_id}": master_catalog_id}
    The master_catalog_id is typically the NVSS ID if available, otherwise
    the FIRST ID, otherwise the RACS ID, or a generated ID.

#### `join_match_coordinates_sky(coords1: astropy.coordinates.sky_coordinate.SkyCoord, coords2: astropy.coordinates.sky_coordinate.SkyCoord, seplimit: Unit("arcsec")) -> Tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray, numpy.ndarray]`

Helper function to perform cross-match using astropy.

Args:
    coords1: Input coordinates (detected sources)
    coords2: Reference coordinates (catalog sources)
    seplimit: Cross-match radius limit

Returns:
    Tuple of:
    - Indices of coords1 that have matches
    - Indices of coords2 that match coords1
    - Separation distances for matches
    - 3D distances for matches

#### `multi_catalog_match(detected_ra: numpy.ndarray, detected_dec: numpy.ndarray, catalogs: Dict[str, Dict[str, numpy.ndarray]], radius_arcsec: float = 10.0) -> pandas.core.frame.DataFrame`

Match sources against multiple catalogs simultaneously.

Args:
    detected_ra: RA of detected sources (degrees)
    detected_dec: Dec of detected sources (degrees)
    catalogs: Dictionary mapping catalog names to dictionaries containing:
        - 'ra': RA array (degrees)
        - 'dec': Dec array (degrees)
        - 'flux': Flux array (optional)
        - 'id': ID array (optional)
    radius_arcsec: Matching radius in arcseconds

Returns:
    DataFrame with best match for each detected source across all catalogs:
    - detected_idx: Index of detected source
    - best_catalog: Name of catalog with best match
    - best_catalog_idx: Index in best catalog
    - best_separation_arcsec: Best separation distance
    - Additional columns for each catalog with match info

#### `search_around_sky(coords1: astropy.coordinates.sky_coordinate.SkyCoord, coords2: astropy.coordinates.sky_coordinate.SkyCoord, radius: astropy.coordinates.angles.core.Angle) -> Tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray]`

Find all matches within radius (not just nearest neighbor).

Useful for advanced association methods that need to consider
multiple potential matches.

Args:
    coords1: Input coordinates
    coords2: Reference coordinates
    radius: Search radius

Returns:
    Tuple of:
    - Indices of coords1 with matches
    - Indices of coords2 that match
    - Separation distances

---
