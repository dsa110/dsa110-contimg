# Real-World Pipeline Examples

This document provides real-world examples of using the DSA-110 Continuum
Imaging Pipeline.

## Example 1: Basic Observation Processing

Process a single observation from UVH5 to final image.

```python
from pathlib import Path
from dsa110_contimg.pipeline import PipelineOrchestrator, StageDefinition
from dsa110_contimg.pipeline.config import PipelineConfig, PathsConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages_impl import (
    CatalogSetupStage,
    ConversionStage,
    CalibrationSolveStage,
    CalibrationStage,
    ImagingStage,
    ValidationStage
)

# Configuration
config = PipelineConfig(
    paths=PathsConfig(
        input_dir=Path("/data/incoming"),
        output_dir=Path("/data/products"),
        scratch_dir=Path("/dev/shm")  # Use tmpfs for fast I/O
    ),
    conversion=ConversionConfig(
        max_workers=8,
        stage_to_tmpfs=True
    ),
    imaging=ImagingConfig(
        niter=1000,
        threshold="0.001Jy"
    )
)

# Define pipeline stages
stages = [
    StageDefinition("catalog_setup", CatalogSetupStage(config), []),
    StageDefinition("conversion", ConversionStage(config), ["catalog_setup"]),
    StageDefinition("calibration_solve", CalibrationSolveStage(config), ["conversion"]),
    StageDefinition("calibration", CalibrationStage(config), ["calibration_solve"]),
    StageDefinition("imaging", ImagingStage(config), ["calibration"]),
    StageDefinition("validation", ValidationStage(config), ["imaging"]),
]

# Create orchestrator
orchestrator = PipelineOrchestrator(stages)

# Process observation
observation_path = "/data/incoming/2025-01-15T12:00:00.uvh5"

context = PipelineContext(
    config=config,
    inputs={
        "input_path": observation_path,
        "start_time": "2025-01-15T12:00:00",
        "end_time": "2025-01-15T13:00:00"
    }
)

result = orchestrator.execute(context)

# Check results
if result.status == PipelineStatus.COMPLETED:
    image_path = result.context.outputs["image_path"]
    validation_results = result.context.outputs["validation_results"]

    print(f"Image created: {image_path}")
    print(f"Validation status: {validation_results['status']}")
else:
    print(f"Pipeline failed: {result.status}")
    for stage_name, stage_result in result.stage_results.items():
        if stage_result.status == StageStatus.FAILED:
            print(f"  {stage_name}: {stage_result.error}")
```

## Example 2: Batch Processing Multiple Observations

Process multiple observations in parallel.

```python
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def process_observation(observation_path: str, config: PipelineConfig):
    """Process a single observation."""
    stages = [
        StageDefinition("catalog_setup", CatalogSetupStage(config), []),
        StageDefinition("conversion", ConversionStage(config), ["catalog_setup"]),
        StageDefinition("calibration_solve", CalibrationSolveStage(config), ["conversion"]),
        StageDefinition("calibration", CalibrationStage(config), ["calibration_solve"]),
        StageDefinition("imaging", ImagingStage(config), ["calibration"]),
    ]

    orchestrator = PipelineOrchestrator(stages)

    context = PipelineContext(
        config=config,
        inputs={"input_path": observation_path}
    )

    result = orchestrator.execute(context)
    return result

# Configuration
config = PipelineConfig(
    paths=PathsConfig(
        input_dir=Path("/data/incoming"),
        output_dir=Path("/data/products")
    )
)

# Find all observations
observation_dir = Path("/data/incoming")
observations = list(observation_dir.glob("*.uvh5"))

# Process in parallel
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(process_observation, str(obs), config)
        for obs in observations
    ]

    results = [f.result() for f in futures]

# Check results
successful = [r for r in results if r.status == PipelineStatus.COMPLETED]
failed = [r for r in results if r.status == PipelineStatus.FAILED]

print(f"Processed {len(successful)}/{len(results)} observations successfully")
```

## Example 3: Custom Stage for Source Detection

Add a custom stage for source detection.

