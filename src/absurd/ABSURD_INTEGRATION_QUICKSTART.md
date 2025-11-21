# Absurd Integration Quick Start Guide

## Overview

This guide provides a quick overview of how to integrate Absurd into the DSA-110
continuum imaging pipeline. For detailed analysis, see
`ABSURD_INTEGRATION_ANALYSIS.md`.

## What is Absurd?

Absurd is a PostgreSQL-based durable execution workflow system that provides:

- **Automatic checkpointing** between steps
- **Built-in retry logic** with exponential backoff
- **Event-driven workflows** for coordination
- **Web UI (Habitat)** for monitoring
- **No external services** - just Postgres

## Quick Integration Steps

### 1. Install Absurd Schema

```bash
# Install absurdctl (from Absurd releases)
# Then initialize database:
absurdctl init -d dsa110_absurd
absurdctl create-queue -d dsa110_absurd dsa110-pipeline
```

### 2. Install Python Dependencies

```bash
pip install asyncpg  # For async PostgreSQL access
# Or use psycopg2 for sync access
```

### 3. Basic Integration Pattern

The simplest integration wraps your existing pipeline stages as Absurd steps:

```python
from dsa110_contimg.pipeline.workflows import standard_imaging_workflow
from dsa110_contimg.pipeline.config import PipelineConfig

# Your existing pipeline code stays the same
config = PipelineConfig.from_env()
orchestrator = standard_imaging_workflow(config)

# Wrap as Absurd task
async def pipeline_task(params, ctx):
    # Each step is checkpointed automatically
    setup = await ctx.step("setup", lambda: setup_pipeline(params))
    convert = await ctx.step("convert", lambda: run_conversion(setup))
    calibrate = await ctx.step("calibrate", lambda: run_calibration(convert))
    image = await ctx.step("image", lambda: run_imaging(calibrate))
    return {"status": "completed", "outputs": image.outputs}
```

### 4. Spawn Tasks

```python
# Spawn a pipeline task
await absurd_app.spawn("dsa110-pipeline", {
    "input_path": "/data/incoming/observation.hdf5",
    "calibrator": "0834+555"
})
```

### 5. Run Worker

```python
# Worker pulls tasks and executes them
await absurd_app.start_worker()
```

## Integration Strategies

### Strategy 1: Wrap Pipeline Stages (Recommended for Start)

- Minimal code changes
- Each stage becomes an Absurd step
- Automatic checkpointing between stages
- See `examples/absurd_integration_example.py`

### Strategy 2: Per-Stage Tasks

- Each stage is a separate Absurd task
- Coordinated via events
- Better for parallelization
- More complex but more flexible

### Strategy 3: Mosaic Orchestration

- Use Absurd for mosaic creation workflows
- Especially useful for streaming mosaics
- Event-driven coordination

### Strategy 4: Hybrid Approach

- Absurd for high-level orchestration
- Existing pipeline code for execution
- Best balance of simplicity and power

## Key Benefits

1. **Reliability**: Pipeline resumes from last checkpoint after crash
2. **Observability**: Habitat UI shows all running tasks
3. **Retry Logic**: Built-in retries with exponential backoff
4. **State Management**: All state in Postgres (survives restarts)

## Example: Basic Worker

```python
import asyncio
from absurd_client import AbsurdClient
from pipeline_adapter import AbsurdPipelineAdapter

async def main():
    # Connect to Absurd
    absurd = AbsurdClient("postgresql://localhost/dsa110_absurd")
    await absurd.connect()

    # Create adapter
    config = PipelineConfig.from_env()
    adapter = AbsurdPipelineAdapter(config, absurd)

    # Start worker
    worker = AbsurdWorker(absurd, adapter)
    await worker.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## Monitoring

### Habitat UI

Start Habitat to monitor tasks:

```bash
cd /home/ubuntu/proj/absurd/habitat
make run
# Then visit http://localhost:8080
```

### Query Tasks Directly

```sql
-- View all tasks in queue
SELECT * FROM absurd.t_dsa110_pipeline;

-- View running tasks
SELECT * FROM absurd.t_dsa110_pipeline WHERE state = 'running';

-- View failed tasks
SELECT * FROM absurd.t_dsa110_pipeline WHERE state = 'failed';

-- View checkpoints
SELECT * FROM absurd.c_dsa110_pipeline;
```

## Next Steps

1. **Review Analysis**: Read `ABSURD_INTEGRATION_ANALYSIS.md` for detailed
   strategies
2. **Try Example**: Run `examples/absurd_integration_example.py` (after setup)
3. **Start Small**: Integrate one workflow first (e.g., single mosaic creation)
4. **Monitor**: Use Habitat UI to observe execution
5. **Expand**: Gradually integrate more workflows

## Common Patterns

### Pattern 1: Simple Pipeline Execution

```python
async def simple_pipeline(params, ctx):
    result = await ctx.step("execute", lambda: run_full_pipeline(params))
    return result
```

### Pattern 2: Multi-Stage with Checkpoints

```python
async def multi_stage_pipeline(params, ctx):
    stage1 = await ctx.step("stage1", lambda: execute_stage1(params))
    stage2 = await ctx.step("stage2", lambda: execute_stage2(stage1))
    stage3 = await ctx.step("stage3", lambda: execute_stage3(stage2))
    return stage3
```

### Pattern 3: Event-Driven

```python
async def event_driven_pipeline(params, ctx):
    # Wait for external event
    event = await ctx.awaitEvent("calibration.completed")

    # Process event
    result = await ctx.step("process", lambda: process_event(event))
    return result
```

### Pattern 4: Batch Processing

```python
async def batch_pipeline(params, ctx):
    items = await ctx.step("list_items", lambda: get_items_to_process())

    results = []
    for item in items:
        result = await ctx.step(f"process_{item.id}", lambda: process_item(item))
        results.append(result)

    return {"results": results}
```

## Troubleshooting

### Task Not Claimed

- Check queue exists:
  `SELECT * FROM absurd.queues WHERE queue_name = 'dsa110-pipeline';`
- Check worker is running
- Check database connection

### Checkpoint Not Found

- Check checkpoint was saved:
  `SELECT * FROM absurd.c_dsa110_pipeline WHERE task_id = '...';`
- Verify checkpoint name matches
- Check JSON serialization

### Retry Not Working

- Check retry strategy in task parameters
- Verify error is retryable (not a permanent failure)
- Check max_attempts setting

## Resources

- **Absurd Repository**: `/home/ubuntu/proj/absurd/`
- **Absurd README**: `/home/ubuntu/proj/absurd/README.md`
- **Analysis Document**: `ABSURD_INTEGRATION_ANALYSIS.md`
- **Example Code**: `examples/absurd_integration_example.py`
- **Pipeline Code**: `dsa110_contimg/pipeline/`

## Questions?

For detailed implementation strategies, error handling patterns, and advanced
features, see `ABSURD_INTEGRATION_ANALYSIS.md`.
