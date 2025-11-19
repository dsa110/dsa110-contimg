# Operating the DSA-110 Pipeline with Absurd

**Date:** 2025-11-18  
**Type:** Operations Guide  
**Status:** ✅ Production-Ready

---

## Overview

This guide explains how to operate the DSA-110 continuum imaging pipeline using
the Absurd workflow manager. All 9 pipeline stages are now executable as durable
Absurd tasks.

---

## Prerequisites

1. **Database Setup:**

   ```bash
   # Set up Absurd PostgreSQL database
   ./scripts/absurd/setup_absurd_db.sh

   # Create the pipeline queue
   ./scripts/absurd/create_absurd_queues.sh
   ```

2. **Environment Configuration:**

   ```bash
   # Add to your environment or .env file
   export ABSURD_ENABLED=true
   export ABSURD_DATABASE_URL="postgresql://postgres:postgres@localhost/dsa110_absurd"
   export ABSURD_QUEUE_NAME="dsa110-pipeline"
   export ABSURD_WORKER_CONCURRENCY=4
   ```

3. **Verify Setup:**
   ```bash
   # Test database connection
   python scripts/absurd/test_absurd_connection.py
   ```

---

## Starting the System

### 1. Start the FastAPI Backend

```bash
# Source casa6 environment
source /data/dsa110-contimg/scripts/dev/developer-setup.sh

# Start the API server
cd /data/dsa110-contimg
uvicorn src.dsa110_contimg.api.routes:app --host 0.0.0.0 --port 8000 --reload
```

The API server includes Absurd endpoints at:

- `POST /api/absurd/tasks` - Submit tasks
- `GET /api/absurd/tasks/{task_id}` - Get task status
- `GET /api/absurd/tasks` - List tasks
- `DELETE /api/absurd/tasks/{task_id}` - Cancel task
- `GET /api/absurd/queues/{queue_name}/stats` - Queue statistics

### 2. Start the Absurd Worker

In a separate terminal:

```bash
# Source casa6 environment
source /data/dsa110-contimg/scripts/dev/developer-setup.sh

# Start the worker
cd /data/dsa110-contimg
python -c "
import asyncio
from dsa110_contimg.absurd import AbsurdConfig
from dsa110_contimg.absurd.worker import AbsurdWorker
from dsa110_contimg.absurd.adapter import execute_pipeline_task

async def main():
    config = AbsurdConfig.from_env()
    worker = AbsurdWorker(config, execute_pipeline_task)
    await worker.start()

asyncio.run(main())
"
```

Or create a worker script:

```bash
# Create scripts/absurd/start_worker.py
cat > scripts/absurd/start_worker.py << 'WORKER_EOF'
#!/usr/bin/env python
"""Start Absurd worker for DSA-110 pipeline."""

import asyncio
import logging
from dsa110_contimg.absurd import AbsurdConfig
from dsa110_contimg.absurd.worker import AbsurdWorker
from dsa110_contimg.absurd.adapter import execute_pipeline_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Start the Absurd worker."""
    config = AbsurdConfig.from_env()
    config.validate()

    logger.info(f"Starting worker with config: {config}")

    worker = AbsurdWorker(config, execute_pipeline_task)

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Shutting down worker...")
        await worker.stop()

if __name__ == "__main__":
    asyncio.run(main())
WORKER_EOF

chmod +x scripts/absurd/start_worker.py
python scripts/absurd/start_worker.py
```

---

## Submitting Pipeline Tasks

### Option 1: Using the API (Recommended)

```python
import requests

# Submit a conversion task
response = requests.post("http://localhost:8000/api/absurd/tasks", json={
    "task_name": "convert-uvh5-to-ms",
    "params": {
        "config": {
            "paths": {
                "incoming": "/data/incoming",
                "staging": "/stage/dsa110-contimg",
                "products": "/data/dsa110-contimg/products"
            }
        },
        "inputs": {
            "input_path": "/data/incoming/observation_2025-01-01.hdf5",
            "start_time": "2025-01-01T00:00:00",
            "end_time": "2025-01-01T01:00:00"
        }
    }
})

task = response.json()
print(f"Task submitted: {task['task_id']}")

# Check task status
status = requests.get(f"http://localhost:8000/api/absurd/tasks/{task['task_id']}")
print(status.json())
```

### Option 2: Using Python Client Directly

