# How to Create a New Pipeline Stage

This guide walks you through creating a new pipeline stage for the DSA-110
Continuum Imaging Pipeline.

## Overview

A pipeline stage is a modular unit of work that transforms a `PipelineContext`
into a new `PipelineContext` with additional outputs. Stages are executed
sequentially by the `PipelineOrchestrator`, which manages dependencies, retries,
and error handling.

## Step-by-Step Guide

### 1. Create Your Stage Class

Create a new class that inherits from `PipelineStage`:

```python
from dsa110_contimg.pipeline.stages import PipelineStage
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.config import PipelineConfig
from typing import Tuple, Optional

class MyNewStage(PipelineStage):
    """My new stage: Brief description of what this stage does.

    Detailed explanation of the stage's purpose, inputs, outputs, and
    any scientific or technical rationale.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize the stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for stage execution.

        Check that all required inputs are present and valid before
        attempting execution.

        Args:
            context: Pipeline context to validate

        Returns:
            Tuple of (is_valid, error_message). If is_valid is False,
            error_message should explain why validation failed.
        """
        # Check for required inputs
        if "required_input" not in context.inputs:
            return False, "required_input missing from context.inputs"

        # Validate input exists
        input_path = context.inputs["required_input"]
        if not Path(input_path).exists():
            return False, f"Input file not found: {input_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute the stage and return updated context.

        This is where your stage's core logic goes. Read inputs from
        context.inputs, perform work, and return a new context with
        outputs added via context.with_output() or context.with_outputs().

        Args:
            context: Input context with configuration and inputs

        Returns:
            Updated context with new outputs

        Raises:
            Exception: If stage execution fails
        """
        # Get inputs
        input_path = context.inputs["required_input"]

        # Perform work
        result = do_something(input_path)

        # Return updated context with outputs
        return context.with_output("my_output", result)

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup resources after execution (optional).

        Called after execution (success or failure) to clean up temporary
        resources. On failure, this should clean up any partial outputs
        to prevent accumulation of corrupted files.

        Args:
            context: Context used during execution
        """
        # Clean up temporary files, close connections, etc.
        pass

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate stage outputs after execution (optional).

        Called after successful execution to verify that outputs are correct
        and complete before proceeding to next stage.

        Args:
            context: Context with outputs to validate

        Returns:
            Tuple of (is_valid, error_message). If is_valid is False,
            error_message should explain what validation failed.
        """
        if "my_output" not in context.outputs:
            return False, "my_output missing from context.outputs"

        output_path = context.outputs["my_output"]
        if not Path(output_path).exists():
            return False, f"Output file not found: {output_path}"

        return True, None

    def get_name(self) -> str:
        """Get stage name for logging and tracking.

        Returns:
            Stage name (use snake_case, e.g., "my_new_stage")
        """
        return "my_new_stage"
```

### 2. Add Your Stage to the Pipeline

Register your stage in the pipeline orchestrator. Find where stages are
registered (typically in `src/dsa110_contimg/pipeline/orchestrator.py` or a
configuration file) and add:

```python
from dsa110_contimg.pipeline.stages_impl import MyNewStage

# In the stage definitions list
stages = [
    # ... existing stages ...
    StageDefinition(
        name="my_new_stage",
        stage=MyNewStage(config),
        dependencies=["previous_stage"]  # List of stage names this depends on
    ),
]
```

### 3. Write Tests

Create comprehensive tests for your stage:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from dsa110_contimg.pipeline.config import PipelineConfig, PathsConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages_impl import MyNewStage

class TestMyNewStage:
    """Test MyNewStage."""

    def test_validate_missing_input(self):
        """Test validation fails when required input is missing."""
        config = PipelineConfig(paths=PathsConfig(...))
        context = PipelineContext(config=config)
        stage = MyNewStage(config)

        is_valid, error_msg = stage.validate(context)
        assert not is_valid
        assert "required_input" in error_msg.lower()

    def test_validate_valid_input(self):
        """Test validation succeeds with valid input."""
        config = PipelineConfig(paths=PathsConfig(...))
        context = PipelineContext(
            config=config,
            inputs={"required_input": "/valid/path"}
        )
        stage = MyNewStage(config)

        is_valid, error_msg = stage.validate(context)
        assert is_valid
        assert error_msg is None

    def test_execute(self):
        """Test stage execution."""
        config = PipelineConfig(paths=PathsConfig(...))
        context = PipelineContext(
            config=config,
            inputs={"required_input": "/input/path"}
        )
        stage = MyNewStage(config)

        # Mock external dependencies
        with patch("dsa110_contimg.module.function") as mock_func:
            mock_func.return_value = "result"

            result_context = stage.execute(context)

            assert "my_output" in result_context.outputs
            assert result_context.outputs["my_output"] == "result"

    def test_get_name(self):
        """Test stage name."""
        config = PipelineConfig(paths=PathsConfig(...))
        stage = MyNewStage(config)
        assert stage.get_name() == "my_new_stage"
