# ABSURD Workflow Manager Deployment Plan

**Date:** 2025-12-01  
**Status:** Planning  
**Target:** Deploy durable workflow manager to `frontend/` and `backend/`

---

## Overview

ABSURD is a PostgreSQL-backed durable workflow/task queue manager that provides:

| Feature             | Description                               |
| ------------------- | ----------------------------------------- |
| **Fault Tolerance** | Tasks survive worker crashes and restarts |
| **Durability**      | Task state persisted in PostgreSQL        |
| **Retries**         | Automatic retry with configurable limits  |
| **Scheduling**      | Cron-based scheduled task execution       |
| **Workflow DAGs**   | Task dependency graphs and orchestration  |
| **Observability**   | Prometheus metrics, historical tracking   |

### Architecture

```
┌─────────────────┐
│  Frontend UI    │ ← Workflows dashboard, task management
│  (React + TS)   │
└────────┬────────┘
         │ HTTP/REST
         ↓
┌─────────────────┐
│   FastAPI App   │ ← Router: /absurd/* endpoints
│  (Python async) │
└────────┬────────┘
         │ AbsurdClient (asyncpg)
         ↓
┌─────────────────┐
│  PostgreSQL DB  │ ← absurd schema with tasks table
│  (dsa110_absurd)│
└────────┬────────┘
         ↑ Claims/executes tasks
┌─────────────────┐
│  Absurd Worker  │ ← Processes pipeline stages
└─────────────────┘
```

### Current State Assessment

| Component        | Location                                                  | Status                       |
| ---------------- | --------------------------------------------------------- | ---------------------------- |
| Backend module   | `legacy.backend/src/dsa110_contimg/absurd/`               | ✅ Complete, needs migration |
| FastAPI router   | `legacy.backend/src/dsa110_contimg/api/routers/absurd.py` | ✅ Complete, needs migration |
| Frontend client  | Does not exist                                            | ❌ Needs creation            |
| Error handling   | `frontend/src/constants/errorMappings.ts`                 | ✅ `ABSURD_DISABLED` exists  |
| Database schema  | `legacy.backend/src/dsa110_contimg/absurd/schema.sql`     | ✅ Complete                  |
| Systemd services | Does not exist                                            | ❌ Needs creation            |

---

## Phase 1: Backend Infrastructure

### 1.1 Migrate Core Modules from Legacy

**Source:** `legacy.backend/src/dsa110_contimg/absurd/`  
**Target:** `backend/src/dsa110_contimg/absurd/`

#### Files to Copy (in order of dependency)

| File              | Size | Purpose                  | Dependencies                |
| ----------------- | ---- | ------------------------ | --------------------------- |
| `config.py`       | 4KB  | Configuration dataclass  | None                        |
| `schema.sql`      | 9KB  | PostgreSQL schema        | None                        |
| `client.py`       | 14KB | Async PostgreSQL client  | `config.py`                 |
| `worker.py`       | 8KB  | Task executor harness    | `client.py`, `config.py`    |
| `scheduling.py`   | 18KB | Cron scheduling          | `client.py`                 |
| `dependencies.py` | 22KB | Workflow DAG management  | `client.py`                 |
| `monitoring.py`   | 38KB | Prometheus metrics       | `client.py`                 |
| `adapter.py`      | 56KB | Pipeline stage executors | All above + pipeline stages |
| `__init__.py`     | 2KB  | Package exports          | All above                   |

#### Step-by-Step Migration Commands

```bash
# 1. Create target directory
mkdir -p /data/dsa110-contimg/backend/src/dsa110_contimg/absurd

# 2. Copy files preserving structure
cd /data/dsa110-contimg
cp legacy.backend/src/dsa110_contimg/absurd/config.py \
   backend/src/dsa110_contimg/absurd/
cp legacy.backend/src/dsa110_contimg/absurd/schema.sql \
   backend/src/dsa110_contimg/absurd/
cp legacy.backend/src/dsa110_contimg/absurd/client.py \
   backend/src/dsa110_contimg/absurd/
cp legacy.backend/src/dsa110_contimg/absurd/worker.py \
   backend/src/dsa110_contimg/absurd/
cp legacy.backend/src/dsa110_contimg/absurd/scheduling.py \
   backend/src/dsa110_contimg/absurd/
cp legacy.backend/src/dsa110_contimg/absurd/dependencies.py \
   backend/src/dsa110_contimg/absurd/
cp legacy.backend/src/dsa110_contimg/absurd/monitoring.py \
   backend/src/dsa110_contimg/absurd/
cp legacy.backend/src/dsa110_contimg/absurd/adapter.py \
   backend/src/dsa110_contimg/absurd/
cp legacy.backend/src/dsa110_contimg/absurd/__init__.py \
   backend/src/dsa110_contimg/absurd/

# 3. Copy FastAPI router
cp legacy.backend/src/dsa110_contimg/api/routers/absurd.py \
   backend/src/dsa110_contimg/api/routers/
```

#### `__init__.py` Package Exports Reference

The migrated `__init__.py` should export these components:

```python
# Core client and worker
from .client import AbsurdClient
from .config import AbsurdConfig
from .worker import AbsurdWorker, set_websocket_manager

# Task chains (predefined workflows)
from .adapter import (
    STANDARD_PIPELINE_CHAIN,    # Full: conversion → calibration → imaging
    QUICK_IMAGING_CHAIN,        # Fast: conversion → imaging (skip cal)
    CALIBRATOR_CHAIN,           # Cal source: conversion → calibration-solve
    TARGET_CHAIN,               # Target: calibration-apply → imaging
    AbsurdStreamingBridge,      # Bridge to streaming converter
    TaskChain,
    execute_chained_task,
    execute_housekeeping,
)

# Scheduling
from .scheduling import (
    TaskScheduler,
    ScheduledTask,
    ScheduleState,
    parse_cron_expression,
    calculate_next_run,
    create_schedule,
    get_schedule,
    list_schedules,
    update_schedule,
    delete_schedule,
    trigger_schedule_now,
    ensure_scheduled_tasks_table,
)

# Dependencies/DAG
from .dependencies import (
    WorkflowDAG,
    TaskNode,
    DependencyState,
    detect_cycles,
    topological_sort,
    get_ready_tasks,
    create_workflow,
    spawn_task_with_dependencies,
    get_workflow_dag,
    get_workflow_status,
    get_ready_workflow_tasks,
    list_workflows,
    ensure_dependencies_schema,
)
```