```python
from dsa110_contimg.pipeline.stages import PipelineStage
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.config import PipelineConfig
from typing import Tuple, Optional
import pandas as pd
from astropy.io import fits

class SourceDetectionStage(PipelineStage):
    """Detect sources in FITS images."""

    def __init__(self, config: PipelineConfig):
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        if "image_path" not in context.outputs:
            return False, "image_path required in context.outputs"

        image_path = context.outputs["image_path"]
        if not Path(image_path).exists():
            return False, f"Image file not found: {image_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        image_path = context.outputs["image_path"]

        # Load image
        with fits.open(image_path) as hdul:
            data = hdul[0].data
            header = hdul[0].header

        # Detect sources (simplified example)
        # In practice, use proper source detection algorithm
        sources = detect_sources(data, header, threshold=5.0)  # 5σ threshold

        # Convert to DataFrame
        sources_df = pd.DataFrame({
            "ra_deg": sources["ra"],
            "dec_deg": sources["dec"],
            "flux_jy": sources["flux"],
            "snr": sources["snr"]
        })

        return context.with_output("detected_sources", sources_df)

    def get_name(self) -> str:
        return "source_detection"

# Use in pipeline
stages = [
    StageDefinition("imaging", ImagingStage(config), ["calibration"]),
    StageDefinition("source_detection", SourceDetectionStage(config), ["imaging"]),
    StageDefinition("cross_match", CrossMatchStage(config), ["source_detection"]),
]
```

## Example 4: Error Handling and Retry

Handle errors and retry failed stages.

```python
from dsa110_contimg.pipeline import PipelineOrchestrator, StageDefinition
from dsa110_contimg.pipeline.resilience import RetryPolicy

# Configure retry policy
retry_policy = RetryPolicy(
    max_retries=3,
    backoff_factor=2.0,
    retryable_exceptions=(IOError, TimeoutError)
)

# Create orchestrator with retry policy
orchestrator = PipelineOrchestrator(
    stages,
    retry_policy=retry_policy
)

# Execute with error handling
try:
    result = orchestrator.execute(context)

    if result.status == PipelineStatus.FAILED:
        # Check which stages failed
        for stage_name, stage_result in result.stage_results.items():
            if stage_result.status == StageStatus.FAILED:
                print(f"Stage {stage_name} failed after {stage_result.retry_count} retries")
                print(f"Error: {stage_result.error}")

                # Handle specific stage failures
                if stage_name == "conversion":
                    # Try alternative conversion method
                    pass
                elif stage_name == "calibration":
                    # Use fallback calibration
                    pass

except Exception as e:
    print(f"Pipeline execution failed: {e}")
    # Cleanup, notify, etc.
```

## Example 5: Conditional Stage Execution

Skip stages based on configuration or context.

```python
class ConditionalValidationStage(PipelineStage):
    """Validation stage that can be skipped."""

    def __init__(self, config: PipelineConfig):
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        # Skip if validation disabled
        if not self.config.validation.enabled:
            return False, "Validation disabled in configuration"

        if "image_path" not in context.outputs:
            return False, "image_path required"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        # Check if already validated
        if "validation_results" in context.outputs:
            return context  # Skip if already done

        # Perform validation
        image_path = context.outputs["image_path"]
        results = run_validation(image_path)

        return context.with_output("validation_results", results)

    def get_name(self) -> str:
        return "validation"

# Use conditional execution
config.validation.enabled = False  # Disable validation
# Validation stage will be skipped
```

## Example 6: Monitoring and Observability

Add monitoring and observability to pipeline execution.

```python
from dsa110_contimg.pipeline.observability import PipelineObserver

class CustomObserver(PipelineObserver):
    """Custom observer for monitoring."""

    def on_pipeline_start(self, context: PipelineContext):
        print(f"Pipeline started: {context.job_id}")

    def on_stage_start(self, stage_name: str, context: PipelineContext):
        print(f"Stage started: {stage_name}")

    def on_stage_end(self, stage_name: str, context: PipelineContext, duration: float):
        print(f"Stage completed: {stage_name} in {duration:.2f}s")

    def on_pipeline_end(self, result):
        print(f"Pipeline completed: {result.status}")

# Create observer
observer = CustomObserver()

# Use in orchestrator
orchestrator = PipelineOrchestrator(stages, observer=observer)

# Execute
result = orchestrator.execute(context)
```

## Example 7: Pipeline with Database Integration

