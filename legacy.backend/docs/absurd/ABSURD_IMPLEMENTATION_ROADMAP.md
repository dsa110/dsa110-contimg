# Absurd Implementation Roadmap

## Overview

This document outlines the step-by-step implementation plan for integrating
Absurd into the DSA-110 continuum imaging pipeline. The approach is incremental,
starting with a minimal proof of concept and gradually expanding.

## Prerequisites

- PostgreSQL database (can be same or separate from existing databases)
- Python 3.11+ (already required for CASA6)
- Access to `/home/ubuntu/proj/absurd/` directory

## Phase 1: Foundation Setup (Week 1)

### Step 1.1: Install Absurd Schema

**Goal**: Set up Absurd database schema

**Actions**:

```bash
# 1. Ensure PostgreSQL is running and accessible
psql --version

# 2. Create database for Absurd (or use existing)
createdb dsa110_absurd
# OR if using existing database:
# psql -d your_existing_db

# 3. Install Absurd schema
cd /home/ubuntu/proj/absurd
psql -d dsa110_absurd -f sql/absurd.sql

# 4. Verify installation
psql -d dsa110_absurd -c "SELECT * FROM absurd.queues;"
```

**Verification**:

- Schema `absurd` exists
- Tables created: `queues`, `t_*`, `r_*`, `c_*`, `e_*`, `w_*`
- Functions available: `spawn_task`, `claim_task`, etc.

**Files to create**:

- `scripts/setup_absurd_db.sh` - Setup script for database initialization

### Step 1.2: Create Queue

**Goal**: Create the main pipeline queue

**Actions**:

```bash
# Using absurdctl (if available)
cd /home/ubuntu/proj/absurd
./absurdctl create-queue -d dsa110_absurd dsa110-pipeline

# OR using SQL directly
psql -d dsa110_absurd -c "SELECT absurd.create_queue('dsa110-pipeline');"
```

**Verification**:

```sql
SELECT * FROM absurd.queues WHERE queue_name = 'dsa110-pipeline';
```

**Files to create**:

- `scripts/create_absurd_queues.sh` - Queue creation script

### Step 1.3: Create Python SDK Wrapper

**Goal**: Create a simple Python client for Absurd (since no official Python SDK
exists)

**Actions**: Create `dsa110_contimg/absurd/client.py`:

```python
"""Simple Absurd client for Python."""
import json
import logging
from typing import Any, Dict, Optional
import asyncpg

logger = logging.getLogger(__name__)


class AbsurdClient:
    """Client for interacting with Absurd durable execution system."""

    def __init__(self, database_url: str):
        """Initialize Absurd client.

        Args:
            database_url: PostgreSQL connection string
                Example: "postgresql://user:pass@localhost/dsa110_absurd"
        """
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool."""
        self.pool = await asyncpg.create_pool(self.database_url)
        logger.info("Connected to Absurd database")

    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()

    async def spawn_task(
        self,
        queue_name: str,
        task_name: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None
    ) -> str:
        """Spawn a new task in Absurd queue.

        Returns:
            Task ID (UUID as string)
        """
        async with self.pool.acquire() as conn:
            task_id = await conn.fetchval(
                "SELECT absurd.spawn_task($1, $2, $3::jsonb, $4::jsonb)",
                queue_name,
                task_name,
                json.dumps(params),
                json.dumps(headers or {})
            )
            logger.info(f"Spawned task {task_id} in queue {queue_name}")
            return str(task_id)

    async def get_task(self, queue_name: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM absurd.t_{queue_name} WHERE task_id = $1",
                task_id
            )
            if row:
                return dict(row)
            return None
```

**Files to create**:

- `dsa110_contimg/absurd/__init__.py`
- `dsa110_contimg/absurd/client.py`
- `dsa110_contimg/absurd/config.py` - Configuration management

**Dependencies to add**:

```bash
# Add to requirements or setup.py
asyncpg>=0.29.0  # For async PostgreSQL access
```

### Step 1.4: Add Configuration

**Goal**: Add Absurd configuration to pipeline config

**Actions**: Update `dsa110_contimg/pipeline/config.py`:

```python
class PipelineConfig(BaseModel):
    # ... existing fields ...

    # Absurd configuration
    absurd_enabled: bool = Field(
        default=False,
        description="Enable Absurd durable execution"
    )
    absurd_database_url: Optional[str] = Field(
        default=None,
        description="PostgreSQL connection URL for Absurd"
    )
    absurd_queue_name: str = Field(
        default="dsa110-pipeline",
        description="Default Absurd queue name"
    )

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        # ... existing code ...

        # Add Absurd config from environment
        absurd_enabled = os.getenv("ABSURD_ENABLED", "false").lower() == "true"
        absurd_database_url = os.getenv("ABSURD_DATABASE_URL")
        absurd_queue_name = os.getenv("ABSURD_QUEUE_NAME", "dsa110-pipeline")

        return cls(
            # ... existing fields ...
            absurd_enabled=absurd_enabled,
            absurd_database_url=absurd_database_url,
            absurd_queue_name=absurd_queue_name,
        )
```