### 1.2 Set Up PostgreSQL Database

#### Prerequisites

- PostgreSQL 12+ installed and running
- `uuid-ossp` extension available
- Superuser or database creation privileges

#### Option A: Automated Setup (Recommended)

```bash
# Copy setup scripts if not present
cp -r legacy.backend/scripts/absurd/ scripts/absurd/

# Run setup
./scripts/absurd/setup_absurd_db.sh
./scripts/absurd/create_absurd_queues.sh

# Verify
python scripts/absurd/test_absurd_connection.py
```

#### Option B: Manual Setup

```bash
# 1. Create database
createdb dsa110_absurd

# 2. Apply schema
psql dsa110_absurd < backend/src/dsa110_contimg/absurd/schema.sql

# 3. Verify schema was created
psql dsa110_absurd -c "\dt absurd.*"
# Expected output:
#              List of relations
#  Schema |  Name  | Type  |  Owner
# --------+--------+-------+----------
#  absurd | tasks  | table | postgres
```

#### Database Schema Details

The `schema.sql` creates:

**Tables:**

- `absurd.tasks` - Main task queue table with columns:
  - `task_id` (UUID, PK) - Unique task identifier
  - `queue_name` (TEXT) - Queue this task belongs to
  - `task_name` (TEXT) - Task type (e.g., "imaging", "calibration-apply")
  - `params` (JSONB) - Task parameters
  - `priority` (INTEGER) - Higher = more urgent
  - `status` (TEXT) - pending/claimed/completed/failed/cancelled/retrying
  - `worker_id` (TEXT) - ID of worker processing this task
  - `attempt` (INTEGER) - Current attempt number
  - `max_retries` (INTEGER) - Maximum retry attempts
  - `result` (JSONB) - Task result (on completion)
  - `error` (TEXT) - Error message (on failure)
  - `created_at`, `claimed_at`, `completed_at` - Timestamps
  - `wait_time_sec`, `execution_time_sec` - Performance metrics

**Stored Functions:**

- `absurd.spawn_task()` - Create a new task
- `absurd.claim_task()` - Atomically claim next pending task (uses `FOR UPDATE SKIP LOCKED`)
- `absurd.complete_task()` - Mark task completed with result
- `absurd.fail_task()` - Mark task failed with error
- `absurd.cancel_task()` - Cancel a pending task
- `absurd.retry_task()` - Reset failed task to pending
- `absurd.get_queue_stats()` - Get task counts by status

**Indexes:**

- `idx_tasks_queue_status` - Fast lookup by queue + status
- `idx_tasks_priority` - Priority ordering for claiming
- `idx_tasks_created_at` - Time-based queries
- `idx_tasks_worker_id` - Worker task lookup

### 1.3 Install Dependencies

#### Python Dependencies

```bash
# Activate environment
conda activate casa6

# Install asyncpg (async PostgreSQL driver)
pip install asyncpg>=0.29.0

# Verify installation
python -c "import asyncpg; print(f'asyncpg {asyncpg.__version__}')"
# Expected: asyncpg 0.29.0 or higher
```

#### Add to requirements.txt

```bash
# Add to backend/requirements.txt
echo "asyncpg>=0.29.0" >> backend/requirements.txt
```

### 1.4 Add FastAPI Router

#### Copy Router from Legacy

```bash
cp legacy.backend/src/dsa110_contimg/api/routers/absurd.py \
   backend/src/dsa110_contimg/api/routers/
```

#### Register Router in Application

Edit `backend/src/dsa110_contimg/api/app.py`:

```python
# Add import at top of file
from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig

# Import router
from .routers import absurd as absurd_router

# In create_app() or at module level, add router
app.include_router(
    absurd_router.router,
    prefix="/absurd",
    tags=["absurd"],
)

# Add lifecycle hooks for Absurd client
@app.on_event("startup")
async def startup_absurd():
    config = AbsurdConfig.from_env()
    if config.enabled:
        app.state.absurd_client = AbsurdClient(config.database_url)
        await app.state.absurd_client.connect()
        logger.info("ABSURD client connected")
    else:
        app.state.absurd_client = None
        logger.info("ABSURD disabled")

@app.on_event("shutdown")
async def shutdown_absurd():
    if hasattr(app.state, 'absurd_client') and app.state.absurd_client:
        await app.state.absurd_client.close()
        logger.info("ABSURD client disconnected")
```

#### Verify Router Registration

```bash
# Start API server
cd /data/dsa110-contimg/backend
uvicorn dsa110_contimg.api.app:app --reload --port 8000

# Test health endpoint (in another terminal)
curl http://localhost:8000/absurd/health
# Expected (when disabled): {"status": "disabled", "enabled": false}
# Expected (when enabled): {"status": "ok", "enabled": true, "queue": "dsa110-pipeline"}
```

**API Endpoints:**

