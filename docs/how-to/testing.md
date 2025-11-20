# Testing Guide for Pipeline Stages

This guide provides comprehensive instructions for testing pipeline stages in
the DSA-110 Continuum Imaging Pipeline.

## Overview

Testing pipeline stages involves multiple levels:

1. **Unit Tests**: Test individual stages in isolation
2. **Integration Tests**: Test stage interactions and orchestrator behavior
3. **End-to-End Tests**: Test complete pipeline workflows

## Unit Testing

### Test Structure

Unit tests for stages should follow this structure:

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from dsa110_contimg.pipeline.config import PipelineConfig, PathsConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages_impl import MyStage

class TestMyStage:
    """Test MyStage."""

    def test_validate_missing_input(self):
        """Test validation fails when required input is missing."""
        # Setup
        config = PipelineConfig(paths=PathsConfig(...))
        context = PipelineContext(config=config)
        stage = MyStage(config)

        # Execute
        is_valid, error_msg = stage.validate(context)

        # Assert
        assert not is_valid
        assert "required_input" in error_msg.lower()

    def test_validate_valid_input(self):
        """Test validation succeeds with valid input."""
        # Setup
        config = PipelineConfig(paths=PathsConfig(...))
        context = PipelineContext(
            config=config,
            inputs={"required_input": "/valid/path"}
        )
        stage = MyStage(config)

        # Execute
        is_valid, error_msg = stage.validate(context)

        # Assert
        assert is_valid
        assert error_msg is None

    def test_execute(self):
        """Test stage execution."""
        # Setup
        config = PipelineConfig(paths=PathsConfig(...))
        context = PipelineContext(
            config=config,
            inputs={"required_input": "/input/path"}
        )
        stage = MyStage(config)

        # Mock external dependencies
        with patch("dsa110_contimg.module.function") as mock_func:
            mock_func.return_value = "result"

            # Execute
            result_context = stage.execute(context)

            # Assert
            assert "output" in result_context.outputs
            assert result_context.outputs["output"] == "result"
            mock_func.assert_called_once()

    def test_get_name(self):
        """Test stage name."""
        config = PipelineConfig(paths=PathsConfig(...))
        stage = MyStage(config)
        assert stage.get_name() == "my_stage"
```

### Testing Checklist

For each stage, test:

- [ ] **`validate()` with missing inputs**: Should return
      `(False, error_message)`
- [ ] **`validate()` with invalid inputs**: Should return
      `(False, error_message)`
- [ ] **`validate()` with valid inputs**: Should return `(True, None)`
- [ ] **`execute()` with mocked dependencies**: Should return updated context
- [ ] **`execute()` output verification**: Outputs should be correct
- [ ] **`cleanup()` is called**: Should clean up resources
- [ ] **`validate_outputs()` checks outputs**: Should validate outputs exist and
      are correct
- [ ] **`get_name()` returns correct name**: Should return snake_case name
- [ ] **Error handling**: Should raise appropriate exceptions
- [ ] **Edge cases**: Empty inputs, large files, etc.

### Mocking External Dependencies

Always mock external dependencies (CASA, file I/O, databases):

```python
# Mock CASA functions
with patch("dsa110_contimg.calibration.calibration.solve_calibration_tables") as mock_solve:
    mock_solve.return_value = {"K": "/mock/K.cal"}
    result = stage.execute(context)

# Mock file operations
with patch("pathlib.Path.exists", return_value=True):
    is_valid, _ = stage.validate(context)

# Mock database operations
with patch("dsa110_contimg.database.get_connection") as mock_db:
    mock_db.return_value = MagicMock()
    result = stage.execute(context)
```

### Testing Validation

Test validation thoroughly:

```python
def test_validate_missing_input(self):
    """Test validation fails when input is missing."""
    context = PipelineContext(config=config)
    stage = MyStage(config)

    is_valid, error_msg = stage.validate(context)
    assert not is_valid
    assert "input" in error_msg.lower()

def test_validate_nonexistent_file(self):
    """Test validation fails when file doesn't exist."""
    context = PipelineContext(
        config=config,
        inputs={"input_path": "/nonexistent/file"}
    )
    stage = MyStage(config)

    is_valid, error_msg = stage.validate(context)
    assert not is_valid
    assert "not found" in error_msg.lower()