```

### 4. Document Your Stage

Add your stage to the pipeline architecture documentation
(`docs/concepts/pipeline_stage_architecture.md`):

```markdown
### MyNewStage

- **Purpose:** Brief description
- **Inputs:** `required_input` (description)
- **Outputs:** `my_output` (description)
- **Dependencies:** `previous_stage`
- **Scientific Rationale:** Why this stage exists
```

## Best Practices

### 1. Immutability

Always return a new context using `context.with_output()` or
`context.with_outputs()`. Never modify the input context directly.

```python
# Good
return context.with_output("key", value)

# Bad
context.outputs["key"] = value
return context
```

### 2. Validation

Validate inputs thoroughly in `validate()`. Check for:

- Missing required inputs
- Invalid file paths
- Configuration settings
- Prerequisites from previous stages

### 3. Error Handling

Raise exceptions with clear error messages. The orchestrator will handle retries
and logging.

```python
if not Path(input_path).exists():
    raise FileNotFoundError(f"Input file not found: {input_path}")
```

### 4. Cleanup

Always clean up temporary resources in `cleanup()`, especially on failure:

```python
def cleanup(self, context: PipelineContext) -> None:
    """Clean up temporary files."""
    if "temp_file" in context.metadata:
        temp_path = Path(context.metadata["temp_file"])
        if temp_path.exists():
            temp_path.unlink()
```

### 5. Logging

Use the logger for important events:

```python
from dsa110_contimg.utils.logging import get_logger

logger = get_logger(__name__)

def execute(self, context: PipelineContext) -> PipelineContext:
    logger.info(f"Starting {self.get_name()} stage")
    # ... work ...
    logger.info(f"Completed {self.get_name()} stage")
    return context
```

### 6. Naming

- Use snake_case for stage names (e.g., `my_new_stage`)
- Be descriptive but concise
- Match the class name pattern: `MyNewStage` → `"my_new_stage"`

## Common Patterns

### Pattern 1: File Processing Stage

```python
def execute(self, context: PipelineContext) -> PipelineContext:
    input_path = context.inputs["input_file"]
    output_path = process_file(input_path, self.config)
    return context.with_output("output_file", output_path)
```

### Pattern 2: Database Query Stage

```python
def execute(self, context: PipelineContext) -> PipelineContext:
    query_params = context.inputs["query_params"]
    results = query_database(query_params, self.config)
    return context.with_outputs({
        "query_results": results,
        "query_count": len(results)
    })
```

### Pattern 3: Conditional Execution

```python
def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
    if not self.config.my_stage.enabled:
        return False, "My stage is disabled in configuration"
    return True, None
```

## Testing Checklist

- [ ] Test `validate()` with missing inputs
- [ ] Test `validate()` with invalid inputs
- [ ] Test `validate()` with valid inputs
- [ ] Test `execute()` with mocked dependencies
- [ ] Test `execute()` returns updated context
- [ ] Test `cleanup()` is called
- [ ] Test `validate_outputs()` checks outputs
- [ ] Test `get_name()` returns correct name
- [ ] Test error handling and exceptions
- [ ] Test edge cases (empty inputs, large files, etc.)

## Integration

After creating your stage:

1. Add it to the pipeline orchestrator configuration
2. Update dependency graph if needed
3. Add integration tests
4. Update documentation
5. Add to mind palace (Graphiti) if it's a significant addition

## Examples

See existing stages in `src/dsa110_contimg/pipeline/stages_impl.py`:

- `CatalogSetupStage` - Database setup
- `ConversionStage` - File format conversion
- `CalibrationSolveStage` - Calibration solving
- `ImagingStage` - Image generation
- `ValidationStage` - Quality assurance

## Troubleshooting

**Problem:** Stage not executing

- Check that stage is registered in orchestrator
- Verify dependencies are satisfied
- Check validation is passing

**Problem:** Outputs not available to next stage

- Ensure you're using `context.with_output()` or `context.with_outputs()`
- Verify output keys match what next stage expects

**Problem:** Tests failing

- Check that mocks are patching the correct import path
- Verify test data matches expected format
- Ensure cleanup is not interfering with tests

## Related Documentation

- [Pipeline Stage Architecture](../../architecture/pipeline/pipeline_stage_architecture.md)
- [Pipeline Overview](../../architecture/pipeline/pipeline_overview.md) - Configuration details
- [Testing Guide](../how-to/testing.md)