| Method | Endpoint                            | Description               |
| ------ | ----------------------------------- | ------------------------- |
| POST   | `/absurd/tasks`                     | Spawn a new task          |
| GET    | `/absurd/tasks/{task_id}`           | Get task details          |
| GET    | `/absurd/tasks`                     | List tasks (with filters) |
| DELETE | `/absurd/tasks/{task_id}`           | Cancel a task             |
| GET    | `/absurd/queues/{queue_name}/stats` | Queue statistics          |
| GET    | `/absurd/health`                    | Health check              |
| GET    | `/absurd/metrics`                   | Prometheus metrics        |
| POST   | `/absurd/schedules`                 | Create scheduled task     |
| GET    | `/absurd/workflows`                 | List workflows            |
| POST   | `/absurd/workflows`                 | Create workflow DAG       |

#### API Request/Response Examples

**Spawn a Task:**

```bash
curl -X POST http://localhost:8000/absurd/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "queue_name": "dsa110-pipeline",
    "task_name": "convert-uvh5-to-ms",
    "params": {
      "config": {},
      "inputs": {
        "input_path": "/data/incoming",
        "start_time": "2025-12-01T00:00:00",
        "end_time": "2025-12-01T01:00:00"
      }
    },
    "priority": 0,
    "timeout_sec": 3600
  }'

# Response:
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "queue_name": "dsa110-pipeline",
  "task_name": "convert-uvh5-to-ms",
  "created_at": "2025-12-01T12:00:00Z"
}
```

**Get Task Status:**

```bash
curl http://localhost:8000/absurd/tasks/a1b2c3d4-e5f6-7890-abcd-ef1234567890

# Response:
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "task_name": "convert-uvh5-to-ms",
  "params": {...},
  "result": {
    "status": "success",
    "outputs": {"ms_path": "/stage/dsa110-contimg/ms/2025-12-01T00:00:00.ms"},
    "message": "Conversion completed successfully"
  },
  "created_at": "2025-12-01T12:00:00Z",
  "claimed_at": "2025-12-01T12:00:01Z",
  "completed_at": "2025-12-01T12:15:32Z",
  "wait_time_sec": 1.2,
  "execution_time_sec": 931.4
}
```

**List Tasks with Filters:**

```bash
# List pending tasks
curl "http://localhost:8000/absurd/tasks?status=pending&limit=10"

# List failed imaging tasks
curl "http://localhost:8000/absurd/tasks?status=failed&task_name=imaging"

# Response:
{
  "tasks": [...],
  "total": 42
}
```

**Get Queue Statistics:**

```bash
curl http://localhost:8000/absurd/queues/dsa110-pipeline/stats

# Response:
{
  "queue_name": "dsa110-pipeline",
  "pending": 15,
  "claimed": 2,
  "completed": 1247,
  "failed": 23,
  "cancelled": 5,
  "retrying": 1,
  "total": 1293
}
```

### 1.5 Configure Environment

#### Configuration Reference

The `AbsurdConfig` dataclass reads from environment variables:

```python
@dataclass
class AbsurdConfig:
    enabled: bool = False                    # ABSURD_ENABLED
    database_url: str = "postgresql://..."   # ABSURD_DATABASE_URL
    queue_name: str = "dsa110-pipeline"      # ABSURD_QUEUE_NAME
    worker_concurrency: int = 4              # ABSURD_WORKER_CONCURRENCY
    worker_poll_interval_sec: float = 1.0    # ABSURD_WORKER_POLL_INTERVAL
    task_timeout_sec: int = 3600             # ABSURD_TASK_TIMEOUT
    max_retries: int = 3                     # ABSURD_MAX_RETRIES
    dead_letter_enabled: bool = True         # ABSURD_DLQ_ENABLED
    dead_letter_queue_name: str = "...-dlq"  # ABSURD_DLQ_QUEUE_NAME
```

#### Environment File

Add to `ops/systemd/contimg.env` or `.env`:

```bash
# =============================================================================
# ABSURD Workflow Manager Configuration
# =============================================================================

# Enable ABSURD (set to "false" to disable)
ABSURD_ENABLED=true

# PostgreSQL connection URL
# Format: postgresql://user:password@host:port/database
ABSURD_DATABASE_URL=postgresql://postgres@localhost/dsa110_absurd

# Queue name for pipeline tasks
ABSURD_QUEUE_NAME=dsa110-pipeline

# Worker settings
ABSURD_WORKER_CONCURRENCY=4        # Max concurrent tasks per worker
ABSURD_WORKER_POLL_INTERVAL=1.0    # Seconds between polling for new tasks

# Task settings
ABSURD_TASK_TIMEOUT=3600           # Default timeout: 1 hour (imaging can take 60+ min)
ABSURD_MAX_RETRIES=3               # Retry failed tasks up to 3 times

# Dead letter queue (for tasks that exceed max retries)
ABSURD_DLQ_ENABLED=true
ABSURD_DLQ_QUEUE_NAME=dsa110-pipeline-dlq
```

#### Validation

Test configuration loading:

```bash
# Python validation
python -c "
from dsa110_contimg.absurd import AbsurdConfig
config = AbsurdConfig.from_env()
config.validate()
print(f'ABSURD enabled: {config.enabled}')
print(f'Database: {config.database_url}')
print(f'Queue: {config.queue_name}')
print(f'Concurrency: {config.worker_concurrency}')
"
```

---

## Phase 2: Frontend Integration

### 2.1 Create ABSURD API Client

**File:** `frontend/src/api/absurd.ts`

This file provides a typed TypeScript client for all ABSURD API endpoints.