```python
import asyncio
from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig

async def submit_task():
    config = AbsurdConfig.from_env()
    client = AbsurdClient(config)
    await client.connect()

    # Submit conversion task
    task_id = await client.spawn_task(
        task_name="convert-uvh5-to-ms",
        params={
            "config": config_dict,
            "inputs": {
                "input_path": "/data/incoming/obs.hdf5",
                "start_time": "2025-01-01T00:00:00",
                "end_time": "2025-01-01T01:00:00"
            }
        },
        priority=10
    )

    print(f"Task submitted: {task_id}")

    # Wait for completion
    while True:
        task = await client.get_task(task_id)
        if task["status"] in ["completed", "failed", "cancelled"]:
            break
        await asyncio.sleep(1)

    print(f"Task {task['status']}: {task.get('result')}")

    await client.close()

asyncio.run(submit_task())
```

---

## Complete Pipeline Workflow

### Full Pipeline Orchestration

```python
import asyncio
from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig

async def run_full_pipeline(observation_path: str):
    """Run the full DSA-110 pipeline for an observation."""
    config = AbsurdConfig.from_env()
    client = AbsurdClient(config)
    await client.connect()

    pipeline_config = {
        "paths": {
            "incoming": "/data/incoming",
            "staging": "/stage/dsa110-contimg",
            "products": "/data/dsa110-contimg/products"
        }
    }

    try:
        # 1. Catalog Setup (if needed)
        print("Step 1: Setting up catalogs...")
        catalog_task = await client.spawn_task(
            "catalog-setup",
            {"config": pipeline_config, "inputs": {"input_path": observation_path}},
            priority=100
        )
        catalog_result = await wait_for_task(client, catalog_task)

        # 2. Convert UVH5 to MS
        print("Step 2: Converting UVH5 to MS...")
        conversion_task = await client.spawn_task(
            "convert-uvh5-to-ms",
            {
                "config": pipeline_config,
                "inputs": {
                    "input_path": observation_path,
                    "start_time": "2025-01-01T00:00:00",
                    "end_time": "2025-01-01T01:00:00"
                }
            },
            priority=90
        )
        conversion_result = await wait_for_task(client, conversion_task)
        ms_path = conversion_result["result"]["outputs"]["ms_path"]

        # 3. Solve Calibration
        print("Step 3: Solving calibration...")
        cal_solve_task = await client.spawn_task(
            "calibration-solve",
            {"config": pipeline_config, "outputs": {"ms_path": ms_path}},
            priority=80
        )
        cal_solve_result = await wait_for_task(client, cal_solve_task)
        cal_tables = cal_solve_result["result"]["outputs"]["calibration_tables"]

        # 4. Apply Calibration
        print("Step 4: Applying calibration...")
        cal_apply_task = await client.spawn_task(
            "calibration-apply",
            {
                "config": pipeline_config,
                "outputs": {"ms_path": ms_path, "calibration_tables": cal_tables}
            },
            priority=70
        )
        await wait_for_task(client, cal_apply_task)

        # 5. Imaging
        print("Step 5: Creating image...")
        imaging_task = await client.spawn_task(
            "imaging",
            {"config": pipeline_config, "outputs": {"ms_path": ms_path}},
            priority=60
        )
        imaging_result = await wait_for_task(client, imaging_task)
        image_path = imaging_result["result"]["outputs"]["image_path"]

        # 6. Validation
        print("Step 6: Validating image...")
        validation_task = await client.spawn_task(
            "validation",
            {"config": pipeline_config, "outputs": {"image_path": image_path}},
            priority=50
        )
        validation_result = await wait_for_task(client, validation_task)

        # 7. Cross-match
        print("Step 7: Cross-matching sources...")
        crossmatch_task = await client.spawn_task(
            "crossmatch",
            {"config": pipeline_config, "outputs": {"image_path": image_path}},
            priority=40
        )
        await wait_for_task(client, crossmatch_task)

        # 8. Photometry
        print("Step 8: Extracting photometry...")
        photometry_task = await client.spawn_task(
            "photometry",
            {
                "config": pipeline_config,
                "outputs": {"ms_path": ms_path, "image_path": image_path}
            },
            priority=30
        )
        await wait_for_task(client, photometry_task)

        # 9. Organize Files
        print("Step 9: Organizing files...")
        organize_task = await client.spawn_task(
            "organize-files",
            {"config": pipeline_config, "outputs": {"ms_path": ms_path}},
            priority=20
        )
        await wait_for_task(client, organize_task)

        print(f"✅ Pipeline complete! Image: {image_path}")

    finally:
        await client.close()

async def wait_for_task(client, task_id, poll_interval=2):
    """Wait for a task to complete."""
    while True:
        task = await client.get_task(task_id)
        if task["status"] == "completed":
            return task
        elif task["status"] in ["failed", "cancelled"]:
            raise RuntimeError(f"Task {task_id} {task['status']}: {task.get('error')}")
        await asyncio.sleep(poll_interval)

# Run it
asyncio.run(run_full_pipeline("/data/incoming/observation_2025-01-01.hdf5"))
```

