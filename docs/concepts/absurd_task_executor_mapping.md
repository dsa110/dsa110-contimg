# Absurd Task Executor Mapping

## Pipeline Stages Analysis

Based on the DSA-110 pipeline structure, here are the 9 stages that can be
mapped to Absurd tasks:

### 1. CatalogSetupStage

- **Purpose**: Download and prepare reference catalogs (NVSS, VLASS, ATNF)
- **Inputs**: Catalog names, output directories
- **Outputs**: Downloaded catalog files
- **Absurd Task**: `catalog-setup`
- **Priority**: Low (can run independently, infrequent)
- **Duration**: Medium (minutes)

### 2. ConversionStage

- **Purpose**: Convert UVH5 visibility data to CASA Measurement Sets (MS)
- **Inputs**: UVH5 file paths, output directory
- **Outputs**: MS file paths
- **Absurd Task**: `convert-uvh5-to-ms`
- **Priority**: High (first step in data processing)
- **Duration**: Medium-Long (depends on data size)

### 3. CalibrationSolveStage

- **Purpose**: Solve for calibration solutions (gains, bandpass)
- **Inputs**: MS path, calibrator info
- **Outputs**: Calibration table paths
- **Absurd Task**: `calibration-solve`
- **Priority**: High (blocking for imaging)
- **Duration**: Long (CASA computations)

### 4. CalibrationStage

- **Purpose**: Apply calibration solutions to measurement set
- **Inputs**: MS path, calibration tables
- **Outputs**: Calibrated MS path
- **Absurd Task**: `calibration-apply`
- **Priority**: High (blocking for imaging)
- **Duration**: Medium

### 5. ImagingStage

- **Purpose**: Generate sky images from calibrated visibilities
- **Inputs**: Calibrated MS path, imaging parameters
- **Outputs**: FITS image files
- **Absurd Task**: `imaging`
- **Priority**: High (main science product)
- **Duration**: Very Long (tclean iterations)

### 6. OrganizationStage

- **Purpose**: Organize output files into proper directory structure
- **Inputs**: File paths, organization rules
- **Outputs**: Organized file paths
- **Absurd Task**: `organize-files`
- **Priority**: Low (housekeeping)
- **Duration**: Fast

### 7. ValidationStage

- **Purpose**: Validate images against reference catalogs (flux, astrometry)
- **Inputs**: Image path, catalog name
- **Outputs**: Validation report
- **Absurd Task**: `validation`
- **Priority**: Medium (QA check)
- **Duration**: Medium

### 8. CrossMatchStage

- **Purpose**: Cross-match detected sources with catalogs
- **Inputs**: Source list, catalog name
- **Outputs**: Cross-match results
- **Absurd Task**: `crossmatch`
- **Priority**: Medium (science analysis)
- **Duration**: Medium

### 9. AdaptivePhotometryStage

- **Purpose**: Extract photometry with adaptive binning
- **Inputs**: MS path, source coordinates
- **Outputs**: Photometry measurements
- **Absurd Task**: `photometry`
- **Priority**: Medium (science measurements)
- **Duration**: Long (many sources)

## Task Executor Design

### Task Name Convention

Use kebab-case with descriptive names:

- `convert-uvh5-to-ms`
- `calibration-solve`
- `calibration-apply`
- `imaging`
- `validation`
- `crossmatch`
- `photometry`
- `organize-files`
- `catalog-setup`

### Task Parameter Structure

```python
{
    "task_name": str,       # One of the tasks above
    "ms_path": str,         # Path to measurement set (most tasks)
    "image_path": str,      # Path to image (validation, etc.)
    "config": dict,         # Stage-specific configuration
    "priority": int,        # Task priority (0-10)
    "dependencies": list,   # List of task IDs this depends on
}
```

### Task Result Structure

```python
{
    "status": str,          # "success" or "error"
    "stage": str,           # Stage name
    "outputs": dict,        # Stage-specific outputs
    "metrics": dict,        # Execution metrics
    "message": str,         # Human-readable status
    "error": str | None,    # Error message if failed
}
```

## Implementation Strategy

### Phase 3a: Core Processing Tasks (High Priority)