```typescript
import { apiClient } from "./client";

// =============================================================================
// Types
// =============================================================================

/** Task status values */
export type TaskStatus =
  | "pending" // Waiting in queue
  | "claimed" // Being processed by worker
  | "completed" // Finished successfully
  | "failed" // Failed (may retry)
  | "cancelled" // Cancelled by user
  | "retrying"; // Waiting for retry

/** A task in the Absurd queue */
export interface Task {
  task_id: string;
  queue_name: string;
  task_name: string;
  status: TaskStatus;
  params: Record<string, unknown>;
  priority: number;
  attempt: number;
  max_retries: number;
  created_at: string;
  claimed_at?: string;
  completed_at?: string;
  worker_id?: string;
  result?: TaskResult;
  error?: string;
  wait_time_sec?: number;
  execution_time_sec?: number;
}

/** Result returned by task executor */
export interface TaskResult {
  status: "success" | "error";
  outputs?: Record<string, unknown>;
  message?: string;
  errors?: string[];
}

/** Request to spawn a new task */
export interface SpawnTaskRequest {
  queue_name?: string; // Default: "dsa110-pipeline"
  task_name: TaskName;
  params: Record<string, unknown>;
  priority?: number; // Default: 0 (higher = more urgent)
  timeout_sec?: number; // Default: 3600
}

/** Available task types */
export type TaskName =
  | "convert-uvh5-to-ms"
  | "calibration-solve"
  | "calibration-apply"
  | "imaging"
  | "validation"
  | "crossmatch"
  | "photometry"
  | "catalog-setup"
  | "organize-files"
  | "housekeeping"
  | "create-mosaic";

/** Queue statistics */
export interface QueueStats {
  queue_name: string;
  pending: number;
  claimed: number;
  completed: number;
  failed: number;
  cancelled: number;
  retrying: number;
  total: number;
}

/** Parameters for listing tasks */
export interface ListTasksParams {
  status?: TaskStatus;
  task_name?: TaskName;
  queue_name?: string;
  limit?: number; // Default: 100
  offset?: number; // Default: 0
}

/** Health check response */
export interface HealthResponse {
  status: "ok" | "disabled" | "error";
  enabled: boolean;
  queue?: string;
  error?: string;
}

/** Paginated task list response */
export interface TaskListResponse {
  tasks: Task[];
  total: number;
}

// =============================================================================
// API Client
// =============================================================================

export const absurdApi = {
  /**
   * Check ABSURD health status
   * Returns disabled status if ABSURD_ENABLED=false
   */
  health: () => apiClient.get<HealthResponse>("/absurd/health"),

  /**
   * Spawn a new task in the queue
   * @param data Task specification
   * @returns Created task with pending status
   */
  spawnTask: (data: SpawnTaskRequest) =>
    apiClient.post<Task>("/absurd/tasks", {
      queue_name: data.queue_name ?? "dsa110-pipeline",
      ...data,
    }),

  /**
   * Get task details by ID
   * @param taskId UUID of the task
   */
  getTask: (taskId: string) => apiClient.get<Task>(`/absurd/tasks/${taskId}`),

  /**
   * List tasks with optional filters
   * @param params Filter and pagination parameters
   */
  listTasks: (params?: ListTasksParams) =>
    apiClient.get<TaskListResponse>("/absurd/tasks", { params }),

  /**
   * Cancel a pending or retrying task
   * Cannot cancel claimed (in-progress) tasks
   * @param taskId UUID of the task to cancel
   */
  cancelTask: (taskId: string) => apiClient.delete(`/absurd/tasks/${taskId}`),

  /**
   * Get queue statistics
   * @param queueName Queue name (default: "dsa110-pipeline")
   */
  getQueueStats: (queueName: string = "dsa110-pipeline") =>
    apiClient.get<QueueStats>(`/absurd/queues/${queueName}/stats`),

  /**
   * Retry a failed task
   * @param taskId UUID of the failed task
   */
  retryTask: (taskId: string) =>
    apiClient.post<Task>(`/absurd/tasks/${taskId}/retry`),
};

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Check if ABSURD is available
 * Returns false if disabled or unreachable
 */
export async function isAbsurdAvailable(): Promise<boolean> {
  try {
    const response = await absurdApi.health();
    return response.data.enabled && response.data.status === "ok";
  } catch {
    return false;
  }
}

/**
 * Get human-readable task status
 */
export function getTaskStatusLabel(status: TaskStatus): string {
  const labels: Record<TaskStatus, string> = {
    pending: "Pending",
    claimed: "Running",
    completed: "Completed",
    failed: "Failed",
    cancelled: "Cancelled",
    retrying: "Retrying",
  };
  return labels[status];
}

/**
 * Get status color for UI
 */
export function getTaskStatusColor(status: TaskStatus): string {
  const colors: Record<TaskStatus, string> = {
    pending: "gray",
    claimed: "blue",
    completed: "green",
    failed: "red",
    cancelled: "orange",
    retrying: "yellow",
  };
  return colors[status];
}
```

### 2.2 Create React Query Hooks