**Environment variables**:

```bash
# .env or environment
ABSURD_ENABLED=true
ABSURD_DATABASE_URL=postgresql://user:pass@localhost/dsa110_absurd
ABSURD_QUEUE_NAME=dsa110-pipeline
```

## Phase 2: Proof of Concept (Week 1-2)

### Step 2.1: Create Simple Test Task

**Goal**: Verify Absurd integration works end-to-end

**Actions**: Create `scripts/test_absurd_integration.py`:

```python
#!/usr/bin/env python3
"""Test script to verify Absurd integration."""
import asyncio
import os
from dsa110_contimg.absurd.client import AbsurdClient

async def main():
    database_url = os.getenv(
        "ABSURD_DATABASE_URL",
        "postgresql://postgres:postgres@localhost/dsa110_absurd"
    )

    client = AbsurdClient(database_url)
    await client.connect()

    try:
        # Spawn a test task
        task_id = await client.spawn_task(
            queue_name="dsa110-pipeline",
            task_name="test-task",
            params={"message": "Hello from Absurd!"}
        )

        print(f":check_mark: Spawned task: {task_id}")

        # Get task details
        task = await client.get_task("dsa110-pipeline", task_id)
        print(f":check_mark: Task status: {task['state']}")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

**Run test**:

```bash
cd /data/dsa110-contimg/src
python scripts/test_absurd_integration.py
```

**Verification**:

- Task spawns successfully
- Task appears in database
- Can query task status

### Step 2.2: Create Minimal Worker

**Goal**: Create a simple worker that can execute tasks

**Actions**: Create `dsa110_contimg/absurd/worker.py`:

```python
"""Simple Absurd worker for executing tasks."""
import asyncio
import json
import logging
from typing import Optional
from dsa110_contimg.absurd.client import AbsurdClient

logger = logging.getLogger(__name__)


class AbsurdWorker:
    """Worker that pulls and executes Absurd tasks."""

    def __init__(self, client: AbsurdClient, queue_name: str, worker_id: str = None):
        self.client = client
        self.queue_name = queue_name
        self.worker_id = worker_id or f"worker-{os.getpid()}"
        self.running = False

    async def start(self, poll_interval: float = 5.0):
        """Start worker loop."""
        self.running = True
        logger.info(f"Worker {self.worker_id} started")

        while self.running:
            try:
                # Claim a task
                task = await self._claim_task()

                if task:
                    logger.info(f"Claimed task {task['task_id']}")
                    await self._execute_task(task)
                else:
                    await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                await asyncio.sleep(poll_interval)

    async def _claim_task(self) -> Optional[Dict]:
        """Claim a task from the queue."""
        async with self.client.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM absurd.claim_task($1, $2, $3)",
                self.queue_name,
                self.worker_id,
                300  # 5 minute lease
            )
            if row:
                return dict(row)
            return None

    async def _execute_task(self, task: Dict):
        """Execute a task."""
        task_id = task['task_id']
        run_id = task['run_id']
        params = json.loads(task['params'])

        try:
            # Execute task logic here
            logger.info(f"Executing task {task_id} with params: {params}")

            # For now, just mark as completed
            await self._complete_run(run_id, {"status": "completed"})

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            await self._fail_run(run_id, str(e), retry=True)

    async def _complete_run(self, run_id: str, result: Dict):
        """Mark run as completed."""
        async with self.client.pool.acquire() as conn:
            await conn.execute(
                "SELECT absurd.complete_run($1, $2, $3::jsonb)",
                self.queue_name,
                run_id,
                json.dumps(result)
            )

    async def _fail_run(self, run_id: str, reason: str, retry: bool = True):
        """Mark run as failed."""
        async with self.client.pool.acquire() as conn:
            await conn.execute(
                "SELECT absurd.fail_run($1, $2, $3, $4)",
                self.queue_name,
                run_id,
                reason,
                retry
            )

    def stop(self):
        """Stop worker."""
        self.running = False
```

**Test worker**:

```python
# scripts/test_absurd_worker.py
import asyncio
from dsa110_contimg.absurd.client import AbsurdClient
from dsa110_contimg.absurd.worker import AbsurdWorker

