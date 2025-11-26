# Pipeline Migration Guide

This guide helps migrate between different versions of the DSA-110 Continuum
Imaging Pipeline.

## Version History

### Current Version: 2.0

**Key Changes:**

- Stage-based architecture introduced
- Immutable PipelineContext
- PipelineOrchestrator for dependency management
- Comprehensive error handling and retry logic

### Previous Version: 1.0

**Key Features:**

- Monolithic pipeline execution
- Mutable state
- Sequential processing
- Basic error handling

## Migration from 1.0 to 2.0

### Overview

Version 2.0 introduces a stage-based architecture with immutable contexts. This
requires changes to how pipelines are configured and executed.

### Breaking Changes

#### 1. Pipeline Execution

**Before (1.0):**

```python
from dsa110_contimg.pipeline import run_pipeline

result = run_pipeline(
    input_path="/data/observation.hdf5",
    output_dir="/data/output"
)
```

**After (2.0):**

```python
from dsa110_contimg.pipeline import PipelineOrchestrator, StageDefinition
from dsa110_contimg.pipeline.stages_impl import (
    ConversionStage,
    CalibrationStage,
    ImagingStage
)
from dsa110_contimg.pipeline.config import PipelineConfig, PathsConfig
from dsa110_contimg.pipeline.context import PipelineContext

# Create configuration
config = PipelineConfig(
    paths=PathsConfig(
        input_dir=Path("/data/input"),
        output_dir=Path("/data/output")
    )
)

# Define stages
stages = [
    StageDefinition("conversion", ConversionStage(config), []),
    StageDefinition("calibration", CalibrationStage(config), ["conversion"]),
    StageDefinition("imaging", ImagingStage(config), ["calibration"]),
]

# Create orchestrator
orchestrator = PipelineOrchestrator(stages)

# Create initial context
context = PipelineContext(
    config=config,
    inputs={"input_path": "/data/observation.hdf5"}
)

# Execute pipeline
result = orchestrator.execute(context)
```

#### 2. State Management

**Before (1.0):**

```python
# Mutable state
pipeline_state = {
    "ms_path": "/data/converted.ms",
    "calibration_tables": {...}
}
pipeline_state["image_path"] = "/data/image.fits"  # Direct mutation
```

**After (2.0):**

```python
# Immutable context
context = PipelineContext(
    config=config,
    outputs={"ms_path": "/data/converted.ms"}
)

# Create new context with additional output
new_context = context.with_output("image_path", "/data/image.fits")
# Original context unchanged
```

#### 3. Stage Dependencies

**Before (1.0):**

```python
# Implicit dependencies (execution order)
run_conversion()
run_calibration()  # Assumes conversion completed
run_imaging()  # Assumes calibration completed
```

**After (2.0):**

```python
# Explicit dependencies
stages = [
    StageDefinition("conversion", ConversionStage(config), []),
    StageDefinition("calibration", CalibrationStage(config), ["conversion"]),
    StageDefinition("imaging", ImagingStage(config), ["calibration"]),
]
# Orchestrator resolves dependencies automatically
```

#### 4. Error Handling

**Before (1.0):**

```python
try:
    result = run_pipeline(...)
except Exception as e:
    # Basic error handling
    logger.error(f"Pipeline failed: {e}")
```

**After (2.0):**

```python
result = orchestrator.execute(context)

if result.status == PipelineStatus.FAILED:
    # Detailed error information
    for stage_name, stage_result in result.stage_results.items():
        if stage_result.status == StageStatus.FAILED:
            logger.error(f"Stage {stage_name} failed: {stage_result.error}")
            # Access to retry attempts, error messages, etc.
```

### Migration Steps

#### Step 1: Update Imports

```python
# Old imports
from dsa110_contimg.pipeline import run_pipeline

# New imports
from dsa110_contimg.pipeline import PipelineOrchestrator, StageDefinition
from dsa110_contimg.pipeline.config import PipelineConfig, PathsConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages_impl import (
    ConversionStage,
    CalibrationStage,
    ImagingStage
)
```

#### Step 2: Create Configuration

```python
# Old: No explicit configuration
result = run_pipeline(input_path="...", output_dir="...")

# New: Explicit configuration
config = PipelineConfig(
    paths=PathsConfig(
        input_dir=Path("/data/input"),
        output_dir=Path("/data/output")
    ),
    conversion=ConversionConfig(...),
    calibration=CalibrationConfig(...),
    imaging=ImagingConfig(...)
)
```

#### Step 3: Define Stages

```python
# Old: Implicit stages
# Stages were defined internally

# New: Explicit stage definitions
stages = [
    StageDefinition("conversion", ConversionStage(config), []),
    StageDefinition("calibration", CalibrationStage(config), ["conversion"]),
    StageDefinition("imaging", ImagingStage(config), ["calibration"]),
]
```

#### Step 4: Create Context

```python
# Old: Parameters passed directly
result = run_pipeline(input_path="...", ...)

# New: Context with inputs
context = PipelineContext(
    config=config,
    inputs={"input_path": "/data/observation.hdf5"}
)
```

#### Step 5: Execute Pipeline

```python
# Old: Direct execution
result = run_pipeline(...)

# New: Orchestrator execution
orchestrator = PipelineOrchestrator(stages)
result = orchestrator.execute(context)
```

#### Step 6: Access Results