Store pipeline results in database.

```python
from dsa110_contimg.database.products import ensure_products_db
import sqlite3

class DatabaseStorageStage(PipelineStage):
    """Store pipeline results in database."""

    def __init__(self, config: PipelineConfig):
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        if "image_path" not in context.outputs:
            return False, "image_path required"
        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        image_path = context.outputs["image_path"]

        # Ensure database exists
        db_path = ensure_products_db(context.config.paths.output_dir)

        # Store image metadata
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                INSERT INTO images (path, created_at, job_id)
                VALUES (?, datetime('now'), ?)
            """, (image_path, context.job_id))
            conn.commit()

        return context.with_output("db_path", db_path)

    def get_name(self) -> str:
        return "database_storage"

# Add to pipeline
stages = [
    # ... other stages ...
    StageDefinition("database_storage", DatabaseStorageStage(config), ["imaging"]),
]
```

## Example 8: Parallel Stage Execution

Execute independent stages in parallel.

```python
# Stages that can run in parallel
stages = [
    StageDefinition("conversion", ConversionStage(config), []),
    StageDefinition("calibration_solve", CalibrationSolveStage(config), ["conversion"]),
    # These can run in parallel after calibration_solve
    StageDefinition("calibration", CalibrationStage(config), ["calibration_solve"]),
    StageDefinition("organization", OrganizationStage(config), ["conversion"]),  # Independent
    # Imaging depends on calibration, not organization
    StageDefinition("imaging", ImagingStage(config), ["calibration"]),
]

# Orchestrator automatically handles parallel execution
orchestrator = PipelineOrchestrator(stages)
result = orchestrator.execute(context)

# Organization and Calibration can run in parallel
# Imaging waits for Calibration only
```

## Example 9: Pipeline with Checkpointing

Save pipeline state for recovery.

```python
import pickle
from pathlib import Path

class CheckpointStage(PipelineStage):
    """Save pipeline state for recovery."""

    def __init__(self, config: PipelineConfig):
        self.config = config

    def execute(self, context: PipelineContext) -> PipelineContext:
        checkpoint_dir = Path(context.config.paths.output_dir) / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_path = checkpoint_dir / f"checkpoint_{context.job_id}.pkl"

        # Save context state
        checkpoint_data = {
            "context": context,
            "timestamp": datetime.now().isoformat()
        }

        with open(checkpoint_path, "wb") as f:
            pickle.dump(checkpoint_data, f)

        return context.with_output("checkpoint_path", str(checkpoint_path))

    def get_name(self) -> str:
        return "checkpoint"

# Load checkpoint
def load_checkpoint(checkpoint_path: str) -> PipelineContext:
    with open(checkpoint_path, "rb") as f:
        checkpoint_data = pickle.load(f)
    return checkpoint_data["context"]

# Use checkpoint to resume
checkpoint_path = "/data/products/checkpoints/checkpoint_123.pkl"
context = load_checkpoint(checkpoint_path)
result = orchestrator.execute(context)
```

## Example 10: Pipeline with Custom Error Recovery

Implement custom error recovery logic.

```python
class ResilientImagingStage(ImagingStage):
    """Imaging stage with custom error recovery."""

    def execute(self, context: PipelineContext) -> PipelineContext:
        try:
            return super().execute(context)
        except Exception as e:
            # Try fallback imaging parameters
            logger.warning(f"Imaging failed with standard parameters: {e}")
            logger.info("Trying fallback imaging parameters")

            # Use more conservative parameters
            fallback_config = self.config.copy()
            fallback_config.imaging.niter = 500  # Fewer iterations
            fallback_config.imaging.threshold = "0.01Jy"  # Higher threshold

            # Retry with fallback
            fallback_stage = ImagingStage(fallback_config)
            return fallback_stage.execute(context)

# Use resilient stage
stages = [
    # ... other stages ...
    StageDefinition("imaging", ResilientImagingStage(config), ["calibration"]),
]
```

## Related Documentation

- [Architecture](../ARCHITECTURE.md) - System design and pipeline architecture
- [Developer Guide](../DEVELOPER_GUIDE.md) - Development patterns
- [Troubleshooting](../TROUBLESHOOTING.md) - Common issues and solutions
