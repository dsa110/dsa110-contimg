# Pipeline Framework Testing Strategy

This document outlines a comprehensive testing approach for the new pipeline orchestration framework.

## Testing Philosophy

1. **Test in Isolation**: Unit tests for individual components
2. **Test Integration**: Integration tests for component interactions
3. **Test End-to-End**: E2E tests with mocked external dependencies
4. **Fast Feedback**: Prioritize fast tests, use mocks for slow operations
5. **Realistic Scenarios**: Test common workflows and edge cases

## Test Structure

```
tests/
├── unit/
│   ├── test_pipeline_context.py      # Context operations
│   ├── test_pipeline_config.py       # Config validation
│   ├── test_state_repository.py      # State persistence
│   ├── test_resource_manager.py      # Resource cleanup
│   ├── test_retry_policy.py          # Retry logic
│   └── test_workflow_builder.py     # Workflow composition
├── integration/
│   ├── test_orchestrator.py          # Orchestrator with mock stages
│   ├── test_observer.py              # Observer integration
│   └── test_stage_execution.py       # Stage execution flow
├── e2e/
│   ├── test_conversion_stage.py      # ConversionStage with mocks
│   ├── test_full_workflow.py         # Complete workflow execution
│   └── test_adapter.py               # Legacy adapter integration
└── fixtures/
    ├── conftest.py                   # Shared fixtures
    ├── mock_stages.py                # Mock stage implementations
    └── test_data.py                  # Test data generators
```

## Testing Levels

### 1. Unit Tests

**Goal**: Test individual components in complete isolation.

**Components to Test**:
- `PipelineContext`: Immutability, output merging
- `PipelineConfig`: Validation, from_dict, from_env
- `StateRepository`: CRUD operations (both implementations)
- `ResourceManager`: Temp file/dir lifecycle
- `RetryPolicy`: Retry logic, delay calculation
- `WorkflowBuilder`: Stage addition, dependency validation

**Mocking Strategy**:
- No external dependencies
- Use in-memory implementations where possible
- Mock file system operations

### 2. Integration Tests

**Goal**: Test components working together.

**Scenarios**:
- Orchestrator executing multiple stages
- Dependency resolution and ordering
- Observer collecting metrics
- State repository persisting across stages
- Resource cleanup across stage failures

**Mocking Strategy**:
- Mock stages (fast, predictable)
- Real orchestrator, observer, state repository
- In-memory state repository for speed

### 3. End-to-End Tests

**Goal**: Test complete workflows with realistic scenarios.

**Scenarios**:
- Full workflow execution (convert → calibrate → image)
- Error handling and recovery
- Retry policies in action
- Adapter layer with legacy database

**Mocking Strategy**:
- Mock external dependencies (CASA, file I/O)
- Use minimal test data
- Real pipeline components

## Key Testing Patterns

### 1. Mock Stages

Create reusable mock stages for testing orchestrator logic:

```python
class MockStage(PipelineStage):
    """Mock stage for testing orchestrator."""
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.executed = False
    
    def execute(self, context):
        self.executed = True
        if self.should_fail:
            raise ValueError(f"Mock failure: {self.name}")
        return context.with_output(f"{self.name}_output", "value")
    
    def validate(self, context):
        return True, None
```

### 2. Test Fixtures

Use pytest fixtures for common setup:

```python
@pytest.fixture
def test_config():
    """Standard test configuration."""
    return PipelineConfig(
        paths=PathsConfig(
            input_dir=Path("/test/input"),
            output_dir=Path("/test/output"),
        )
    )

@pytest.fixture
def test_context(test_config):
    """Standard test context."""
    return PipelineContext(config=test_config, job_id=1)

@pytest.fixture
def in_memory_repo():
    """In-memory state repository for fast tests."""
    return InMemoryStateRepository()
```

### 3. Parametrized Tests

Test multiple scenarios efficiently:

```python
@pytest.mark.parametrize("max_attempts,expected_delays", [
    (3, [1.0, 2.0, 4.0]),
    (5, [1.0, 2.0, 4.0, 8.0, 10.0]),  # Capped at max_delay
])
def test_exponential_backoff(max_attempts, expected_delays):
    policy = RetryPolicy(
        max_attempts=max_attempts,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        initial_delay=1.0,
        max_delay=10.0,
    )
    for attempt, expected in enumerate(expected_delays, 1):
        assert policy.get_delay(attempt) == expected
```

### 4. Test Isolation

Each test should be independent:

```python
def test_orchestrator_execution(tmp_path):
    """Test orchestrator with isolated temp directory."""
    # Each test gets its own temp directory
    config = PipelineConfig(
        paths=PathsConfig(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
        )
    )
    # ... test code
```

## Specific Test Cases

### Orchestrator Tests

1. **Dependency Resolution**:
   - Simple linear chain (A → B → C)
   - Parallel stages (A → [B, C] → D)
   - Circular dependency detection
   - Missing dependency detection

