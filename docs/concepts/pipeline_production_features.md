# Pipeline Production Features

**Date:** 2025-11-12  
**Last Updated:** 2025-11-12  
**Status:** complete  
**Related:** [Pipeline Stage Architecture](pipeline_stage_architecture.md)

---

## Overview

The pipeline framework includes comprehensive production-ready features for
reliability, observability, and maintainability. This document describes the
production features and how they work together.

## Production Features

### 1. Health Checks

**Location:** `pipeline/health.py`

Pre-flight health checks validate system state before starting expensive
operations:

- **Disk Space**: Verifies sufficient space for operations
- **Directory Writable**: Ensures output directories are accessible
- **Database Accessible**: Validates database connectivity
- **System Resources**: Checks memory and disk availability

**Usage:** Automatically executed before pipeline starts. Failures are logged as
warnings but don't block execution (allows override for testing).

### 2. Timeout Handling

**Location:** `pipeline/timeout.py`

Prevents stages from hanging indefinitely:

- **Signal-based timeout** (SIGALRM) on main thread
- **Threading-based timeout** for non-main threads
- **Context manager interface** for easy integration
- **Raises `TimeoutError`** when exceeded

**Usage:** Set `timeout` parameter in `StageDefinition`:

```python
StageDefinition(
    name="convert",
    stage=ConversionStage(config),
    timeout=3600.0,  # 1 hour timeout
)
```

### 3. Resource Metrics Collection

**Location:** `pipeline/observability.py`

Tracks resource usage during pipeline execution:

- **Memory Usage**: Peak RSS memory in MB
- **CPU Time**: Estimated CPU time (percentage × duration)
- **Optional Collection**: Requires `psutil`, gracefully degrades if unavailable

**Usage:** Enabled by default in `PipelineObserver`. Metrics included in
`StageMetrics` and logged.

### 4. Graceful Shutdown

**Location:** `pipeline/signals.py`

Handles SIGTERM/SIGINT signals for clean shutdown:

- **Signal Handlers**: Registers handlers for SIGTERM and SIGINT
- **Cleanup Callback**: Executes cleanup function on shutdown
- **Context Manager**: Wraps entire pipeline execution
- **Windows Compatible**: Uses SIGINT only on Windows

**Usage:** Automatically wraps pipeline execution. Cleanup handled by stage
cleanup methods.

### 5. Output Validation

**Location:** `pipeline/stages.py`, `pipeline/stages_impl.py`

Validates stage outputs before proceeding:

- **Post-execution validation**: Checks outputs after successful execution
- **Early failure detection**: Catches invalid outputs before downstream stages
- **Standardized interface**: `validate_outputs()` method on all stages

**Implementation:**

- `ConversionStage`: Validates MS exists, has required columns, contains data
- `CalibrationSolveStage`: Validates calibration tables exist
- `CalibrationStage`: Validates CORRECTED_DATA column exists and is populated
- `ImagingStage`: Validates image files exist and are readable

### 6. Partial Output Cleanup

**Location:** `pipeline/orchestrator.py`, `pipeline/stages_impl.py`

Cleans up partial outputs when stages fail:

- **Automatic cleanup**: Called on both success and failure
- **Prevents accumulation**: Removes corrupted/partial files
- **Stage-specific**: Each stage implements cleanup for its outputs

**Implementation:**

- `ConversionStage`: Removes partial MS files
- `CalibrationSolveStage`: Removes partial calibration tables
- `ImagingStage`: Removes partial image files (all related suffixes)

### 7. Error Handling and Retry

**Location:** `pipeline/resilience.py`, `pipeline/orchestrator.py`

Robust error handling with configurable retry policies:

- **Retry Policies**: Exponential backoff, fixed interval, immediate
- **Retryable Errors**: Configurable error filtering
- **Continue on Failure**: Optional pipeline continuation after stage failure

**Usage:** Configure retry policy in `StageDefinition`:

```python
retry_policy = RetryPolicy(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    initial_delay=1.0,
    max_delay=60.0,
)
```

## Integration

All features are integrated into `PipelineOrchestrator`:

1. **Health Check**: Executed before pipeline starts
2. **Graceful Shutdown**: Wraps entire execution
3. **Timeout**: Applied per-stage if specified
4. **Resource Metrics**: Collected automatically
5. **Output Validation**: Performed after each stage
6. **Cleanup**: Called on both success and failure

## Configuration

Production features are enabled by default. To disable:

```python
# Disable resource metrics collection
observer = PipelineObserver(collect_resource_metrics=False)

# Skip health check (not recommended)
# Health check failures are logged as warnings, not errors

# Disable timeout (not recommended)
# Set timeout=None in StageDefinition
```

## Monitoring

All production features emit structured logs:

- **Health Checks**: Logged at INFO level
- **Timeouts**: Logged at ERROR level
- **Resource Metrics**: Included in stage completion logs
- **Shutdown Signals**: Logged at WARNING level
- **Output Validation**: Logged at INFO/ERROR level
- **Cleanup**: Logged at INFO/WARNING level

## See Also

- [Pipeline Overview](./pipeline_overview.md) - High-level pipeline overview
- [Pipeline Stage Architecture](./pipeline_stage_architecture.md) - Stage-based
  architecture
- [Pipeline Workflow Visualization](./pipeline_workflow_visualization.md) -
  Detailed workflow

## References

- [Pipeline Stage Architecture](./pipeline_stage_architecture.md) - Orchestrator
  details
- [Stage Implementation Guide](../how-to/create_pipeline_stage.md)