**File:** `frontend/src/api/absurdQueries.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  absurdApi,
  ListTasksParams,
  SpawnTaskRequest,
  Task,
  QueueStats,
  HealthResponse,
  TaskListResponse,
} from "./absurd";

// =============================================================================
// Query Keys Factory
// =============================================================================

/**
 * Centralized query keys for cache management
 * Using factory pattern for type safety and consistency
 */
export const absurdKeys = {
  all: ["absurd"] as const,
  health: () => [...absurdKeys.all, "health"] as const,
  tasks: () => [...absurdKeys.all, "tasks"] as const,
  tasksList: (params?: ListTasksParams) =>
    [...absurdKeys.tasks(), params] as const,
  task: (id: string) => [...absurdKeys.all, "task", id] as const,
  queues: () => [...absurdKeys.all, "queues"] as const,
  queue: (name: string) => [...absurdKeys.queues(), name] as const,
};

// =============================================================================
// Queries
// =============================================================================

/**
 * Check ABSURD health status
 * Polls every 30 seconds to detect service availability changes
 */
export const useAbsurdHealth = () =>
  useQuery<HealthResponse>({
    queryKey: absurdKeys.health(),
    queryFn: async () => {
      const response = await absurdApi.health();
      return response.data;
    },
    refetchInterval: 30000,
    // Don't show error toasts for health checks
    meta: { suppressErrors: true },
  });

/**
 * List tasks with optional filters
 * Polls every 5 seconds for real-time updates
 */
export const useAbsurdTasks = (params?: ListTasksParams) =>
  useQuery<TaskListResponse>({
    queryKey: absurdKeys.tasksList(params),
    queryFn: async () => {
      const response = await absurdApi.listTasks(params);
      return response.data;
    },
    refetchInterval: 5000,
    // Keep previous data while refetching
    placeholderData: (previousData) => previousData,
  });

/**
 * Get single task details
 * Polls every 2 seconds when task is in progress
 */
export const useAbsurdTask = (taskId: string) =>
  useQuery<Task>({
    queryKey: absurdKeys.task(taskId),
    queryFn: async () => {
      const response = await absurdApi.getTask(taskId);
      return response.data;
    },
    enabled: !!taskId,
    refetchInterval: (query) => {
      // Poll faster for in-progress tasks
      const status = query.state.data?.status;
      if (status === "claimed" || status === "pending") {
        return 2000; // 2 seconds
      }
      return false; // Stop polling for completed/failed/cancelled
    },
  });

/**
 * Get queue statistics
 * Polls every 10 seconds for dashboard display
 */
export const useAbsurdQueueStats = (queueName: string = "dsa110-pipeline") =>
  useQuery<QueueStats>({
    queryKey: absurdKeys.queue(queueName),
    queryFn: async () => {
      const response = await absurdApi.getQueueStats(queueName);
      return response.data;
    },
    refetchInterval: 10000,
  });

// =============================================================================
// Mutations
// =============================================================================

/**
 * Spawn a new task
 * Invalidates task list on success
 */
export const useSpawnTask = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: SpawnTaskRequest) => {
      const response = await absurdApi.spawnTask(data);
      return response.data;
    },
    onSuccess: (newTask) => {
      // Invalidate list to show new task
      queryClient.invalidateQueries({ queryKey: absurdKeys.tasks() });
      // Invalidate queue stats
      queryClient.invalidateQueries({
        queryKey: absurdKeys.queue(newTask.queue_name),
      });
    },
  });
};

/**
 * Cancel a task
 * Invalidates both task and list caches
 */
export const useCancelTask = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (taskId: string) => {
      await absurdApi.cancelTask(taskId);
      return taskId;
    },
    onSuccess: (taskId) => {
      queryClient.invalidateQueries({ queryKey: absurdKeys.task(taskId) });
      queryClient.invalidateQueries({ queryKey: absurdKeys.tasks() });
      queryClient.invalidateQueries({ queryKey: absurdKeys.queues() });
    },
  });
};

/**
 * Retry a failed task
 */
export const useRetryTask = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (taskId: string) => {
      const response = await absurdApi.retryTask(taskId);
      return response.data;
    },
    onSuccess: (_, taskId) => {
      queryClient.invalidateQueries({ queryKey: absurdKeys.task(taskId) });
      queryClient.invalidateQueries({ queryKey: absurdKeys.tasks() });
    },
  });
};

// =============================================================================
// Custom Hooks
// =============================================================================

/**
 * Hook to check if ABSURD is enabled and available
 * Useful for conditional rendering of workflow features
 */
export const useAbsurdEnabled = () => {
  const { data, isLoading, error } = useAbsurdHealth();

  return {
    isEnabled: data?.enabled ?? false,
    isAvailable: data?.status === "ok",
    isLoading,
    error,
  };
};
```

### 2.3 Create Workflows Dashboard Page

**File:** `frontend/src/pages/WorkflowsPage.tsx`

The dashboard should include these components:

#### Component Structure

```
WorkflowsPage/
├── components/
│   ├── QueueStatsCard.tsx      # Display queue metrics
│   ├── TaskTable.tsx           # Filterable task list
│   ├── TaskDetailDrawer.tsx    # Task details panel
│   ├── SpawnTaskDialog.tsx     # Create new task form
│   └── TaskStatusBadge.tsx     # Status indicator
├── hooks/
│   └── useTaskFilters.ts       # Filter state management
└── WorkflowsPage.tsx           # Main page component
```

#### Page Layout

```tsx
// frontend/src/pages/WorkflowsPage.tsx
import { useState } from "react";
import {
  useAbsurdEnabled,
  useAbsurdTasks,
  useAbsurdQueueStats,
} from "@/api/absurdQueries";

export function WorkflowsPage() {
  const { isEnabled, isAvailable } = useAbsurdEnabled();
  const [filters, setFilters] = useState<ListTasksParams>({
    limit: 50,
  });

  // Show disabled state if ABSURD not available
  if (!isEnabled) {
    return <AbsurdDisabledBanner />;
  }

  return (
    <div className="space-y-6">
      {/* Header with actions */}
      <PageHeader title="Workflows" actions={<SpawnTaskButton />} />

      {/* Queue statistics cards */}
      <QueueStatsSection />

      {/* Task filters */}
      <TaskFilters filters={filters} onFiltersChange={setFilters} />

      {/* Task list table */}
      <TaskTable filters={filters} />
    </div>
  );
}
```

#### Key Features to Implement

1. **Queue Stats Cards** - Display pending/running/completed/failed counts
2. **Task Table** - Sortable, filterable table with columns:
   - Task ID (truncated UUID)
   - Task Name
   - Status (with color badge)
   - Priority
   - Created At
   - Duration (for completed tasks)
   - Actions (view, cancel, retry)
3. **Task Detail Drawer** - Side panel showing:
   - Full task details
   - Parameters (JSON viewer)
   - Result/Error output
   - Timing information
