# Implementing Absurd Task Executors

**Date:** 2025-11-18  
**Type:** Implementation Guide  
**Status:** 📋 Planned - Phase 3

---

## Overview

This guide provides step-by-step instructions for implementing Absurd task
executors for DSA-110 pipeline stages. Each executor wraps an existing pipeline
stage to run via the Absurd durable workflow manager.

## Prerequisites

- Phase 1 & 2 complete (Infrastructure + Integration)
- Absurd database set up and running
- FastAPI server with Absurd router registered
- Understanding of pipeline stages (see
  `docs/concepts/absurd_task_executor_mapping.md`)

## Implementation Pattern

### Step 1: Create Executor Function

Each executor follows this pattern:

```python
async def execute_<stage_name>(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute <stage> via Absurd.

    Args:
        params: Task parameters
            - Required keys: [list required params]
            - Optional keys: [list optional params]

    Returns:
        Task result dict with:
            - status: "success" or "error"
            - outputs: Stage-specific output data
            - metrics: Execution metrics
            - message: Human-readable status

    Raises:
        ValueError: If required params missing
        Exception: If stage execution fails
    """
    # 1. Validate parameters
    # 2. Create pipeline context
    # 3. Execute stage
    # 4. Return results
```

### Step 2: Add to Task Router

Update `src/dsa110_contimg/absurd/adapter.py`:

```python
async def execute_pipeline_task(task_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Route tasks to appropriate executors."""
    if task_name == "convert-uvh5-to-ms":
        return await execute_conversion(params)
    elif task_name == "calibration-solve":
        return await execute_calibration_solve(params)
    # ... etc
    else:
        raise ValueError(f"Unknown task: {task_name}")
```

### Step 3: Test Executor

```python
# Test via Python
from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig

config = AbsurdConfig.from_env()
async with AbsurdClient(config.database_url) as client:
    task_id = await client.spawn_task(
        queue_name=config.queue_name,
        task_name="convert-uvh5-to-ms",
        params={"uvh5_path": "/path/to/data.hdf5"}
    )
    print(f"Task spawned: {task_id}")
```

## Core Executors (Phase 3a)

### 1. Conversion Executor

**Task Name:** `convert-uvh5-to-ms`

**Implementation:**

```python
import asyncio
from pathlib import Path
from typing import Any, Dict

from dsa110_contimg.pipeline.stages_impl import ConversionStage
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.config import PipelineConfig


async def execute_conversion(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute UVH5 to MS conversion.

    Args:
        params:
            - uvh5_path: str - Path to UVH5 file (required)
            - output_dir: str - Output directory (optional)
            - config: dict - Conversion config overrides (optional)

    Returns:
        Result with ms_path, conversion_time, file_size
    """
    # Validate parameters
    if "uvh5_path" not in params:
        raise ValueError("uvh5_path required")

    uvh5_path = Path(params["uvh5_path"])
    if not uvh5_path.exists():
        raise ValueError(f"UVH5 file not found: {uvh5_path}")

    output_dir = Path(params.get("output_dir", "/stage/dsa110-contimg/raw/ms"))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load pipeline config
    pipeline_config = PipelineConfig.from_env()

    # Override config if provided
    if "config" in params:
        for key, value in params["config"].items():
            setattr(pipeline_config.conversion, key, value)

    # Create pipeline context
    context = PipelineContext(
        config=pipeline_config,
        inputs={"uvh5_path": str(uvh5_path)}
    )

    # Execute stage (in thread pool to avoid blocking)
    stage = ConversionStage()

    try:
        start_time = asyncio.get_event_loop().time()

        # Run in thread pool (CASA is not async-safe)
        result_context = await asyncio.to_thread(
            stage.execute,
            context
        )

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # Extract outputs
        ms_path = result_context.outputs.get("ms_path")

        return {
            "status": "success",
            "outputs": {
                "ms_path": ms_path,
                "uvh5_path": str(uvh5_path),
            },
            "metrics": {
                "duration_sec": duration,
                "file_size_bytes": Path(ms_path).stat().st_size if ms_path else 0,
            },
            "message": f"Converted {uvh5_path.name} → {Path(ms_path).name}"
        }

    except Exception as e:
        return {
            "status": "error",
            "outputs": {},
            "metrics": {},
            "message": f"Conversion failed: {str(e)}",
            "error": str(e)
        }
```