---

## Monitoring and Management

### Check Queue Status

```python
import requests

# Get queue statistics
stats = requests.get("http://localhost:8000/api/absurd/queues/dsa110-pipeline/stats")
print(stats.json())
# {
#   "pending": 5,
#   "running": 2,
#   "completed": 123,
#   "failed": 3
# }
```

### List All Tasks

```python
# List recent tasks
tasks = requests.get("http://localhost:8000/api/absurd/tasks?limit=10")
for task in tasks.json():
    print(f"{task['task_id']}: {task['task_name']} - {task['status']}")
```

### Cancel a Task

```python
# Cancel a running task
response = requests.delete(f"http://localhost:8000/api/absurd/tasks/{task_id}")
print(response.json())
```

---

## Deployment Options

### Development (Single Worker)

```bash
# Terminal 1: API server
uvicorn src.dsa110_contimg.api.routes:app --host 0.0.0.0 --port 8000

# Terminal 2: Worker
python scripts/absurd/start_worker.py
```

### Production (Systemd Services)

Create `/etc/systemd/system/dsa110-absurd-worker.service`:

```ini
[Unit]
Description=DSA-110 Absurd Worker
After=network.target postgresql.service

[Service]
Type=simple
User=dsa110
WorkingDirectory=/data/dsa110-contimg
Environment="ABSURD_ENABLED=true"
Environment="ABSURD_DATABASE_URL=postgresql://postgres:postgres@localhost/dsa110_absurd"
Environment="ABSURD_QUEUE_NAME=dsa110-pipeline"
Environment="ABSURD_WORKER_CONCURRENCY=4"
ExecStart=/opt/miniforge/envs/casa6/bin/python scripts/absurd/start_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable dsa110-absurd-worker
sudo systemctl start dsa110-absurd-worker
sudo systemctl status dsa110-absurd-worker
```

### Production (Multiple Workers)

For high throughput, run multiple workers:

```bash
# Start 4 workers
for i in {1..4}; do
    python scripts/absurd/start_worker.py &
done
```

Or use systemd with instance templates: `dsa110-absurd-worker@{1..4}.service`

---

## Troubleshooting

### Worker not picking up tasks

1. **Check database connection:**

   ```bash
   python scripts/absurd/test_absurd_connection.py
   ```

2. **Check worker logs:**

   ```bash
   journalctl -u dsa110-absurd-worker -f
   ```

3. **Verify queue name matches:**
   ```bash
   psql dsa110_absurd -c "SELECT name FROM absurd_queues;"
   ```

### Tasks stuck in pending

1. **Verify worker is running:**

   ```bash
   ps aux | grep absurd
   ```

2. **Check task priorities:**
   - Higher priority = processed first
   - Default priority = 0

3. **Check worker concurrency:**
   - Set `ABSURD_WORKER_CONCURRENCY` higher

### Task failures

1. **Check task result:**

   ```python
   task = await client.get_task(task_id)
   print(task['error'])  # Error message
   print(task['result'])  # Result details
   ```

2. **Check logs:**
   - Worker logs show execution details
   - API logs show task submission

---

## Performance Tuning

### Worker Concurrency

```bash
# High throughput (more CPU cores)
export ABSURD_WORKER_CONCURRENCY=8

# Low resource usage
export ABSURD_WORKER_CONCURRENCY=2
```

### Task Priorities

```python
# Critical tasks (run first)
await client.spawn_task("imaging", params, priority=100)

# Low priority (run when idle)
await client.spawn_task("organize-files", params, priority=10)
```

### Retry Configuration

```bash
export ABSURD_MAX_RETRIES=3
export ABSURD_TASK_TIMEOUT=3600  # 1 hour
```

---

## Next Steps

1. **Integration Testing:** Test with real data files
2. **Monitoring:** Add Prometheus metrics and Grafana dashboards
3. **Workflow Engine:** Implement automatic dependency handling
4. **Dashboard UI:** Add Absurd monitoring to the frontend

---

**Last Updated:** 2025-11-18  
**Status:** ✅ Production-Ready