4. **Spawn Task Dialog** - Form with:
   - Task type selector
   - JSON parameter editor
   - Priority slider
   - Timeout input

### 2.4 Add Route Configuration

Update `frontend/src/router.tsx`:

```typescript
import { WorkflowsPage } from "@/pages/WorkflowsPage";

// Add to routes array
{
  path: "/workflows",
  element: <WorkflowsPage />,
}
```

Update sidebar navigation (`frontend/src/components/layout/Sidebar.tsx`):

```typescript
{
  label: "Workflows",
  href: "/workflows",
  icon: <WorkflowIcon />,  // or PlayCircle, ListChecks, etc.
}
```

### 2.5 Error Handling

#### Existing Error Mapping

Already exists in `frontend/src/constants/errorMappings.ts`:

```typescript
ABSURD_DISABLED: {
  user_message: "Task queue service is disabled",
  action: "Enable queue service or proceed without it",
  severity: "info",
},
```

#### Graceful Degradation Pattern

```typescript
// In components that use ABSURD
function MyComponent() {
  const { isEnabled, isLoading } = useAbsurdEnabled();

  if (isLoading) {
    return <Skeleton />;
  }

  if (!isEnabled) {
    return (
      <Alert severity="info">
        <AlertTitle>Workflow Queue Disabled</AlertTitle>
        <AlertDescription>
          The task queue is currently disabled. Tasks will run directly without
          queuing. Enable ABSURD_ENABLED=true for durable workflow execution.
        </AlertDescription>
      </Alert>
    );
  }

  return <NormalContent />;
}
```

---

## Phase 3: Worker Deployment

### 3.1 Create Systemd Service

**File:** `ops/systemd/contimg-absurd-worker.service`

```ini
[Unit]
Description=DSA-110 ABSURD Workflow Worker
Documentation=file:///data/dsa110-contimg/docs/guides/absurd-deployment-plan.md
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=dsa110
Group=dsa110
WorkingDirectory=/data/dsa110-contimg/backend

# Environment
EnvironmentFile=/data/dsa110-contimg/ops/systemd/contimg.env

# Activate conda environment and run worker
ExecStart=/bin/bash -c 'source /opt/conda/etc/profile.d/conda.sh && \
    conda activate casa6 && \
    python -m dsa110_contimg.absurd.worker'

# Restart policy
Restart=always
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=5

# Resource limits
MemoryMax=64G
CPUQuota=800%

# Logging
StandardOutput=append:/data/dsa110-contimg/state/logs/absurd-worker.log
StandardError=append:/data/dsa110-contimg/state/logs/absurd-worker.log

[Install]
WantedBy=multi-user.target
```

#### Install and Enable Service

```bash
# Copy service file
sudo cp ops/systemd/contimg-absurd-worker.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable contimg-absurd-worker

# Start worker
sudo systemctl start contimg-absurd-worker

# Check status
sudo systemctl status contimg-absurd-worker

# View logs
journalctl -u contimg-absurd-worker -f
```

### 3.2 Task Executors Reference

The `adapter.py` module in legacy backend contains complete implementations.
Here's the mapping of task names to pipeline stages:

| Task Name            | Pipeline Stage            | Description                        |
| -------------------- | ------------------------- | ---------------------------------- |
| `convert-uvh5-to-ms` | `ConversionStage`         | Convert UVH5 subband groups to MS  |
| `calibration-solve`  | `CalibrationSolveStage`   | Solve for calibration solutions    |
| `calibration-apply`  | `CalibrationStage`        | Apply calibration to MS            |
| `imaging`            | `ImagingStage`            | Create sky images (WSClean/tclean) |
| `validation`         | `ValidationStage`         | QA checks on products              |
| `crossmatch`         | `CrossMatchStage`         | Match sources to catalogs          |
| `photometry`         | `AdaptivePhotometryStage` | Time-domain photometry             |
| `catalog-setup`      | `CatalogSetupStage`       | Download/update catalogs           |
| `organize-files`     | `OrganizationStage`       | File organization                  |
| `housekeeping`       | N/A                       | Cleanup old files, compact DBs     |
| `create-mosaic`      | N/A                       | Create mosaic from multiple images |

#### Task Parameter Formats

Each task type expects specific parameters:

**`convert-uvh5-to-ms`:**

```python
{
    "config": {},  # PipelineConfig dict
    "inputs": {
        "input_path": "/data/incoming",
        "start_time": "2025-12-01T00:00:00",
        "end_time": "2025-12-01T01:00:00"
    }
}
```

**`calibration-apply`:**

```python
{
    "config": {},
    "inputs": {
        "ms_path": "/stage/dsa110-contimg/ms/2025-12-01T00:00:00.ms",
        "cal_table_path": "/stage/dsa110-contimg/cal/bandpass.cal"
    }
}
```

**`imaging`:**

```python
{
    "config": {},
    "inputs": {
        "ms_path": "/stage/dsa110-contimg/ms/2025-12-01T00:00:00.ms",
        "output_dir": "/stage/dsa110-contimg/images",
        "field_id": 0,
        "imager": "wsclean"  # or "tclean"
    }
}
```

#### Task Chains (Predefined Workflows)

The adapter provides predefined task chains:

```python
# Standard full pipeline
STANDARD_PIPELINE_CHAIN = TaskChain([
    "convert-uvh5-to-ms",
    "calibration-solve",
    "calibration-apply",
    "imaging",
    "validation",
    "crossmatch",
    "photometry",
])

# Quick imaging (skip calibration for already-calibrated data)
QUICK_IMAGING_CHAIN = TaskChain([
    "convert-uvh5-to-ms",
    "imaging",
])

# Calibrator observation
CALIBRATOR_CHAIN = TaskChain([
    "convert-uvh5-to-ms",
    "calibration-solve",
])

# Target observation (apply existing calibration)
TARGET_CHAIN = TaskChain([
    "calibration-apply",
    "imaging",
    "photometry",
])
```