def test_validate_valid_input(self):
    """Test validation succeeds with valid input."""
    with tempfile.NamedTemporaryFile() as tmp:
        context = PipelineContext(
            config=config,
            inputs={"input_path": tmp.name}
        )
        stage = MyStage(config)

        is_valid, error_msg = stage.validate(context)
        assert is_valid
        assert error_msg is None
```

### Testing Execution

Test execution with mocked dependencies:

```python
def test_execute_success(self):
    """Test successful execution."""
    context = PipelineContext(
        config=config,
        inputs={"input_path": "/mock/input"}
    )
    stage = MyStage(config)

    # Mock external dependencies
    with patch("dsa110_contimg.module.process") as mock_process:
        mock_process.return_value = "/mock/output"

        result_context = stage.execute(context)

        # Verify outputs
        assert "output_path" in result_context.outputs
        assert result_context.outputs["output_path"] == "/mock/output"

        # Verify mock was called correctly
        mock_process.assert_called_once_with("/mock/input")

def test_execute_failure(self):
    """Test execution failure handling."""
    context = PipelineContext(
        config=config,
        inputs={"input_path": "/mock/input"}
    )
    stage = MyStage(config)

    # Mock external dependency to raise exception
    with patch("dsa110_contimg.module.process", side_effect=Exception("Processing failed")):
        with pytest.raises(Exception, match="Processing failed"):
            stage.execute(context)
```

### Testing Cleanup

Test that cleanup is called and works correctly:

```python
def test_cleanup_called(self):
    """Test cleanup is called."""
    context = PipelineContext(config=config)
    stage = MyStage(config)
    stage.cleanup = MagicMock()

    # Execute stage
    stage.execute(context)

    # Verify cleanup was called
    stage.cleanup.assert_called_once_with(context)

def test_cleanup_removes_temp_files(self):
    """Test cleanup removes temporary files."""
    temp_file = Path("/tmp/test_temp_file")
    temp_file.write_text("test")

    context = PipelineContext(
        config=config,
        metadata={"temp_file": str(temp_file)}
    )
    stage = MyStage(config)

    # Execute cleanup
    stage.cleanup(context)

    # Verify temp file was removed
    assert not temp_file.exists()
```

## Integration Testing

### Testing Stage Interactions

Test how stages interact with each other:

```python
def test_stage_chain_execution(self):
    """Test chain of stages executes correctly."""
    # Setup
    context = PipelineContext(config=config, inputs={"input_path": "/mock/input"})

    stage1 = Stage1(config)
    stage2 = Stage2(config)

    # Execute chain
    context1 = stage1.execute(context)
    context2 = stage2.execute(context1)

    # Verify outputs from both stages
    assert "stage1_output" in context2.outputs
    assert "stage2_output" in context2.outputs

def test_output_propagation(self):
    """Test outputs propagate correctly."""
    context = PipelineContext(config=config)

    # Stage 1 produces output
    context1 = stage1.execute(context)
    assert "output1" in context1.outputs

    # Stage 2 uses output1
    context2 = stage2.execute(context1)
    assert "output1" in context2.outputs  # Still present
    assert "output2" in context2.outputs  # New output
```

### Testing Orchestrator

Test orchestrator behavior with real stages:

```python
def test_orchestrator_executes_stages(self):
    """Test orchestrator executes stages in correct order."""
    stages = [
        StageDefinition("stage1", Stage1(config), []),
        StageDefinition("stage2", Stage2(config), ["stage1"]),
    ]

    orchestrator = PipelineOrchestrator(stages)
    result = orchestrator.execute(context)

    assert result.status == PipelineStatus.COMPLETED
    assert "stage1_output" in result.context.outputs
    assert "stage2_output" in result.context.outputs
```

## Running Tests

### Run All Tests

```bash
# Run all unit tests
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/ -v

# Run all integration tests
/opt/miniforge/envs/casa6/bin/python -m pytest tests/integration/ -v

# Run specific test file
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/test_pipeline_stages_comprehensive.py -v

# Run specific test
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/test_pipeline_stages_comprehensive.py::TestConversionStage::test_validate_missing_input -v
```

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_unit_test():
    """Unit test."""
    pass

@pytest.mark.integration
def test_integration_test():
    """Integration test."""
    pass

@pytest.mark.slow
def test_slow_test():
    """Slow test."""
    pass
```