1. `convert-uvh5-to-ms` - Essential for any data processing
2. `calibration-solve` - Essential for imaging
3. `calibration-apply` - Essential for imaging
4. `imaging` - Main science product

### Phase 3b: Analysis Tasks (Medium Priority)

5. `validation` - QA checking
6. `crossmatch` - Source identification
7. `photometry` - Time-domain science

### Phase 3c: Utility Tasks (Low Priority)

8. `organize-files` - Housekeeping
9. `catalog-setup` - One-time setup

## Workflow Orchestration

### Example: Full Pipeline Workflow

```python
# Spawn tasks with dependencies
convert_task = await client.spawn_task(
    queue_name="dsa110-pipeline",
    task_name="convert-uvh5-to-ms",
    params={
        "uvh5_path": "/data/incoming/2025-11-18T12:00:00.hdf5",
        "output_dir": "/stage/dsa110-contimg/raw/ms"
    },
    priority=10
)

cal_solve_task = await client.spawn_task(
    queue_name="dsa110-pipeline",
    task_name="calibration-solve",
    params={
        "ms_path": "<output_from_convert>",
        "calibrator": "3C286"
    },
    priority=9,
    # Note: Dependencies would need to be handled by adapter
)

imaging_task = await client.spawn_task(
    queue_name="dsa110-pipeline",
    task_name="imaging",
    params={
        "ms_path": "<output_from_calibration>",
        "imsize": 4096
    },
    priority=8
)
```

### Dependency Handling Options

**Option A: Manual Chaining**

- User/API spawns tasks sequentially after each completes
- Simple but requires active monitoring

**Option B: Adapter-Level Chaining**

- Adapter spawns next task upon completion
- Requires storing workflow state

**Option C: Workflow Manager (Future)**

- Dedicated workflow orchestration layer
- Could use Absurd tasks or separate system

## Error Handling Strategy

### Retry Logic

- Use Absurd's built-in retry mechanism (`max_retries` config)
- Different retry strategies per task type:
  - `imaging`: 2 retries (may fail on transient CASA issues)
  - `conversion`: 1 retry (usually deterministic)
  - `calibration`: 3 retries (solver can be finicky)

### Circuit Breaker Integration

- Existing circuit breakers should monitor Absurd task failures
- If too many tasks fail, circuit breaker opens
- Prevents cascading failures

### Dead Letter Queue

- Failed tasks after max retries go to DLQ
- DLQ stats available via existing `/api/dlq/stats`
- Manual intervention required for DLQ items

## Resource Management

### Concurrency Limits

- Set `ABSURD_WORKER_CONCURRENCY` based on available resources
- Imaging tasks are memory-intensive (8-16 GB each)
- Suggested: 2-4 imaging workers, 4-8 total workers

### Task Priorities

- Calibration: 9-10 (highest - blocks imaging)
- Imaging: 7-8 (high - main product)
- Photometry/Validation: 5-6 (medium)
- Organization: 1-2 (low - can wait)

### Timeouts

- `imaging`: 3600s (1 hour)
- `calibration-solve`: 1800s (30 min)
- `conversion`: 900s (15 min)
- `validation`: 300s (5 min)

## Monitoring & Observability

### Metrics to Track

- Tasks spawned per stage
- Task completion time per stage
- Task failure rate per stage
- Queue depth per priority
- Worker utilization

### Integration Points

- Existing metrics system: `src/dsa110_contimg/pipeline/metrics.py`
- Existing event bus: `src/dsa110_contimg/pipeline/event_bus.py`
- Circuit breakers: `src/dsa110_contimg/pipeline/circuit_breaker.py`

### Dashboard Visualizations

- Task timeline (Gantt chart)
- Queue depth over time
- Stage-wise success/failure rates
- Worker utilization
- Task duration distributions

## Next Steps

1. **Review & Approve** this mapping
2. **Implement Core Executors** (Phase 3a tasks)
3. **Test with Single Stage** (start with `conversion`)
4. **Add Integration Tests**
5. **Expand to All Stages**
6. **Add Workflow Orchestration**
7. **Production Deployment**