### 3.3 Resource Requirements

| Task Type   | Memory | CPU     | Duration | Concurrency |
| ----------- | ------ | ------- | -------- | ----------- |
| Conversion  | 4 GB   | 2 cores | 15 min   | 4           |
| Calibration | 8 GB   | 4 cores | 30 min   | 2           |
| Imaging     | 16 GB  | 8 cores | 60 min   | 2           |
| Validation  | 2 GB   | 1 core  | 5 min    | 8           |
| Photometry  | 4 GB   | 2 cores | 20 min   | 4           |

**Recommended Worker Host:**

- Total RAM: 64 GB
- Total CPUs: 32 cores
- Worker Concurrency: 4-8

### 3.4 Worker Lifecycle

The `AbsurdWorker` class handles:

1. **Polling Loop** - Checks for pending tasks every `poll_interval` seconds
2. **Task Claiming** - Uses `FOR UPDATE SKIP LOCKED` for atomic claim
3. **Execution** - Runs task in thread pool via `asyncio.to_thread()`
4. **Heartbeat** - Sends periodic heartbeats during long tasks
5. **Completion** - Records result/error and timing metrics
6. **WebSocket Events** - Emits real-time updates to connected clients

```python
# Worker main loop (simplified)
class AbsurdWorker:
    async def start(self):
        async with self.client:
            while self.running:
                task = await self.client.claim_task(
                    self.config.queue_name,
                    self.worker_id
                )
                if task:
                    await self._process_task(task)
                else:
                    await asyncio.sleep(self.config.worker_poll_interval_sec)
```

---

## Phase 4: Testing & Rollout

### 4.1 Pre-Deployment Verification

#### Backend Verification

```bash
# 1. Verify module imports
cd /data/dsa110-contimg/backend
python -c "
from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig, AbsurdWorker
print('✓ Module imports successful')
"

# 2. Verify configuration loads
python -c "
from dsa110_contimg.absurd import AbsurdConfig
config = AbsurdConfig.from_env()
config.validate()
print(f'✓ Config valid: enabled={config.enabled}, queue={config.queue_name}')
"

# 3. Test database connection
python -c "
import asyncio
from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig

async def test():
    config = AbsurdConfig.from_env()
    async with AbsurdClient(config.database_url) as client:
        stats = await client.get_queue_stats(config.queue_name)
        print(f'✓ Database connected: {stats}')

asyncio.run(test())
"
```

#### Frontend Verification

```bash
# 1. Type check
cd /data/dsa110-contimg/frontend
npm run typecheck

# 2. Lint
npm run lint

# 3. Unit tests
npm run test -- --testPathPattern=absurd --passWithNoTests
```

### 4.2 Unit Tests

Create test files:

**Backend:** `backend/tests/unit/absurd/test_client.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from dsa110_contimg.absurd import AbsurdClient, AbsurdConfig


@pytest.fixture
def mock_pool():
    """Mock asyncpg connection pool."""
    pool = AsyncMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(
        return_value=MagicMock()
    )
    return pool


@pytest.mark.asyncio
async def test_spawn_task(mock_pool):
    """Test spawning a task."""
    client = AbsurdClient("postgresql://test")
    client._pool = mock_pool

    task_id = await client.spawn_task(
        queue_name="test-queue",
        task_name="test-task",
        params={"key": "value"},
    )

    assert task_id is not None


@pytest.mark.asyncio
async def test_config_from_env(monkeypatch):
    """Test loading config from environment."""
    monkeypatch.setenv("ABSURD_ENABLED", "true")
    monkeypatch.setenv("ABSURD_QUEUE_NAME", "my-queue")

    config = AbsurdConfig.from_env()

    assert config.enabled is True
    assert config.queue_name == "my-queue"
```

**Frontend:** `frontend/src/api/absurd.test.ts`

```typescript
import { describe, it, expect, vi } from "vitest";
import { absurdApi, getTaskStatusLabel, getTaskStatusColor } from "./absurd";

describe("absurdApi", () => {
  it("should have all required methods", () => {
    expect(absurdApi.health).toBeDefined();
    expect(absurdApi.spawnTask).toBeDefined();
    expect(absurdApi.getTask).toBeDefined();
    expect(absurdApi.listTasks).toBeDefined();
    expect(absurdApi.cancelTask).toBeDefined();
    expect(absurdApi.getQueueStats).toBeDefined();
  });
});

describe("getTaskStatusLabel", () => {
  it("returns correct labels", () => {
    expect(getTaskStatusLabel("pending")).toBe("Pending");
    expect(getTaskStatusLabel("claimed")).toBe("Running");
    expect(getTaskStatusLabel("completed")).toBe("Completed");
    expect(getTaskStatusLabel("failed")).toBe("Failed");
  });
});

describe("getTaskStatusColor", () => {
  it("returns correct colors", () => {
    expect(getTaskStatusColor("completed")).toBe("green");
    expect(getTaskStatusColor("failed")).toBe("red");
    expect(getTaskStatusColor("claimed")).toBe("blue");
  });
});
```

### 4.3 Integration Tests

```bash
# 1. Start API server (terminal 1)
cd /data/dsa110-contimg/backend
uvicorn dsa110_contimg.api.app:app --port 8000

# 2. Run integration tests (terminal 2)

# Test health endpoint
curl -s http://localhost:8000/absurd/health | jq .
# Expected: {"status": "ok", "enabled": true, ...}

# Test spawn task
TASK_ID=$(curl -s -X POST http://localhost:8000/absurd/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "queue_name": "dsa110-pipeline",
    "task_name": "validation",
    "params": {"test_mode": true}
  }' | jq -r .task_id)
echo "Created task: $TASK_ID"

# Test get task
curl -s "http://localhost:8000/absurd/tasks/$TASK_ID" | jq .

# Test list tasks
curl -s "http://localhost:8000/absurd/tasks?status=pending&limit=5" | jq .

# Test queue stats
curl -s http://localhost:8000/absurd/queues/dsa110-pipeline/stats | jq .

# Test cancel task
curl -s -X DELETE "http://localhost:8000/absurd/tasks/$TASK_ID" | jq .
```