### 2. Calibration Solve Executor

**Task Name:** `calibration-solve`

**Implementation:**

```python
async def execute_calibration_solve(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute calibration solve.

    Args:
        params:
            - ms_path: str - Path to MS file (required)
            - calibrator: str - Calibrator name (optional)
            - refant: str - Reference antenna (optional)
            - config: dict - Calibration config overrides (optional)

    Returns:
        Result with calibration table paths
    """
    # Validate
    if "ms_path" not in params:
        raise ValueError("ms_path required")

    ms_path = Path(params["ms_path"])
    if not ms_path.exists():
        raise ValueError(f"MS not found: {ms_path}")

    # Load config
    pipeline_config = PipelineConfig.from_env()

    # Override config
    if "refant" in params:
        pipeline_config.calibration.default_refant = params["refant"]

    if "config" in params:
        for key, value in params["config"].items():
            setattr(pipeline_config.calibration, key, value)

    # Create context
    context = PipelineContext(
        config=pipeline_config,
        inputs={
            "ms_path": str(ms_path),
            "calibrator": params.get("calibrator"),
        }
    )

    # Execute stage
    stage = CalibrationSolveStage()

    try:
        start_time = asyncio.get_event_loop().time()

        result_context = await asyncio.to_thread(
            stage.execute,
            context
        )

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # Extract calibration tables
        caltables = result_context.outputs.get("caltables", {})

        return {
            "status": "success",
            "outputs": {
                "caltables": caltables,
                "ms_path": str(ms_path),
            },
            "metrics": {
                "duration_sec": duration,
                "num_tables": len(caltables),
            },
            "message": f"Solved calibration for {ms_path.name}"
        }

    except Exception as e:
        return {
            "status": "error",
            "outputs": {},
            "metrics": {},
            "message": f"Calibration solve failed: {str(e)}",
            "error": str(e)
        }
```

### 3. Calibration Apply Executor

**Task Name:** `calibration-apply`

```python
async def execute_calibration_apply(params: Dict[str, Any]) -> Dict[str, Any]:
    """Apply calibration solutions to MS.

    Args:
        params:
            - ms_path: str - Path to MS file (required)
            - caltables: dict - Calibration tables (required)
            - config: dict - Config overrides (optional)

    Returns:
        Result with calibrated MS path
    """
    if "ms_path" not in params:
        raise ValueError("ms_path required")
    if "caltables" not in params:
        raise ValueError("caltables required")

    ms_path = Path(params["ms_path"])
    caltables = params["caltables"]

    # Load config
    pipeline_config = PipelineConfig.from_env()

    # Create context
    context = PipelineContext(
        config=pipeline_config,
        inputs={
            "ms_path": str(ms_path),
            "caltables": caltables,
        }
    )

    # Execute
    stage = CalibrationStage()

    try:
        start_time = asyncio.get_event_loop().time()

        result_context = await asyncio.to_thread(
            stage.execute,
            context
        )

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        calibrated_ms = result_context.outputs.get("calibrated_ms_path")

        return {
            "status": "success",
            "outputs": {
                "calibrated_ms_path": calibrated_ms,
                "original_ms_path": str(ms_path),
            },
            "metrics": {
                "duration_sec": duration,
            },
            "message": f"Applied calibration to {ms_path.name}"
        }

    except Exception as e:
        return {
            "status": "error",
            "outputs": {},
            "metrics": {},
            "message": f"Calibration apply failed: {str(e)}",
            "error": str(e)
        }
```