async def main():
    client = AbsurdClient("postgresql://localhost/dsa110_absurd")
    await client.connect()

    worker = AbsurdWorker(client, "dsa110-pipeline")

    # Run for 30 seconds
    try:
        await asyncio.wait_for(worker.start(), timeout=30.0)
    except asyncio.TimeoutError:
        worker.stop()
        print("Worker stopped")

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 2.3: Integrate with Simple Pipeline Stage

**Goal**: Wrap one pipeline stage as Absurd task

**Actions**: Create `dsa110_contimg/pipeline/absurd_adapter.py`:

```python
"""Adapter to run pipeline stages as Absurd tasks."""
from typing import Dict, Any
from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.absurd.client import AbsurdClient

class AbsurdPipelineAdapter:
    """Adapter to run pipeline stages as Absurd tasks."""

    def __init__(self, config: PipelineConfig, absurd_client: AbsurdClient):
        self.config = config
        self.absurd = absurd_client

    async def spawn_pipeline_task(self, params: Dict[str, Any]) -> str:
        """Spawn a pipeline task in Absurd."""
        return await self.absurd.spawn_task(
            queue_name=self.config.absurd_queue_name,
            task_name="dsa110-pipeline",
            params=params
        )
```

Update worker to execute actual pipeline stages:

```python
# In worker.py, update _execute_task
async def _execute_task(self, task: Dict):
    """Execute a task."""
    task_id = task['task_id']
    run_id = task['run_id']
    params = json.loads(task['params'])

    try:
        # Import pipeline components
        from dsa110_contimg.pipeline.config import PipelineConfig
        from dsa110_contimg.pipeline.context import PipelineContext
        from dsa110_contimg.pipeline.workflows import standard_imaging_workflow

        # Create config and context
        config = PipelineConfig.from_env()
        context = PipelineContext(config=config, inputs=params)

        # Execute pipeline
        orchestrator = standard_imaging_workflow(config)
        result = orchestrator.execute(context)

        # Save checkpoint
        await self._set_checkpoint(task_id, "pipeline_complete", {
            "status": result.status.value,
            "outputs": result.context.outputs
        })

        # Complete run
        await self._complete_run(run_id, {
            "status": "completed",
            "result": result.context.outputs
        })

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        await self._fail_run(run_id, str(e), retry=True)
```

## Phase 3: API Integration (Week 2)

### Step 3.1: Add Absurd API Endpoints

**Goal**: Expose Absurd functionality via REST API

**Actions**: Create `dsa110_contimg/api/routers/absurd.py`:

```python
"""Absurd API endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
from dsa110_contimg.absurd.client import AbsurdClient
from dsa110_contimg.pipeline.config import PipelineConfig

router = APIRouter(prefix="/absurd", tags=["absurd"])


class SpawnTaskRequest(BaseModel):
    task_name: str
    params: Dict[str, Any]
    queue_name: Optional[str] = None


@router.post("/tasks/spawn")
async def spawn_task(
    request: SpawnTaskRequest,
    config: PipelineConfig = Depends(get_config)
):
    """Spawn a new Absurd task."""
    if not config.absurd_enabled:
        raise HTTPException(400, "Absurd is not enabled")

    client = AbsurdClient(config.absurd_database_url)
    await client.connect()

    try:
        task_id = await client.spawn_task(
            queue_name=request.queue_name or config.absurd_queue_name,
            task_name=request.task_name,
            params=request.params
        )
        return {"task_id": task_id}
    finally:
        await client.close()


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    config: PipelineConfig = Depends(get_config)
):
    """Get task details."""
    client = AbsurdClient(config.absurd_database_url)
    await client.connect()

    try:
        task = await client.get_task(config.absurd_queue_name, task_id)
        if not task:
            raise HTTPException(404, "Task not found")
        return task
    finally:
        await client.close()
```

Register router in main API:

```python
# In dsa110_contimg/api/__init__.py or main.py
from dsa110_contimg.api.routers import absurd
app.include_router(absurd.router)
```

### Step 3.2: Update Frontend API Client

**Goal**: Add Absurd API calls to frontend

**Actions**: Add to `frontend/src/api/absurd.ts` (create new file):

```typescript
import { apiClient } from "./client";

export interface AbsurdTask {
  taskId: string;
  status: string;
  // ... other fields
}

export const absurdApi = {
  spawnTask: async (taskName: string, params: any) => {
    const response = await apiClient.post("/absurd/tasks/spawn", {
      task_name: taskName,
      params,
    });
    return response.data;
  },

  getTask: async (taskId: string) => {
    const response = await apiClient.get(`/absurd/tasks/${taskId}`);
    return response.data;
  },
};
```