```python
# Old: Direct result access
ms_path = result["ms_path"]
image_path = result["image_path"]

# New: Context outputs
ms_path = result.context.outputs["ms_path"]
image_path = result.context.outputs["image_path"]

# Also check status
if result.status == PipelineStatus.COMPLETED:
    # Process results
    pass
```

### Configuration Migration

#### Old Configuration Format

```python
# Old: Dictionary-based
config = {
    "input_dir": "/data/input",
    "output_dir": "/data/output",
    "calibration": {
        "enabled": True,
        "method": "standard"
    }
}
```

#### New Configuration Format

```python
# New: Pydantic-based
from dsa110_contimg.pipeline.config import (
    PipelineConfig,
    PathsConfig,
    CalibrationConfig
)

config = PipelineConfig(
    paths=PathsConfig(
        input_dir=Path("/data/input"),
        output_dir=Path("/data/output")
    ),
    calibration=CalibrationConfig(
        enabled=True,
        method="standard"
    )
)
```

### Code Migration Examples

#### Example 1: Simple Pipeline

**Before:**

```python
from dsa110_contimg.pipeline import run_pipeline

result = run_pipeline(
    input_path="/data/observation.hdf5",
    output_dir="/data/output"
)
print(f"Image: {result['image_path']}")
```

**After:**

```python
from dsa110_contimg.pipeline import PipelineOrchestrator, StageDefinition
from dsa110_contimg.pipeline.config import PipelineConfig, PathsConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages_impl import (
    ConversionStage,
    CalibrationStage,
    ImagingStage
)

config = PipelineConfig(
    paths=PathsConfig(
        input_dir=Path("/data/input"),
        output_dir=Path("/data/output")
    )
)

stages = [
    StageDefinition("conversion", ConversionStage(config), []),
    StageDefinition("calibration", CalibrationStage(config), ["conversion"]),
    StageDefinition("imaging", ImagingStage(config), ["calibration"]),
]

orchestrator = PipelineOrchestrator(stages)
context = PipelineContext(
    config=config,
    inputs={"input_path": "/data/observation.hdf5"}
)

result = orchestrator.execute(context)
if result.status == PipelineStatus.COMPLETED:
    print(f"Image: {result.context.outputs['image_path']}")
```

#### Example 2: Custom Stage

**Before:**

```python
# Custom processing in pipeline
def custom_process(data):
    # Process data
    return processed_data

result = run_pipeline(
    input_path="...",
    custom_processor=custom_process
)
```

**After:**

```python
# Create custom stage
from dsa110_contimg.pipeline.stages import PipelineStage

class CustomStage(PipelineStage):
    def __init__(self, config: PipelineConfig):
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        if "input_data" not in context.outputs:
            return False, "input_data required"
        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        data = context.outputs["input_data"]
        processed = custom_process(data)
        return context.with_output("processed_data", processed)

    def get_name(self) -> str:
        return "custom"

# Use in pipeline
stages = [
    StageDefinition("previous", PreviousStage(config), []),
    StageDefinition("custom", CustomStage(config), ["previous"]),
]
```

### Testing Migration

#### Old Tests

```python
def test_pipeline():
    result = run_pipeline(input_path="...")
    assert "image_path" in result
```

#### New Tests

```python
def test_pipeline():
    config = PipelineConfig(...)
    stages = [...]
    orchestrator = PipelineOrchestrator(stages)
    context = PipelineContext(config=config, inputs={...})

    result = orchestrator.execute(context)
    assert result.status == PipelineStatus.COMPLETED
    assert "image_path" in result.context.outputs
```

### Common Migration Issues

#### Issue 1: Mutable State

**Problem:** Code modifies state directly

**Solution:** Use `with_output()` or `with_outputs()`

```python
# Wrong
context.outputs["key"] = value

# Correct
context = context.with_output("key", value)
```

#### Issue 2: Missing Dependencies

**Problem:** Stages execute in wrong order

**Solution:** Declare dependencies explicitly

```python
# Wrong: No dependencies
StageDefinition("stage2", Stage2(), [])

# Correct: Declare dependencies
StageDefinition("stage2", Stage2(), ["stage1"])
```

#### Issue 3: Configuration Access

**Problem:** Accessing config as dictionary

**Solution:** Use Pydantic config objects

```python
# Wrong
config["calibration"]["enabled"]

# Correct
config.calibration.enabled
```

### Rollback Strategy

If migration issues occur:

1. **Keep old code**: Don't delete v1.0 code immediately
2. **Gradual migration**: Migrate stages one at a time
3. **Test thoroughly**: Test each migrated stage
4. **Monitor**: Watch for errors in production
5. **Rollback plan**: Keep ability to revert if needed

### Migration Checklist

- [ ] Update imports
- [ ] Create PipelineConfig
- [ ] Define stages with dependencies
- [ ] Create PipelineContext
- [ ] Update pipeline execution
- [ ] Update result access
- [ ] Migrate configuration
- [ ] Update tests
- [ ] Test migration
- [ ] Update documentation
- [ ] Deploy gradually

### Getting Help

If you encounter issues during migration:

1. **Check Documentation**: Review stage architecture docs
2. **Review Examples**: Check migration examples
3. **Test Incrementally**: Migrate one stage at a time
4. **Ask for Help**: Contact pipeline maintainers

## Related Documentation

- [Pipeline Stage Architecture](../../architecture/pipeline/pipeline_stage_architecture.md)
- [Creating Pipeline Stages](../development/create_pipeline_stage.md)
- [Troubleshooting Guide](troubleshooting.md)