2. **Execution Flow**:
   - Successful execution
   - Stage failure handling
   - Retry on failure
   - Skip on prerequisite failure

3. **Context Passing**:
   - Outputs from one stage available to next
   - Context immutability
   - Metadata preservation

### Stage Tests

1. **ConversionStage**:
   - Validation (missing inputs, invalid paths)
   - Successful conversion (mocked)
   - MS discovery after conversion
   - MS index update

2. **CalibrationStage**:
   - Prerequisite validation (MS exists)
   - Calibration application (mocked)
   - State update

3. **ImagingStage**:
   - Prerequisite validation
   - Image creation (mocked)
   - Artifact tracking

### Observer Tests

1. **Logging**:
   - Stage start/complete/fail events
   - Pipeline start/complete events
   - Error context captured

2. **Metrics**:
   - Duration tracking
   - Metrics aggregation
   - Summary generation

### Adapter Tests

1. **Legacy Compatibility**:
   - Job creation in legacy format
   - Status updates
   - Log appending
   - Artifact collection

2. **Error Handling**:
   - Pipeline failures logged correctly
   - Database state consistent
   - Error messages preserved

## Test Data Management

### Minimal Test MS

For tests that need actual MS files, use minimal test data:

```python
@pytest.fixture
def minimal_ms(tmp_path):
    """Create minimal test MS file."""
    ms_path = tmp_path / "test.ms"
    # Use test_utils.create_minimal_test_ms() or mock
    return ms_path
```

### Mock File System

For tests that need file operations:

```python
from unittest.mock import patch, MagicMock

@patch('pathlib.Path.exists')
@patch('pathlib.Path.mkdir')
def test_conversion_stage_validation(mock_mkdir, mock_exists):
    mock_exists.return_value = True
    # ... test validation logic
```

## Performance Considerations

1. **Fast Tests**: Use in-memory repositories, mock file I/O
2. **Slow Tests**: Mark with `@pytest.mark.slow`, run separately
3. **Parallel Execution**: Use `pytest-xdist` for parallel test runs

## Continuous Integration

1. **Unit Tests**: Run on every commit (< 1 minute)
2. **Integration Tests**: Run on PR (< 5 minutes)
3. **E2E Tests**: Run on merge to main (< 15 minutes)

## Coverage Goals

- **Unit Tests**: 90%+ coverage for core components
- **Integration Tests**: All major workflows covered
- **E2E Tests**: Critical paths validated

## Example Test Structure

```python
# tests/integration/test_orchestrator.py
import pytest
from dsa110_contimg.pipeline import (
    PipelineOrchestrator, StageDefinition, PipelineContext,
    PipelineConfig, PathsConfig
)
from tests.fixtures.mock_stages import MockStage

class TestOrchestrator:
    """Integration tests for PipelineOrchestrator."""
    
    def test_linear_execution(self, test_config):
        """Test simple linear stage execution."""
        context = PipelineContext(config=test_config)
        stages = [
            StageDefinition("stage1", MockStage("stage1"), []),
            StageDefinition("stage2", MockStage("stage2"), ["stage1"]),
        ]
        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(context)
        
        assert result.status == PipelineStatus.COMPLETED
        assert "stage1_output" in result.context.outputs
        assert "stage2_output" in result.context.outputs
    
    def test_parallel_stages(self, test_config):
        """Test parallel stage execution."""
        context = PipelineContext(config=test_config)
        stages = [
            StageDefinition("stage1", MockStage("stage1"), []),
            StageDefinition("stage2a", MockStage("stage2a"), ["stage1"]),
            StageDefinition("stage2b", MockStage("stage2b"), ["stage1"]),
            StageDefinition("stage3", MockStage("stage3"), ["stage2a", "stage2b"]),
        ]
        orchestrator = PipelineOrchestrator(stages)
        result = orchestrator.execute(context)
        
        assert result.status == PipelineStatus.COMPLETED
        # Both stage2a and stage2b should complete before stage3
        assert "stage2a_output" in result.context.outputs
        assert "stage2b_output" in result.context.outputs
        assert "stage3_output" in result.context.outputs
    
    def test_circular_dependency(self, test_config):
        """Test circular dependency detection."""
        context = PipelineContext(config=test_config)
        stages = [
            StageDefinition("stage1", MockStage("stage1"), ["stage2"]),
            StageDefinition("stage2", MockStage("stage2"), ["stage1"]),
        ]
        orchestrator = PipelineOrchestrator(stages)
        
        with pytest.raises(ValueError, match="Circular dependency"):
            orchestrator.execute(context)
```

## Next Steps

1. Create test fixtures (`conftest.py`)
2. Implement mock stages (`mock_stages.py`)
3. Write unit tests for each component
4. Write integration tests for orchestrator
5. Write E2E tests for complete workflows
6. Set up CI/CD test execution
7. Monitor test coverage and add tests for gaps