## Phase 4: UI Integration (Week 2-3)

### Step 4.1: Add Toggle to Workflow Forms

**Goal**: Add "Use Durable Execution" option to existing workflows

**Actions**: Update `frontend/src/components/workflows/ConversionWorkflow.tsx`:

```typescript
const [useDurableExecution, setUseDurableExecution] = useState(false);

// In form:
<FormControlLabel
  control={
    <Switch
      checked={useDurableExecution}
      onChange={(e) => setUseDurableExecution(e.target.checked)}
    />
  }
  label="Use Durable Execution"
/>

// In submit handler:
if (useDurableExecution) {
  const result = await absurdApi.spawnTask('dsa110-pipeline', convertParams);
  showSuccess(`Durable workflow started: ${result.task_id}`);
} else {
  // Existing workflow creation
  convertMutation.mutate(...);
}
```

### Step 4.2: Create Workflows Page

**Goal**: Create page to view Absurd workflows

**Actions**: Create `frontend/src/pages/AbsurdWorkflowsPage.tsx` (see
`ABSURD_USER_INTERACTION_GUIDE.md` for full implementation)

## Phase 5: Advanced Features (Week 3-4)

### Step 5.1: Implement Checkpointing

**Goal**: Add checkpoint support to pipeline stages

**Actions**:

- Update worker to save checkpoints after each stage
- Add checkpoint loading on resume
- Update UI to show checkpoint timeline

### Step 5.2: Add Retry Policies

**Goal**: Configure retry strategies

**Actions**:

- Add retry policy configuration
- Implement exponential backoff
- Add max attempts limits

### Step 5.3: Integrate Habitat UI

**Goal**: Add Habitat monitoring UI

**Actions**:

- Run Habitat backend service
- Integrate Habitat API endpoints
- Add Habitat UI components to dashboard

## Testing Strategy

### Unit Tests

- Test Absurd client functions
- Test worker task execution
- Test checkpoint save/load

### Integration Tests

- Test end-to-end workflow execution
- Test failure and retry scenarios
- Test checkpoint recovery

### Manual Testing

- Start workflow via UI
- Monitor in workflows page
- Simulate failure and verify retry
- Verify checkpoint recovery

## Rollout Plan

1. **Week 1**: Foundation + Proof of Concept
   - Set up database and schema
   - Create Python client
   - Test basic task spawning

2. **Week 2**: Basic Integration
   - Integrate with one pipeline stage
   - Add API endpoints
   - Create simple worker

3. **Week 3**: UI Integration
   - Add toggle to workflow forms
   - Create workflows page
   - Add monitoring

4. **Week 4**: Polish & Production
   - Add checkpointing
   - Add retry policies
   - Full testing
   - Documentation

## Success Criteria

- [ ] Can spawn pipeline tasks via API
- [ ] Worker can execute tasks
- [ ] Tasks survive crashes and resume
- [ ] UI shows workflow status
- [ ] Checkpoints work correctly
- [ ] Retries work as expected

## Next Steps

1. **Start with Step 1.1**: Install Absurd schema
2. **Complete Phase 1**: Foundation setup
3. **Test Phase 2**: Proof of concept
4. **Iterate**: Add features incrementally

## Files to Create

```
dsa110_contimg/
├── absurd/
│   ├── __init__.py
│   ├── client.py          # Absurd client
│   ├── worker.py          # Worker implementation
│   ├── adapter.py         # Pipeline adapter
│   └── config.py          # Configuration
├── api/
│   └── routers/
│       └── absurd.py      # API endpoints
scripts/
├── setup_absurd_db.sh     # Database setup
├── create_absurd_queues.sh # Queue creation
└── test_absurd_integration.py # Test script
frontend/src/
├── api/
│   └── absurd.ts          # Frontend API client
└── pages/
    └── AbsurdWorkflowsPage.tsx # Workflows page
```

## Dependencies

Add to `requirements.txt` or `setup.py`:

```
asyncpg>=0.29.0  # For async PostgreSQL access
```

## Environment Variables

```bash
# Enable Absurd
ABSURD_ENABLED=true

# Database connection
ABSURD_DATABASE_URL=postgresql://user:pass@localhost/dsa110_absurd

# Queue name
ABSURD_QUEUE_NAME=dsa110-pipeline
```

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running
- Check connection string format
- Verify database exists and schema is installed

### Task Not Executing

- Check worker is running
- Verify queue exists
- Check task status in database

### Checkpoint Issues

- Verify checkpoint data is JSON serializable
- Check checkpoint table exists
- Verify checkpoint names are consistent
