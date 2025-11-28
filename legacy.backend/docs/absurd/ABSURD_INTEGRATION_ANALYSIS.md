# Absurd Integration Analysis for DSA-110 Continuum Imaging Pipeline

## Executive Summary

This document explores integration strategies for incorporating
[Absurd](https://github.com/earendil-works/absurd) - a PostgreSQL-based durable
execution workflow system - into the DSA-110 continuum imaging pipeline. Absurd
provides durable task execution with automatic retries, checkpointing, and
event-driven workflows, which could significantly enhance the reliability and
observability of the radio astronomy data processing pipeline.

## Current Pipeline Architecture

### Pipeline Components

The DSA-110 continuum imaging pipeline (`dsa110-contimg`) consists of:

1. **Stage-Based Pipeline** (`dsa110_contimg/pipeline/`):
   - `PipelineOrchestrator`: Manages stage execution with dependency resolution
   - `PipelineStage`: Abstract base class for pipeline stages
   - Concrete stages: `CatalogSetupStage`, `ConversionStage`,
     `CalibrationSolveStage`, `CalibrationStage`, `ImagingStage`,
     `ValidationStage`, etc.
   - `PipelineContext`: Carries state between stages
   - `PipelineConfig`: Configuration management

2. **Mosaic Orchestration** (`dsa110_contimg/mosaic/`):
   - `MosaicOrchestrator`: High-level mosaic creation logic
   - `StreamingMosaicManager`: Processes groups of MS files
   - Handles transit selection, calibration, imaging, and mosaic assembly

3. **Workflow Patterns**:
   - Standard workflow: Convert → Solve Calibration → Apply Calibration → Image
   - Reprocessing workflows
   - Batch processing for multiple transits

### Current State Management

- **SQLite databases**: Products DB, HDF5 index DB, calibration registry, data
  registry
- **File-based state**: Status files, error logs
- **In-memory state**: Pipeline context passed between stages
- **No durable execution**: If a process crashes mid-pipeline, work is lost

## Absurd Overview

### Key Features

1. **Durable Execution**: Tasks survive crashes, restarts, and network failures
2. **Automatic Checkpointing**: Each step is checkpointed automatically
3. **Retry Logic**: Built-in retry strategies with exponential backoff
4. **Event-Driven**: Tasks can suspend and wait for events
5. **Postgres-Based**: All state stored in PostgreSQL (no external services)
6. **Pull-Based**: Workers pull tasks from queues
7. **Web UI**: Habitat provides visibility into running tasks

### Core Concepts

- **Queue**: Named queue for organizing tasks
- **Task**: A unit of work with parameters
- **Run**: An attempt to execute a task
- **Step**: A checkpointed operation within a task
- **Checkpoint**: Saved state for a step
- **Event**: External signals that tasks can wait for

## Integration Strategies

### Strategy 1: Wrap Pipeline Stages as Absurd Tasks (Recommended)

**Approach**: Each pipeline stage becomes an Absurd step, with the full pipeline
as a single Absurd task.

**Benefits**:

- Minimal changes to existing pipeline code
- Automatic checkpointing between stages
- Built-in retry logic per stage
- Full observability through Habitat UI

**Implementation**:

```python
# New file: dsa110_contimg/pipeline/absurd_adapter.py

from typing import Dict, Any
from dsa110_contimg.pipeline.orchestrator import PipelineOrchestrator
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.config import PipelineConfig

class AbsurdPipelineAdapter:
    """Adapter to run pipeline stages as Absurd tasks."""

    def __init__(self, config: PipelineConfig, absurd_client):
        self.config = config
        self.absurd = absurd_client
        self.orchestrator = None  # Will be created per workflow

    async def execute_pipeline_task(self, params: Dict[str, Any], ctx):
        """Execute pipeline as Absurd task with checkpointed steps."""

        # Step 1: Setup (checkpointed)
        setup_result = await ctx.step("setup", async () => {
            return self._setup_pipeline(params)
        })

        # Step 2: Catalog setup (checkpointed)
        catalog_status = await ctx.step("catalog_setup", async () => {
            return self._execute_stage("catalog_setup", setup_result.context)
        })

        # Step 3: Conversion (checkpointed)
        conversion_result = await ctx.step("convert", async () => {
            return self._execute_stage("convert", catalog_status.context)
        })

        # Step 4: Calibration solve (checkpointed)
        cal_solve_result = await ctx.step("calibrate_solve", async () => {
            return self._execute_stage("calibrate_solve", conversion_result.context)
        })

        # Step 5: Calibration apply (checkpointed)
        cal_apply_result = await ctx.step("calibrate_apply", async () => {
            return self._execute_stage("calibrate_apply", cal_solve_result.context)
        })

        # Step 6: Imaging (checkpointed)
        imaging_result = await ctx.step("image", async () => {
            return self._execute_stage("image", cal_apply_result.context)
        })

        # Step 7: Validation (checkpointed, optional)
        if self.config.validation.enabled:
            validation_result = await ctx.step("validate", async () => {
                return self._execute_stage("validate", imaging_result.context)
            })

        return {
            "status": "completed",
            "outputs": imaging_result.context.outputs
        }

    def _setup_pipeline(self, params):
        """Initialize pipeline orchestrator."""
        from dsa110_contimg.pipeline.workflows import standard_imaging_workflow
        self.orchestrator = standard_imaging_workflow(self.config)
        initial_context = PipelineContext(
            config=self.config,
            inputs=params
        )
        return {"context": initial_context}

    def _execute_stage(self, stage_name: str, context: PipelineContext):
        """Execute a single pipeline stage."""
        stage_def = self.orchestrator.stages[stage_name]
        result = self.orchestrator._execute_stage(stage_def, context)
        return {"context": result.context, "status": result.status}
```

**Usage**:

```python
# Register the task
absurd_app.register_task(
    {"name": "dsa110-pipeline"},
    execute_pipeline_task
)

# Spawn a pipeline task
await absurd_app.spawn("dsa110-pipeline", {
    "input_path": "/data/incoming/observation.hdf5",
    "calibrator": "0834+555",
    "output_dir": "/stage/dsa110-contimg/mosaics"
})
```

### Strategy 2: Per-Stage Tasks with Event Coordination

**Approach**: Each pipeline stage is a separate Absurd task, coordinated via
events.

**Benefits**:

- Fine-grained control and observability
- Stages can be retried independently
- Natural parallelization opportunities
- Better resource management

**Implementation**:

```python
class AbsurdStageCoordinator:
    """Coordinate pipeline stages as separate Absurd tasks."""

    async def conversion_task(self, params: Dict[str, Any], ctx):
        """Conversion stage as Absurd task."""
        result = await ctx.step("convert", async () => {
            # Execute conversion stage
            return execute_conversion_stage(params)
        })

        # Emit event for next stage
        await self.absurd.emit_event(
            f"conversion.completed:{params['job_id']}",
            {"ms_paths": result.ms_paths, "context": result.context}
        )

        return result

    async def calibration_task(self, params: Dict[str, Any], ctx):
        """Calibration stage waits for conversion event."""
        # Wait for conversion to complete
        conversion_event = await ctx.awaitEvent(
            f"conversion.completed:{params['job_id']}"
        )

        # Execute calibration
        result = await ctx.step("calibrate", async () => {
            return execute_calibration_stage(conversion_event.data)
        })

        # Emit event for imaging stage
        await self.absurd.emit_event(
            f"calibration.completed:{params['job_id']}",
            {"cal_tables": result.cal_tables, "context": result.context}
        )

        return result
```

### Strategy 3: Mosaic Orchestration with Absurd

**Approach**: Use Absurd to manage the mosaic creation workflow, especially for
streaming mosaics.

**Benefits**:

- Durable state for long-running mosaic processes
- Automatic retry for failed mosaic groups
- Event-driven coordination between mosaic steps
- Better handling of multi-transit workflows

**Implementation**:

```python
class AbsurdMosaicOrchestrator:
    """Mosaic orchestrator using Absurd for durable execution."""

    async def create_mosaic_task(self, params: Dict[str, Any], ctx):
        """Create mosaic with checkpointed steps."""

        # Step 1: Find available transits
        transits = await ctx.step("find_transits", async () => {
            return self.orchestrator.list_available_transits_with_quality()
        })

        # Step 2: Select transit (checkpointed)
        selected_transit = await ctx.step("select_transit", async () => {
            return self._select_transit(transits, params)
        })

        # Step 3: Process group workflow (checkpointed)
        mosaic_path = await ctx.step("process_group", async () => {
            return self.orchestrator._process_group_workflow(
                selected_transit.group_id,
                min_ms_count=params.get("min_ms_count", 10)
            )
        })

        # Step 4: Wait for publishing (event-driven)
        if params.get("wait_for_published", False):
            await ctx.awaitEvent(f"mosaic.published:{mosaic_path}")

        return {"mosaic_path": mosaic_path, "transit": selected_transit}

    async def batch_mosaic_task(self, params: Dict[str, Any], ctx):
        """Create multiple mosaics with checkpointing."""
        transits = await ctx.step("list_transits", async () => {
            return self.orchestrator.list_available_transits_with_quality()
        })

        results = []
        for transit in transits:
            result = await ctx.step(f"mosaic_{transit.group_id}", async () => {
                return await self.create_mosaic_task({
                    **params,
                    "transit": transit
                }, ctx)
            })
            results.append(result)

        return {"results": results, "count": len(results)}
```

### Strategy 4: Hybrid Approach - Absurd for Long-Running Workflows

**Approach**: Use Absurd for high-level workflow orchestration, keep existing
pipeline stages for low-level execution.

**Benefits**:

- Minimal disruption to existing code
- Absurd handles workflow-level concerns (retries, state)
- Existing stages handle domain logic
- Best of both worlds

**Implementation**:

```python
class HybridWorkflowManager:
    """Hybrid approach: Absurd orchestrates, pipeline executes."""

    async def full_pipeline_workflow(self, params: Dict[str, Any], ctx):
        """High-level workflow managed by Absurd."""

        # Checkpoint: Workflow started
        workflow_state = await ctx.step("workflow_init", async () => {
            return {
                "job_id": params["job_id"],
                "started_at": datetime.now().isoformat(),
                "status": "running"
            }
        })

        # Execute pipeline (existing code, wrapped in step)
        pipeline_result = await ctx.step("execute_pipeline", async () => {
            # Use existing PipelineOrchestrator
            orchestrator = standard_imaging_workflow(self.config)
            result = orchestrator.execute(
                PipelineContext(config=self.config, inputs=params)
            )
            return {
                "status": result.status.value,
                "outputs": result.context.outputs,
                "stage_results": {
                    name: {
                        "status": r.status.value,
                        "duration": r.duration_seconds
                    }
                    for name, r in result.stage_results.items()
                }
            }
        })

        # Checkpoint: Workflow completed
        await ctx.step("workflow_complete", async () => {
            return {
                **workflow_state,
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "pipeline_result": pipeline_result
            }
        })

        return pipeline_result
```

## Implementation Recommendations

### Phase 1: Proof of Concept (Low Risk)

1. **Create Absurd Adapter Module**:
   - New module: `dsa110_contimg/pipeline/absurd_adapter.py`
   - Wrap existing `PipelineOrchestrator` with Absurd task interface
   - Test with single pipeline execution

2. **Database Setup**:
   - Install Absurd SQL schema in existing Postgres (or new database)
   - Create queue: `dsa110-pipeline`
   - Test basic task spawning and execution

3. **Worker Process**:
   - Create simple worker script that pulls tasks from Absurd queue
   - Execute pipeline stages as Absurd steps
   - Log results back to Absurd

### Phase 2: Integration (Medium Risk)

1. **Mosaic Orchestration**:
   - Integrate Absurd into `MosaicOrchestrator`
   - Use Absurd for batch mosaic creation
   - Add event-driven coordination for publishing

2. **API Integration**:
   - Update API endpoints to spawn Absurd tasks instead of direct execution
   - Add Absurd task status endpoints
   - Integrate Habitat UI for monitoring

3. **Error Handling**:
   - Map pipeline errors to Absurd retry policies
   - Add custom retry logic for transient failures
   - Improve error reporting through Absurd checkpoints

### Phase 3: Full Integration (Higher Risk)

1. **Replace Existing Orchestration**:
   - Migrate all workflows to Absurd
   - Remove custom retry logic (use Absurd's)
   - Consolidate state management in Postgres

2. **Advanced Features**:
   - Event-driven workflows for external triggers
   - Parallel stage execution with Absurd coordination
   - Long-running workflows (days/weeks) with suspension

## Technical Considerations

### Database Choice

**Option A: Separate Postgres Database**

- Pros: Isolation, easier to manage
- Cons: Additional database to maintain

**Option B: Shared Postgres Database**

- Pros: Single database, easier deployment
- Cons: Schema mixing, potential conflicts

**Recommendation**: Start with separate database, migrate to shared if needed.

### Python SDK

Absurd currently has a TypeScript SDK. For Python integration:

1. **Option 1**: Use PostgreSQL client directly (psycopg2/asyncpg)
   - Call Absurd stored procedures directly
   - More control, but more code

2. **Option 2**: Create Python SDK wrapper
   - Wrap Absurd SQL functions in Python classes
   - Better ergonomics, reusable

3. **Option 3**: Use HTTP API (if Absurd adds one)
   - Future-proof, but may not exist yet

**Recommendation**: Start with Option 1 (direct SQL), create wrapper if needed.

### State Serialization

Pipeline context needs to be serialized for checkpoints:

```python
def serialize_context(context: PipelineContext) -> Dict[str, Any]:
    """Serialize pipeline context for Absurd checkpoint."""
    return {
        "inputs": context.inputs,
        "outputs": context.outputs,
        "metadata": context.metadata,
        # Exclude non-serializable objects (reconstruct on resume)
        "config_ref": context.config.paths.model_dump()
    }

def deserialize_context(data: Dict[str, Any], config: PipelineConfig) -> PipelineContext:
    """Deserialize pipeline context from Absurd checkpoint."""
    return PipelineContext(
        config=config,
        inputs=data["inputs"],
        outputs=data["outputs"],
        metadata=data.get("metadata", {})
    )
```

### Error Handling

Map pipeline errors to Absurd retry strategies:

```python
def should_retry(error: Exception) -> bool:
    """Determine if error should trigger retry."""
    # Transient errors: retry
    if isinstance(error, (TimeoutError, ConnectionError, OSError)):
        return True

    # Data errors: don't retry
    if isinstance(error, (ValueError, KeyError, FileNotFoundError)):
        return False

    # CASA errors: check error message
    if "CASA" in str(error):
        if "timeout" in str(error).lower():
            return True
        if "disk full" in str(error).lower():
            return False

    # Default: retry once
    return True
```

## Benefits of Integration

### Reliability

- **Automatic Recovery**: Pipeline resumes from last checkpoint after crash
- **Retry Logic**: Built-in retry with exponential backoff
- **State Persistence**: All state stored in Postgres (survives restarts)

### Observability

- **Habitat UI**: Visual dashboard for all running tasks
- **Checkpoint History**: See exactly where pipeline failed
- **Task Status**: Real-time status of all pipeline executions

### Scalability

- **Worker Pool**: Multiple workers can pull tasks from queue
- **Parallel Execution**: Natural parallelization with event coordination
- **Resource Management**: Control concurrency through queue configuration

### Maintainability

- **Simplified Code**: Less custom retry/state management code
- **Standard Patterns**: Use Absurd's proven patterns
- **Better Testing**: Test workflows independently

## Risks and Mitigations

### Risk 1: Additional Complexity

**Mitigation**: Start with simple adapter pattern, don't rewrite everything at
once.

### Risk 2: Database Dependency

**Mitigation**: Absurd uses Postgres (likely already available), no new services
needed.

### Risk 3: Learning Curve

**Mitigation**: Absurd is designed to be simple, start with basic integration.

### Risk 4: Performance Overhead

**Mitigation**: Checkpointing overhead is minimal (JSON writes to Postgres),
test with real workloads.

## Next Steps

1. **Review and Feedback**: Review this analysis with team
2. **Proof of Concept**: Implement Phase 1 (simple adapter)
3. **Test with Real Data**: Run proof of concept with actual pipeline
4. **Evaluate Results**: Assess benefits vs. complexity
5. **Decide on Full Integration**: Proceed to Phase 2/3 if successful

## References

- [Absurd GitHub Repository](https://github.com/earendil-works/absurd)
- [Absurd README](file:///home/ubuntu/proj/absurd/README.md)
- [DSA-110 Pipeline Documentation](file:///data/dsa110-contimg/src/docs/)
- Current Pipeline Code: `dsa110_contimg/pipeline/`

## Appendix: Example Integration Code

See `examples/absurd_integration_example.py` for a complete working example of
Strategy 1 (wrap pipeline stages as Absurd tasks).