### 4.4 Staged Rollout

#### Stage 1: Deploy Disabled (Day 1)

```bash
# 1. Deploy code with ABSURD disabled
export ABSURD_ENABLED=false
sudo systemctl restart contimg-api

# 2. Verify disabled response
curl http://localhost:8000/absurd/health
# Expected: {"status": "disabled", "enabled": false}

# 3. Verify frontend shows "disabled" banner
# Visit http://localhost:3000/workflows
```

#### Stage 2: Enable for Testing (Day 2-3)

```bash
# 1. Enable ABSURD
export ABSURD_ENABLED=true
sudo systemctl restart contimg-api

# 2. Start worker
sudo systemctl start contimg-absurd-worker

# 3. Monitor worker logs
journalctl -u contimg-absurd-worker -f

# 4. Run test pipeline
curl -X POST http://localhost:8000/absurd/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "validation",
    "params": {"ms_path": "/stage/dsa110-contimg/ms/test.ms"}
  }'

# 5. Monitor task completion
watch -n 2 'curl -s http://localhost:8000/absurd/queues/dsa110-pipeline/stats | jq .'
```

#### Stage 3: Production Rollout (Day 4+)

```bash
# 1. Enable for streaming converter (10%)
# Edit streaming converter to route 10% of groups to ABSURD

# 2. Monitor for 24 hours
# Check metrics dashboard, queue depth, success rate

# 3. Increase to 50%
# Edit streaming converter to route 50% of groups

# 4. Monitor for 24 hours

# 5. Full rollout (100%)
# All groups routed through ABSURD
```

### 4.5 Rollback Plan

If issues arise at any stage:

```bash
# 1. Disable ABSURD immediately
export ABSURD_ENABLED=false
sudo systemctl restart contimg-api

# 2. Stop worker
sudo systemctl stop contimg-absurd-worker

# 3. System falls back to direct execution
# Pipeline continues without ABSURD

# 4. Tasks remain in PostgreSQL (no data loss)
# Can retry later after fixing issues

# 5. Query pending tasks for triage
psql dsa110_absurd -c "
  SELECT task_id, task_name, status, created_at
  FROM absurd.tasks
  WHERE status = 'pending'
  ORDER BY created_at;
"
```

---

## Deployment Checklist

### Backend

- [ ] Migrate `absurd/` module to `backend/src/dsa110_contimg/absurd/`
- [ ] Create PostgreSQL database `dsa110_absurd`
- [ ] Apply schema: `schema.sql`
- [ ] Install `asyncpg>=0.29.0`
- [ ] Register FastAPI router in `app.py`
- [ ] Add environment variables to `contimg.env`
- [ ] Implement 9 task executors in `adapter.py`
- [ ] Write unit tests for client, worker, adapter
- [ ] Write integration tests for API endpoints

### Frontend

- [ ] Create `src/api/absurd.ts` - API client
- [ ] Create `src/api/absurdQueries.ts` - React Query hooks
- [ ] Create `src/pages/WorkflowsPage.tsx` - Dashboard
- [ ] Add route to `router.tsx`
- [ ] Add navigation link in sidebar
- [ ] Handle `ABSURD_DISABLED` error gracefully
- [ ] Write component tests

### Operations

- [ ] Create `contimg-absurd-worker.service`
- [ ] Enable and start worker service
- [ ] Configure log rotation for worker logs
- [ ] Set up Prometheus scraping for `/absurd/metrics`
- [ ] Create Grafana dashboard for ABSURD metrics
- [ ] Configure alerting for failures

### Documentation

- [ ] Update API reference docs
- [ ] Create operations runbook
- [ ] Write troubleshooting guide
- [ ] Document rollback procedures

---

## Monitoring & Alerting

### Key Metrics

- `absurd_tasks_total{status}` - Total tasks by status
- `absurd_tasks_current{status}` - Current task counts
- `absurd_wait_time_seconds` - Task wait time (p50, p95, p99)
- `absurd_execution_time_seconds` - Execution time (p50, p95, p99)
- `absurd_throughput_per_minute` - Tasks completed per minute
- `absurd_success_rate` - Success rate (0-1)
- `absurd_error_rate` - Error rate (0-1)

### Alerts

| Alert             | Condition                           | Severity |
| ----------------- | ----------------------------------- | -------- |
| Queue Backlog     | `pending_count > 1000`              | Warning  |
| High Failure Rate | `error_rate_5min > 0.10`            | Critical |
| Slow Tasks        | `p95_execution_time > 2 * expected` | Warning  |
| Worker Down       | No task claims for 5 min            | Critical |

---

## Timeline Estimate

| Phase     | Duration      | Description            |
| --------- | ------------- | ---------------------- |
| Phase 1   | 1-2 days      | Backend infrastructure |
| Phase 2   | 2-3 days      | Frontend integration   |
| Phase 3   | 1-2 days      | Worker deployment      |
| Phase 4   | 2-3 days      | Testing & rollout      |
| **Total** | **6-10 days** | Full deployment        |

---

## References

- Legacy implementation: `legacy.backend/src/dsa110_contimg/absurd/`
- Status docs: `.local/internal/docs/dev/status/2025-11/absurd_*.md`
- Operations guide: `legacy.backend/docs/operations/absurd_operations_guide.md`