### 4. Imaging Executor

**Task Name:** `imaging`

```python
async def execute_imaging(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute imaging (tclean).

    Args:
        params:
            - ms_path: str - Path to calibrated MS (required)
            - imsize: int - Image size in pixels (optional, default: 4096)
            - niter: int - Number of iterations (optional)
            - config: dict - Imaging config overrides (optional)

    Returns:
        Result with image paths
    """
    if "ms_path" not in params:
        raise ValueError("ms_path required")

    ms_path = Path(params["ms_path"])

    # Load config
    pipeline_config = PipelineConfig.from_env()

    # Override imaging params
    if "config" in params:
        for key, value in params["config"].items():
            setattr(pipeline_config.imaging, key, value)

    # Create context
    context = PipelineContext(
        config=pipeline_config,
        inputs={
            "ms_path": str(ms_path),
            "imsize": params.get("imsize", 4096),
            "niter": params.get("niter"),
        }
    )

    # Execute
    stage = ImagingStage()

    try:
        start_time = asyncio.get_event_loop().time()

        # Imaging is CPU/memory intensive, run in thread
        result_context = await asyncio.to_thread(
            stage.execute,
            context
        )

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # Extract outputs
        image_path = result_context.outputs.get("image_path")
        pbcor_path = result_context.outputs.get("pbcor_image_path")

        return {
            "status": "success",
            "outputs": {
                "image_path": image_path,
                "pbcor_image_path": pbcor_path,
                "ms_path": str(ms_path),
            },
            "metrics": {
                "duration_sec": duration,
                "image_size_mb": Path(image_path).stat().st_size / 1e6 if image_path else 0,
            },
            "message": f"Imaged {ms_path.name} → {Path(image_path).name if image_path else 'N/A'}"
        }

    except Exception as e:
        return {
            "status": "error",
            "outputs": {},
            "metrics": {},
            "message": f"Imaging failed: {str(e)}",
            "error": str(e)
        }
```

## Complete adapter.py Implementation

Update `src/dsa110_contimg/absurd/adapter.py`:

```python
"""
Pipeline adapter for Absurd task execution.

Provides task executors for all DSA-110 pipeline stages.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict

from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.stages_impl import (
    ConversionStage,
    CalibrationSolveStage,
    CalibrationStage,
    ImagingStage,
    ValidationStage,
    CrossMatchStage,
    AdaptivePhotometryStage,
    OrganizationStage,
    CatalogSetupStage,
)

logger = logging.getLogger(__name__)


async def execute_pipeline_task(task_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a pipeline task via Absurd.

    Routes task_name to appropriate executor.

    Args:
        task_name: Task type (kebab-case)
        params: Task parameters

    Returns:
        Task result dict

    Raises:
        ValueError: If task_name unknown
    """
    logger.info(f"Executing task: {task_name}")

    # Route to appropriate executor
    if task_name == "convert-uvh5-to-ms":
        return await execute_conversion(params)
    elif task_name == "calibration-solve":
        return await execute_calibration_solve(params)
    elif task_name == "calibration-apply":
        return await execute_calibration_apply(params)
    elif task_name == "imaging":
        return await execute_imaging(params)
    elif task_name == "validation":
        return await execute_validation(params)
    elif task_name == "crossmatch":
        return await execute_crossmatch(params)
    elif task_name == "photometry":
        return await execute_photometry(params)
    elif task_name == "organize-files":
        return await execute_organization(params)
    elif task_name == "catalog-setup":
        return await execute_catalog_setup(params)
    else:
        raise ValueError(f"Unknown task: {task_name}")


# Include all executor implementations here
# (execute_conversion, execute_calibration_solve, etc.)
```

## Testing

### Unit Test Example