Run tests by marker:

```bash
# Run only unit tests
/opt/miniforge/envs/casa6/bin/python -m pytest -m unit -v

# Run only fast tests (exclude slow)
/opt/miniforge/envs/casa6/bin/python -m pytest -m "unit and not slow" -v
```

### Test Coverage

Generate coverage reports:

```bash
# Run with coverage
/opt/miniforge/envs/casa6/bin/python -m pytest --cov=src/dsa110_contimg/pipeline --cov-report=html tests/unit/

# View coverage report
open htmlcov/index.html
```

## Best Practices

### 1. Use Fixtures

Create reusable fixtures for common setup:

```python
@pytest.fixture
def config():
    """Create test configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield PipelineConfig(
            paths=PathsConfig(
                input_dir=Path(tmpdir) / "input",
                output_dir=Path(tmpdir) / "output",
            )
        )

@pytest.fixture
def context(config):
    """Create test context."""
    return PipelineContext(config=config, inputs={"input_path": "/mock/input"})
```

### 2. Use Parametrize

Test multiple scenarios with parametrize:

```python
@pytest.mark.parametrize("stage_class,config_kwargs", [
    (ConversionStage, {}),
    (CalibrationStage, {}),
    (ImagingStage, {}),
])
def test_all_stages_have_cleanup(stage_class, config_kwargs):
    """Test all stages have cleanup method."""
    config = PipelineConfig(paths=PathsConfig(...))
    stage = stage_class(config, **config_kwargs)
    assert hasattr(stage, "cleanup")
    assert callable(stage.cleanup)
```

### 3. Test Edge Cases

Always test edge cases:

```python
def test_empty_input(self):
    """Test handling of empty input."""
    context = PipelineContext(config=config, inputs={"input_path": ""})
    stage = MyStage(config)

    is_valid, error_msg = stage.validate(context)
    assert not is_valid

def test_large_file(self):
    """Test handling of large files."""
    # Create large file
    large_file = create_large_file(size_mb=1000)
    context = PipelineContext(config=config, inputs={"input_path": large_file})
    stage = MyStage(config)

    # Should handle gracefully
    result = stage.execute(context)
    assert "output" in result.outputs
```

### 4. Use Descriptive Test Names

Use clear, descriptive test names:

```python
# ✓ GOOD: Descriptive name
def test_validate_fails_when_input_file_does_not_exist(self):
    """Test validation fails when input file does not exist."""
    pass

# ✗ BAD: Vague name
def test_validate(self):
    """Test validation."""
    pass
```

### 5. Test One Thing Per Test

Each test should test one specific behavior:

```python
# ✓ GOOD: Tests one thing
def test_validate_missing_input(self):
    """Test validation fails when input is missing."""
    pass

def test_validate_invalid_input(self):
    """Test validation fails when input is invalid."""
    pass

# ✗ BAD: Tests multiple things
def test_validate(self):
    """Test validation for missing and invalid inputs."""
    # Tests two different scenarios
    pass
```

## Common Issues and Solutions

### Issue: Tests Fail Due to CASA Dependencies

**Solution:** Mock CASA functions:

```python
with patch("dsa110_contimg.calibration.calibration.solve_calibration_tables") as mock_solve:
    mock_solve.return_value = {"K": "/mock/K.cal"}
    result = stage.execute(context)
```

### Issue: Tests Fail Due to File System Operations

**Solution:** Use temporary directories:

```python
with tempfile.TemporaryDirectory() as tmpdir:
    config = PipelineConfig(paths=PathsConfig(input_dir=Path(tmpdir)))
    # Test with temporary directory
```

### Issue: Tests Are Slow

**Solution:** Mock slow operations:

```python
with patch("dsa110_contimg.module.slow_operation") as mock_slow:
    mock_slow.return_value = "result"
    result = stage.execute(context)
```

## Related Documentation

- [Pipeline Stage Architecture](../concepts/pipeline_stage_architecture.md)
- [Pipeline Patterns](../concepts/pipeline_patterns.md)
- [Creating Pipeline Stages](create_pipeline_stage.md)