```python
import pytest
from dsa110_contimg.absurd.adapter import execute_conversion


@pytest.mark.asyncio
async def test_conversion_executor():
    """Test conversion executor."""
    params = {
        "uvh5_path": "/path/to/test.hdf5",
        "output_dir": "/tmp/test_output"
    }

    result = await execute_conversion(params)

    assert result["status"] == "success"
    assert "ms_path" in result["outputs"]
    assert result["metrics"]["duration_sec"] > 0
```

### Integration Test

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_pipeline_via_absurd():
    """Test full pipeline via Absurd."""
    from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig

    config = AbsurdConfig.from_env()
    client = AbsurdClient(config.database_url)
    await client.connect()

    try:
        # Spawn conversion task
        task_id = await client.spawn_task(
            queue_name=config.queue_name,
            task_name="convert-uvh5-to-ms",
            params={"uvh5_path": "/path/to/test.hdf5"}
        )

        # Wait for completion
        while True:
            task = await client.get_task(task_id)
            if task["status"] in ("completed", "failed"):
                break
            await asyncio.sleep(1)

        assert task["status"] == "completed"

    finally:
        await client.close()
```

## Deployment

### 1. Update Worker Service

Create `scripts/absurd/run_worker.sh`:

```bash
#!/bin/bash
# Run Absurd worker

cd /data/dsa110-contimg
source scripts/dev/developer-setup.sh

export ABSURD_ENABLED=true
export ABSURD_DATABASE_URL="postgresql://postgres@localhost/dsa110_absurd"
export ABSURD_WORKER_CONCURRENCY=4

# Run worker
python -c "
import asyncio
from dsa110_contimg.absurd import AbsurdWorker, AbsurdConfig
from dsa110_contimg.absurd.adapter import execute_pipeline_task

config = AbsurdConfig.from_env()
worker = AbsurdWorker(config, execute_pipeline_task)
asyncio.run(worker.start())
"
```

### 2. Create Systemd Service

Create `/etc/systemd/system/absurd-worker.service`:

```ini
[Unit]
Description=Absurd Pipeline Worker
After=network.target postgresql.service

[Service]
Type=simple
User=dsa110
WorkingDirectory=/data/dsa110-contimg
Environment="ABSURD_ENABLED=true"
Environment="ABSURD_DATABASE_URL=postgresql://postgres@localhost/dsa110_absurd"
Environment="ABSURD_WORKER_CONCURRENCY=4"
ExecStart=/data/dsa110-contimg/scripts/absurd/run_worker.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable absurd-worker
sudo systemctl start absurd-worker
sudo systemctl status absurd-worker
```

## Monitoring

### Check Worker Status

```bash
# Check systemd service
sudo systemctl status absurd-worker

# Check logs
sudo journalctl -u absurd-worker -f

# Check queue stats
curl http://localhost:8000/absurd/queues/dsa110-pipeline/stats
```

### Monitor Task Execution

```python
# Python monitoring script
from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig

config = AbsurdConfig.from_env()
async with AbsurdClient(config.database_url) as client:
    # Get recent tasks
    tasks = await client.list_tasks(
        queue_name=config.queue_name,
        limit=100
    )

    # Print stats
    total = len(tasks)
    completed = sum(1 for t in tasks if t["status"] == "completed")
    failed = sum(1 for t in tasks if t["status"] == "failed")

    print(f"Total: {total}, Completed: {completed}, Failed: {failed}")
```

## Next Steps

1. **Implement Core Executors** (Phase 3a)
2. **Test Each Executor** individually
3. **Deploy Worker** to staging
4. **Run Integration Tests**
5. **Implement Remaining Executors** (Phase 3b/3c)
6. **Production Deployment**

---

**See Also:**

- Task Mapping: `docs/concepts/absurd_task_executor_mapping.md`
- Quick Start: `docs/how-to/absurd_quick_start.md`
- Phase 2 Status: `docs/dev/status/2025-11/absurd_phase2_complete.md`
