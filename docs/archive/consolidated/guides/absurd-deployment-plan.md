# ABSURD Workflow Manager Deployment Plan

**Date:** 2025-12-01  
**Status:** Deployed (services pending activation)  
**Target:** Deploy durable workflow manager to `frontend/` and `backend/`
**Last Verified:** 2025-12-01 (Pre-flight check passed)

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
| React Query       | `frontend/package.json`                                   | ✅ @tanstack/react-query installed |

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

### Prometheus Metrics Endpoint

The `/absurd/metrics` endpoint exports Prometheus-format metrics:

```text
# HELP absurd_tasks_total Total number of tasks by status
# TYPE absurd_tasks_total counter
absurd_tasks_total{status="spawned"} 1247
absurd_tasks_total{status="claimed"} 1245
absurd_tasks_total{status="completed"} 1220
absurd_tasks_total{status="failed"} 23
absurd_tasks_total{status="cancelled"} 5

# HELP absurd_tasks_current Current number of tasks by status
# TYPE absurd_tasks_current gauge
absurd_tasks_current{status="pending"} 15
absurd_tasks_current{status="claimed"} 2

# HELP absurd_wait_time_seconds Task wait time in seconds
# TYPE absurd_wait_time_seconds summary
absurd_wait_time_seconds{quantile="0.5"} 1.2
absurd_wait_time_seconds{quantile="0.95"} 5.8
absurd_wait_time_seconds{quantile="0.99"} 12.3

# HELP absurd_execution_time_seconds Task execution time in seconds
# TYPE absurd_execution_time_seconds summary
absurd_execution_time_seconds{quantile="0.5"} 120.5
absurd_execution_time_seconds{quantile="0.95"} 890.2
absurd_execution_time_seconds{quantile="0.99"} 1800.0

# HELP absurd_throughput_per_minute Tasks completed per minute
# TYPE absurd_throughput_per_minute gauge
absurd_throughput_per_minute{window="1m"} 2.5
absurd_throughput_per_minute{window="5m"} 2.8
absurd_throughput_per_minute{window="15m"} 3.1
```

### Prometheus Scrape Configuration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "absurd"
    static_configs:
      - targets: ["localhost:8000"]
    metrics_path: "/absurd/metrics"
    scrape_interval: 15s
```

### Grafana Dashboard

Create dashboard with panels for:

1. **Queue Overview** (Stat panels)

   - Pending tasks
   - Running tasks
   - Completed (24h)
   - Failed (24h)

2. **Throughput** (Time series)

   - Tasks/minute over time
   - By task type

3. **Latency** (Time series)

   - Wait time p50/p95/p99
   - Execution time p50/p95/p99

4. **Success Rate** (Gauge)

   - Current success rate
   - Error rate trend

5. **Task Breakdown** (Pie chart)
   - By task type
   - By status

### Alerts

| Alert             | Condition                           | Severity |
| ----------------- | ----------------------------------- | -------- |
| Queue Backlog     | `pending_count > 1000`              | Warning  |
| High Failure Rate | `error_rate_5min > 0.10`            | Critical |
| Slow Tasks        | `p95_execution_time > 2 * expected` | Warning  |
| Worker Down       | No task claims for 5 min            | Critical |

#### Alertmanager Rules

```yaml
groups:
  - name: absurd
    rules:
      - alert: AbsurdQueueBacklog
        expr: absurd_tasks_current{status="pending"} > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "ABSURD queue backlog detected"
          description: "{{ $value }} pending tasks in queue"

      - alert: AbsurdHighFailureRate
        expr: absurd_error_rate{window="5m"} > 0.10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "ABSURD high failure rate"
          description: "{{ $value | humanizePercentage }} failure rate"

      - alert: AbsurdWorkerDown
        expr: increase(absurd_tasks_total{status="claimed"}[5m]) == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "ABSURD worker not claiming tasks"
          description: "No tasks claimed in last 5 minutes"
```

---

## Edge Cases and Handling Strategies

This section documents edge cases that can occur in production and how the system
handles (or should handle) each scenario.

### 1. Worker Crashes Mid-Task

**Scenario:** Worker process dies while executing a task (OOM, SIGKILL, power loss).

**Current Behavior:**

- Task remains in `claimed` status with stale `claimed_at` timestamp
- No heartbeat updates occur
- Task appears "stuck"

**Required Handling:**

```sql
-- Reaper job to reclaim orphaned tasks (run every 5 minutes)
UPDATE absurd.tasks
SET status = 'pending',
    worker_id = NULL,
    claimed_at = NULL
WHERE status = 'claimed'
  AND claimed_at < NOW() - INTERVAL '10 minutes'  -- No heartbeat for 10 min
  AND attempt < max_retries;

-- Move exhausted retries to failed
UPDATE absurd.tasks
SET status = 'failed',
    error = 'Task abandoned after worker crash (max retries exhausted)',
    completed_at = NOW()
WHERE status = 'claimed'
  AND claimed_at < NOW() - INTERVAL '10 minutes'
  AND attempt >= max_retries;
```

**Implementation:** Add a periodic cleanup task in the worker or a separate
systemd timer:

```python
# backend/src/dsa110_contimg/absurd/reaper.py
async def reap_orphaned_tasks(client: AbsurdClient, timeout_minutes: int = 10):
    """Reclaim tasks from crashed workers."""
    async with client._pool.acquire() as conn:
        # Reclaim retriable tasks
        reclaimed = await conn.execute("""
            UPDATE absurd.tasks
            SET status = 'pending', worker_id = NULL, claimed_at = NULL
            WHERE status = 'claimed'
              AND claimed_at < NOW() - INTERVAL '%s minutes'
              AND attempt < max_retries
        """, timeout_minutes)

        # Fail exhausted tasks
        failed = await conn.execute("""
            UPDATE absurd.tasks
            SET status = 'failed',
                error = 'Abandoned after worker crash',
                completed_at = NOW()
            WHERE status = 'claimed'
              AND claimed_at < NOW() - INTERVAL '%s minutes'
              AND attempt >= max_retries
        """, timeout_minutes)

        return {"reclaimed": reclaimed, "failed": failed}
```

### 2. Database Connection Lost During Task Execution

**Scenario:** Network partition or PostgreSQL restart while task is running.

**Current Behavior:**

- `asyncpg.InterfaceError` or `asyncpg.ConnectionDoesNotExistError` raised
- Task execution may complete but result cannot be saved
- Worker may crash or enter error recovery

**Required Handling:**

```python
# In worker._process_task()
async def _process_task(self, task: Dict[str, Any]):
    task_id = task["task_id"]
    result = None

    try:
        result = await self.executor(task["task_name"], task["params"])
    except Exception as e:
        logger.exception(f"Task {task_id} execution failed")
        result = {"status": "error", "errors": [str(e)]}

    # Retry database operations with backoff
    for attempt in range(3):
        try:
            if result.get("status") == "error":
                await self.client.fail_task(task_id, result["errors"][0])
            else:
                await self.client.complete_task(task_id, result)
            break
        except (asyncpg.InterfaceError, asyncpg.ConnectionDoesNotExistError):
            logger.warning(f"DB connection lost, attempt {attempt + 1}/3")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            await self.client.connect()  # Reconnect
    else:
        # All retries failed - write result to local recovery file
        await self._write_recovery_file(task_id, result)
```

**Recovery File Format:**

```python
# backend/src/dsa110_contimg/absurd/recovery.py
import json
from pathlib import Path

RECOVERY_DIR = Path("/data/dsa110-contimg/state/absurd_recovery")

async def write_recovery_file(task_id: str, result: dict):
    """Write task result to recovery file when DB is unavailable."""
    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
    recovery_file = RECOVERY_DIR / f"{task_id}.json"
    recovery_file.write_text(json.dumps({
        "task_id": task_id,
        "result": result,
        "timestamp": datetime.utcnow().isoformat(),
    }))

async def process_recovery_files(client: AbsurdClient):
    """Process any pending recovery files on startup."""
    for recovery_file in RECOVERY_DIR.glob("*.json"):
        try:
            data = json.loads(recovery_file.read_text())
            await client.complete_task(data["task_id"], data["result"])
            recovery_file.unlink()
            logger.info(f"Recovered task {data['task_id']}")
        except Exception as e:
            logger.error(f"Failed to recover {recovery_file}: {e}")
```

### 3. Duplicate Task Submission

**Scenario:** User or API submits the same task twice (network retry, UI double-click).

**Current Behavior:**

- Two identical tasks are created
- Both may execute, wasting resources
- Results may conflict or overwrite each other

**Required Handling:**

Option A - Idempotency Key:

```sql
-- Add idempotency_key column
ALTER TABLE absurd.tasks ADD COLUMN idempotency_key TEXT;
CREATE UNIQUE INDEX idx_tasks_idempotency
    ON absurd.tasks(queue_name, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
```

```python
async def spawn_task_idempotent(
    self,
    queue_name: str,
    task_name: str,
    params: Dict[str, Any],
    idempotency_key: str,
    **kwargs
) -> Tuple[UUID, bool]:
    """Spawn task with idempotency guarantee.

    Returns:
        (task_id, created) - created=False if task already exists
    """
    async with self._pool.acquire() as conn:
        # Check for existing task
        existing = await conn.fetchrow("""
            SELECT task_id FROM absurd.tasks
            WHERE queue_name = $1 AND idempotency_key = $2
        """, queue_name, idempotency_key)

        if existing:
            return existing["task_id"], False

        # Create new task
        task_id = await self.spawn_task(queue_name, task_name, params, **kwargs)

        # Set idempotency key
        await conn.execute("""
            UPDATE absurd.tasks SET idempotency_key = $2 WHERE task_id = $1
        """, task_id, idempotency_key)

        return task_id, True
```

Option B - Content-based deduplication:

```python
import hashlib

def compute_task_hash(task_name: str, params: dict) -> str:
    """Compute hash of task content for deduplication."""
    content = json.dumps({"task_name": task_name, "params": params}, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]

async def spawn_task_dedupe(self, queue_name: str, task_name: str, params: dict, window_hours: int = 24):
    """Spawn task with content-based deduplication."""
    content_hash = compute_task_hash(task_name, params)

    async with self._pool.acquire() as conn:
        # Check for recent identical task
        existing = await conn.fetchrow("""
            SELECT task_id, status FROM absurd.tasks
            WHERE queue_name = $1
              AND idempotency_key = $2
              AND created_at > NOW() - INTERVAL '%s hours'
              AND status NOT IN ('failed', 'cancelled')
        """, queue_name, content_hash, window_hours)

        if existing:
            logger.info(f"Deduplicated task, returning existing {existing['task_id']}")
            return existing["task_id"], False

        task_id = await self.spawn_task(queue_name, task_name, params)
        await conn.execute("""
            UPDATE absurd.tasks SET idempotency_key = $2 WHERE task_id = $1
        """, task_id, content_hash)

        return task_id, True
```

### 4. Task Timeout

**Scenario:** Task runs longer than allowed timeout (imaging stuck, infinite loop).

**Current Behavior:**

- Worker heartbeat continues
- Task runs indefinitely
- No automatic termination

**Required Handling:**

```python
# In worker.py
async def _process_task(self, task: Dict[str, Any]):
    task_id = task["task_id"]
    timeout_sec = task.get("timeout_sec") or self.config.default_timeout_sec

    try:
        # Execute with timeout
        result = await asyncio.wait_for(
            self.executor(task["task_name"], task["params"]),
            timeout=timeout_sec
        )
        await self.client.complete_task(task_id, result)

    except asyncio.TimeoutError:
        error_msg = f"Task timed out after {timeout_sec} seconds"
        logger.error(f"Task {task_id}: {error_msg}")
        await self._handle_failure(task, error_msg)
```

**Database-level enforcement (reaper checks):**

```sql
-- Find and fail timed-out tasks
UPDATE absurd.tasks
SET status = 'failed',
    error = 'Task timed out',
    completed_at = NOW()
WHERE status = 'claimed'
  AND timeout_sec IS NOT NULL
  AND claimed_at + (timeout_sec || ' seconds')::INTERVAL < NOW();
```

### 5. Partial Pipeline Failure

**Scenario:** Workflow with dependencies - early stage fails, downstream stages waiting.

**Current Behavior:**

- Downstream tasks remain in `pending` forever
- No cascade cancellation
- Users must manually cancel orphaned tasks

**Required Handling:**

```python
# backend/src/dsa110_contimg/absurd/dependencies.py

async def cancel_downstream_tasks(client: AbsurdClient, failed_task_id: UUID):
    """Cancel all tasks that depend on a failed task."""
    async with client._pool.acquire() as conn:
        # Find tasks that depend on the failed task
        dependent_tasks = await conn.fetch("""
            SELECT task_id FROM absurd.tasks
            WHERE params->>'depends_on' = $1
              AND status = 'pending'
        """, str(failed_task_id))

        cancelled = []
        for row in dependent_tasks:
            await conn.execute("""
                UPDATE absurd.tasks
                SET status = 'cancelled',
                    error = 'Cancelled: upstream task %s failed',
                    completed_at = NOW()
                WHERE task_id = $1
            """, row["task_id"], str(failed_task_id))
            cancelled.append(row["task_id"])

            # Recursively cancel downstream
            cancelled.extend(
                await cancel_downstream_tasks(client, row["task_id"])
            )

        return cancelled
```

**Usage in worker:**

```python
async def _handle_failure(self, task: Dict[str, Any], error_msg: str):
    task_id = task["task_id"]
    await self.client.fail_task(task_id, error_msg)

    # Cancel downstream tasks
    cancelled = await cancel_downstream_tasks(self.client, UUID(task_id))
    if cancelled:
        logger.warning(f"Cancelled {len(cancelled)} downstream tasks after {task_id} failed")
```

### 6. Queue Overflow / Backpressure

**Scenario:** Tasks are submitted faster than workers can process them.

**Symptoms:**

- Pending queue grows unbounded
- Wait times increase dramatically
- Memory pressure on PostgreSQL

**Required Handling:**

```python
# backend/src/dsa110_contimg/absurd/backpressure.py

MAX_PENDING_TASKS = 1000  # Per queue

async def check_queue_capacity(client: AbsurdClient, queue_name: str) -> bool:
    """Check if queue can accept more tasks."""
    async with client._pool.acquire() as conn:
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM absurd.tasks
            WHERE queue_name = $1 AND status = 'pending'
        """, queue_name)
        return count < MAX_PENDING_TASKS

async def spawn_task_with_backpressure(
    client: AbsurdClient,
    queue_name: str,
    task_name: str,
    params: dict,
    max_wait_sec: int = 60
) -> UUID:
    """Spawn task with backpressure - waits or rejects if queue full."""
    start = time.time()

    while time.time() - start < max_wait_sec:
        if await check_queue_capacity(client, queue_name):
            return await client.spawn_task(queue_name, task_name, params)
        await asyncio.sleep(1.0)

    raise QueueFullError(f"Queue {queue_name} at capacity, try again later")
```

**API-level handling:**

```python
# In FastAPI router
@router.post("/tasks")
async def create_task(request: TaskCreateRequest):
    try:
        task_id = await spawn_task_with_backpressure(
            client, request.queue_name, request.task_name, request.params
        )
        return {"task_id": str(task_id)}
    except QueueFullError as e:
        raise HTTPException(status_code=503, detail=str(e))
```

### 7. Worker Scaling Issues

**Scenario:** Single worker is bottleneck; need to scale horizontally.

**Considerations:**

- Each worker needs unique `worker_id`
- `FOR UPDATE SKIP LOCKED` ensures no double-claiming
- Some tasks may not be parallelizable (file locks, GPU)

**Configuration for multi-worker:**

```bash
# ops/systemd/contimg-absurd-worker@.service (template unit)
[Unit]
Description=ABSURD Worker %i
After=network.target postgresql.service

[Service]
Type=simple
User=dsa110
Environment=WORKER_ID=worker-%i
EnvironmentFile=/data/dsa110-contimg/ops/systemd/contimg.env
ExecStart=/opt/conda/envs/casa6/bin/python -m dsa110_contimg.absurd.worker
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Start 4 worker instances
sudo systemctl enable contimg-absurd-worker@{1..4}
sudo systemctl start contimg-absurd-worker@{1..4}
```

**Task affinity for non-parallelizable tasks:**

```python
# Force certain tasks to specific worker
EXCLUSIVE_TASKS = {"imaging", "calibration-solve"}

async def claim_task_with_affinity(
    client: AbsurdClient, queue_name: str, worker_id: str
) -> Optional[Dict]:
    """Claim task with exclusive task handling."""
    # First try to claim exclusive tasks only on worker-1
    if worker_id == "worker-1":
        task = await client.claim_task_by_name(queue_name, worker_id, list(EXCLUSIVE_TASKS))
        if task:
            return task

    # All workers can claim non-exclusive tasks
    return await client.claim_task_excluding(queue_name, worker_id, list(EXCLUSIVE_TASKS))
```

### 8. Frontend Polling During ABSURD Outage

**Scenario:** ABSURD backend is down but frontend keeps polling.

**Current Behavior:**

- Frontend shows loading state indefinitely
- Network requests fail repeatedly
- No feedback to user

**Required Handling:**

Already implemented in `PipelineStatusPanel`:

```typescript
// placeholderData provides fallback during errors
const { data, isError, refetch } = useQuery({
  queryKey: ["absurd", "status"],
  queryFn: fetchPipelineStatus,
  retry: 2,
  placeholderData: {
    stages: EMPTY_STAGES,
    total: EMPTY_COUNTS,
    worker_count: 0,
    is_healthy: false,
  },
});

// Error state shown to user
if (isError) {
  return (
    <div className="card p-4">
      <p>Unable to load pipeline status</p>
      <p>ABSURD workflow manager may not be enabled yet</p>
      <button onClick={() => refetch()}>Retry</button>
    </div>
  );
}
```

**Additional improvement - exponential backoff:**

```typescript
// hooks/usePipelineStatus.ts
export function usePipelineStatus(pollInterval = 30000) {
  const [backoffMultiplier, setBackoffMultiplier] = useState(1);

  const query = useQuery({
    queryKey: ["absurd", "status"],
    queryFn: fetchPipelineStatus,
    refetchInterval: pollInterval * backoffMultiplier,
    retry: 2,
    onError: () => {
      // Increase backoff on error (max 5x)
      setBackoffMultiplier((prev) => Math.min(prev * 2, 5));
    },
    onSuccess: () => {
      // Reset backoff on success
      setBackoffMultiplier(1);
    },
  });

  return query;
}
```

### 9. Task Parameter Validation

**Scenario:** Invalid parameters submitted (missing required fields, wrong types).

**Current Behavior:**

- Task is created and claimed
- Executor fails immediately with validation error
- Wastes worker cycle

**Required Handling:**

```python
# backend/src/dsa110_contimg/absurd/validation.py
from pydantic import BaseModel, ValidationError
from typing import Dict, Any, Type

TASK_SCHEMAS: Dict[str, Type[BaseModel]] = {
    "convert-uvh5-to-ms": ConvertUvh5Params,
    "calibration-solve": CalibrationSolveParams,
    "calibration-apply": CalibrationApplyParams,
    "imaging": ImagingParams,
    # ... etc
}

class ConvertUvh5Params(BaseModel):
    input_dir: str
    output_dir: str
    start_time: str
    end_time: str

class ImagingParams(BaseModel):
    ms_path: str
    output_dir: str
    imager: str = "wsclean"
    niter: int = 50000

async def validate_task_params(task_name: str, params: dict) -> list[str]:
    """Validate task parameters before spawning."""
    schema = TASK_SCHEMAS.get(task_name)
    if not schema:
        return []  # No validation for unknown tasks

    try:
        schema(**params)
        return []
    except ValidationError as e:
        return [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
```

**API-level validation:**

```python
@router.post("/tasks")
async def create_task(request: TaskCreateRequest):
    errors = await validate_task_params(request.task_name, request.params)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_PARAMS", "errors": errors}
        )

    task_id = await client.spawn_task(
        request.queue_name, request.task_name, request.params
    )
    return {"task_id": str(task_id)}
```

### 10. Clock Skew Between Workers

**Scenario:** Workers on different machines have unsynchronized clocks.

**Impact:**

- Task timing metrics are incorrect
- Timeout calculations may be wrong
- Reaper may incorrectly reclaim active tasks

**Required Handling:**

```bash
# Ensure NTP is running on all machines
sudo systemctl enable --now chronyd

# Verify sync status
chronyc tracking
```

**Database-side mitigation (use database time):**

```sql
-- Always use NOW() in database functions, not client timestamps
-- The claim_task function already does this correctly:
UPDATE absurd.tasks
SET claimed_at = NOW()  -- Database time, not client time
WHERE ...
```

### Summary Table

| Edge Case                | Severity | Current State      | Required Action      |
| ------------------------ | -------- | ------------------ | -------------------- |
| Worker crash mid-task    | High     | Task stuck         | Add reaper job       |
| DB connection lost       | High     | Task may be lost   | Add recovery files   |
| Duplicate submission     | Medium   | Duplicates created | Add idempotency keys |
| Task timeout             | Medium   | Runs forever       | Add asyncio.timeout  |
| Partial pipeline failure | Medium   | Orphaned tasks     | Cascade cancellation |
| Queue overflow           | Medium   | Unbounded growth   | Add backpressure     |
| Worker scaling           | Low      | Single worker      | Template units       |
| Frontend polling outage  | Low      | Loading forever    | Already handled      |
| Invalid parameters       | Low      | Fails at execution | Pre-validate         |
| Clock skew               | Low      | Incorrect metrics  | Use DB time, NTP     |

---## Troubleshooting

### Common Issues

#### 1. Worker Not Starting

**Symptom:** `systemctl status contimg-absurd-worker` shows failed

**Check:**

```bash
# View full logs
journalctl -u contimg-absurd-worker -n 100 --no-pager

# Common causes:
# - Missing ABSURD_DATABASE_URL
# - PostgreSQL not running
# - asyncpg not installed
# - Import errors in adapter.py
```

**Fix:**

```bash
# Verify environment
cat /data/dsa110-contimg/ops/systemd/contimg.env | grep ABSURD

# Test connection manually
python -c "
import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect('postgresql://postgres@localhost/dsa110_absurd')
    print('Connected!')
    await conn.close()

asyncio.run(test())
"
```

#### 2. Tasks Stuck in "pending"

**Symptom:** Tasks never transition to "claimed"

**Check:**

```bash
# Is worker running?
systemctl status contimg-absurd-worker

# Is worker polling the correct queue?
journalctl -u contimg-absurd-worker | grep "queue"

# Check queue name matches
grep ABSURD_QUEUE_NAME /data/dsa110-contimg/ops/systemd/contimg.env
```

**Fix:**

```bash
# Ensure queue names match
export ABSURD_QUEUE_NAME=dsa110-pipeline
sudo systemctl restart contimg-absurd-worker
```

#### 3. Tasks Failing Immediately

**Symptom:** Tasks go directly to "failed" status

**Check:**

```bash
# Get error message
psql dsa110_absurd -c "
  SELECT task_id, task_name, error
  FROM absurd.tasks
  WHERE status = 'failed'
  ORDER BY completed_at DESC
  LIMIT 5;
"
```

**Common causes:**

- Missing input files
- Invalid parameters
- Pipeline stage errors
- CASA not available

#### 4. Database Connection Errors

**Symptom:** `asyncpg.exceptions.ConnectionDoesNotExistError`

**Check:**

```bash
# PostgreSQL running?
systemctl status postgresql

# Database exists?
psql -l | grep dsa110_absurd

# Schema exists?
psql dsa110_absurd -c "\dt absurd.*"
```

**Fix:**

```bash
# Recreate database if needed
dropdb dsa110_absurd
createdb dsa110_absurd
psql dsa110_absurd < backend/src/dsa110_contimg/absurd/schema.sql
```

#### 5. API Returns 503 Service Unavailable

**Symptom:** `/absurd/health` returns error

**Check:**

```bash
# Is ABSURD enabled?
curl http://localhost:8000/absurd/health

# If disabled, enable it:
export ABSURD_ENABLED=true
sudo systemctl restart contimg-api
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Set log level
export LOG_LEVEL=DEBUG

# Or in Python
import logging
logging.getLogger('dsa110_contimg.absurd').setLevel(logging.DEBUG)
```

### Database Queries for Debugging

```sql
-- Task counts by status
SELECT status, COUNT(*)
FROM absurd.tasks
GROUP BY status;

-- Recent failed tasks
SELECT task_id, task_name, error, completed_at
FROM absurd.tasks
WHERE status = 'failed'
ORDER BY completed_at DESC
LIMIT 10;

-- Long-running tasks
SELECT task_id, task_name,
       EXTRACT(EPOCH FROM (NOW() - claimed_at)) as running_seconds
FROM absurd.tasks
WHERE status = 'claimed'
ORDER BY claimed_at;

-- Task timing statistics
SELECT task_name,
       COUNT(*) as count,
       AVG(execution_time_sec) as avg_time,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_sec) as p95_time
FROM absurd.tasks
WHERE status = 'completed'
  AND completed_at > NOW() - INTERVAL '24 hours'
GROUP BY task_name;

-- Dead letter queue tasks
SELECT task_id, task_name, attempt, error, created_at
FROM absurd.tasks
WHERE queue_name LIKE '%-dlq'
ORDER BY created_at DESC;
```

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

## Quick Reference Commands

### Service Management

```bash
# API server
sudo systemctl start|stop|restart|status contimg-api

# ABSURD worker
sudo systemctl start|stop|restart|status contimg-absurd-worker

# View logs
journalctl -u contimg-absurd-worker -f
journalctl -u contimg-api -f
```

### Database Operations

```bash
# Connect to database
psql dsa110_absurd

# Quick stats
psql dsa110_absurd -c "SELECT * FROM absurd.get_queue_stats('dsa110-pipeline');"

# Clear all tasks (DANGER - use only in dev)
psql dsa110_absurd -c "TRUNCATE absurd.tasks;"
```

### API Testing

```bash
# Health check
curl http://localhost:8000/absurd/health

# Spawn task
curl -X POST http://localhost:8000/absurd/tasks \
  -H "Content-Type: application/json" \
  -d '{"task_name": "validation", "params": {}}'

# List pending tasks
curl "http://localhost:8000/absurd/tasks?status=pending"

# Get queue stats
curl http://localhost:8000/absurd/queues/dsa110-pipeline/stats

# Cancel task
curl -X DELETE http://localhost:8000/absurd/tasks/{task_id}
```

---

## References

- Legacy implementation: `legacy.backend/src/dsa110_contimg/absurd/`
- Status docs: `.local/internal/docs/dev/status/2025-11/absurd_*.md`
- Operations guide: `legacy.backend/docs/operations/absurd_operations_guide.md`
- Executor roadmap: `.local/internal/docs/dev/status/2025-11/absurd_executor_roadmap.md`
- Integration summary: `.local/internal/docs/dev/status/2025-11/absurd_integration_summary.md`

---

## Appendix A: Pre-Flight Checklist

Before beginning deployment, verify all prerequisites are met:

### Environment Verification

```bash
#!/bin/bash
# Pre-flight checklist script
# Save as: scripts/absurd/preflight_check.sh

set -e
echo "=== ABSURD Deployment Pre-Flight Checklist ==="
echo ""

# 1. Verify conda environment
echo "1. Checking conda environment..."
if conda info --envs | grep -q "casa6"; then
    echo "   ✅ casa6 environment exists"
else
    echo "   ❌ casa6 environment NOT FOUND"
    exit 1
fi

# 2. Verify legacy files exist
echo "2. Checking legacy source files..."
LEGACY_DIR="/data/dsa110-contimg/legacy.backend/src/dsa110_contimg/absurd"
REQUIRED_FILES="config.py client.py worker.py schema.sql adapter.py"
for f in $REQUIRED_FILES; do
    if [[ -f "$LEGACY_DIR/$f" ]]; then
        echo "   ✅ $f exists"
    else
        echo "   ❌ $f MISSING"
        exit 1
    fi
done

# 3. Verify legacy router exists
echo "3. Checking legacy router..."
ROUTER="/data/dsa110-contimg/legacy.backend/src/dsa110_contimg/api/routers/absurd.py"
if [[ -f "$ROUTER" ]]; then
    echo "   ✅ absurd.py router exists ($(wc -l < "$ROUTER") lines)"
else
    echo "   ❌ absurd.py router MISSING"
    exit 1
fi

# 4. Verify PostgreSQL is running
echo "4. Checking PostgreSQL..."
if pg_isready -h localhost -q; then
    echo "   ✅ PostgreSQL is running"
else
    echo "   ❌ PostgreSQL is NOT running"
    exit 1
fi

# 5. Verify asyncpg is installed
echo "5. Checking Python dependencies..."
conda activate casa6
if python -c "import asyncpg" 2>/dev/null; then
    echo "   ✅ asyncpg is installed"
else
    echo "   ⚠️  asyncpg NOT installed (will be installed during deployment)"
fi

# 6. Verify frontend dependencies
echo "6. Checking frontend dependencies..."
if grep -q "@tanstack/react-query" /data/dsa110-contimg/frontend/package.json; then
    echo "   ✅ @tanstack/react-query is installed"
else
    echo "   ❌ @tanstack/react-query NOT installed"
    exit 1
fi

# 7. Check disk space
echo "7. Checking disk space..."
AVAILABLE=$(df -BG /data | tail -1 | awk '{print $4}' | tr -d 'G')
if [[ $AVAILABLE -gt 10 ]]; then
    echo "   ✅ ${AVAILABLE}GB available on /data"
else
    echo "   ⚠️  Only ${AVAILABLE}GB available (recommend >10GB)"
fi

# 8. Check for existing ABSURD database
echo "8. Checking for existing database..."
if psql -lqt | cut -d \| -f 1 | grep -qw dsa110_absurd; then
    echo "   ⚠️  dsa110_absurd database already exists"
    echo "      Consider backing up before proceeding"
else
    echo "   ✅ dsa110_absurd database does not exist (will be created)"
fi

echo ""
echo "=== Pre-Flight Check Complete ==="
echo "Run the deployment when all checks pass."
```

### Database Backup (Before Migration)

**IMPORTANT:** Always backup existing databases before schema changes.

```bash
# Backup existing ABSURD database (if exists)
if psql -lqt | cut -d \| -f 1 | grep -qw dsa110_absurd; then
    BACKUP_FILE="/data/dsa110-contimg/state/backups/absurd_$(date +%Y%m%d_%H%M%S).sql"
    mkdir -p /data/dsa110-contimg/state/backups
    pg_dump dsa110_absurd > "$BACKUP_FILE"
    gzip "$BACKUP_FILE"
    echo "Backup saved to: ${BACKUP_FILE}.gz"
fi

# Backup main pipeline database
pg_dump dsa110_contimg > "/data/dsa110-contimg/state/backups/contimg_$(date +%Y%m%d_%H%M%S).sql"
```

---

## Appendix B: Rollback Procedures

If deployment fails or issues are discovered, follow these rollback procedures.

### Quick Rollback (Services Only)

```bash
#!/bin/bash
# Rollback script - services only (keeps data)
# Save as: scripts/absurd/rollback_services.sh

set -e
echo "=== ABSURD Service Rollback ==="

# 1. Stop ABSURD services
echo "Stopping ABSURD services..."
sudo systemctl stop contimg-absurd-worker 2>/dev/null || true
sudo systemctl disable contimg-absurd-worker 2>/dev/null || true

# 2. Remove router from API (manual step)
echo "Manual step required:"
echo "  - Remove 'absurd' router from backend/src/dsa110_contimg/api/app.py"
echo "  - Remove absurd import from routers/__init__.py"

# 3. Disable ABSURD in environment
sed -i 's/ABSURD_ENABLED=true/ABSURD_ENABLED=false/' \
    /data/dsa110-contimg/ops/systemd/contimg.env

# 4. Restart API without ABSURD
sudo systemctl restart contimg-api

echo "=== Rollback Complete (Services) ==="
echo "Database preserved. Frontend routes may need manual removal."
```

### Full Rollback (Including Database)

```bash
#!/bin/bash
# Full rollback script - removes all ABSURD components
# Save as: scripts/absurd/rollback_full.sh

set -e
echo "=== ABSURD Full Rollback ==="
echo "WARNING: This will delete the ABSURD database!"
read -p "Continue? (y/N): " confirm
[[ "$confirm" != "y" ]] && exit 1

# 1. Stop services
echo "Stopping services..."
sudo systemctl stop contimg-absurd-worker 2>/dev/null || true
sudo systemctl disable contimg-absurd-worker 2>/dev/null || true

# 2. Backup database before deletion
BACKUP_FILE="/data/dsa110-contimg/state/backups/absurd_rollback_$(date +%Y%m%d_%H%M%S).sql"
pg_dump dsa110_absurd > "$BACKUP_FILE" 2>/dev/null || true

# 3. Drop database
echo "Dropping database..."
dropdb dsa110_absurd 2>/dev/null || true

# 4. Remove backend module
echo "Removing backend module..."
rm -rf /data/dsa110-contimg/backend/src/dsa110_contimg/absurd/
rm -f /data/dsa110-contimg/backend/src/dsa110_contimg/api/routers/absurd.py

# 5. Remove systemd service
echo "Removing systemd service..."
sudo rm -f /etc/systemd/system/contimg-absurd-worker.service
sudo systemctl daemon-reload

# 6. Disable in environment
sed -i 's/ABSURD_ENABLED=true/ABSURD_ENABLED=false/' \
    /data/dsa110-contimg/ops/systemd/contimg.env

# 7. Clean up recovery files
rm -rf /data/dsa110-contimg/state/absurd_recovery/

echo "=== Full Rollback Complete ==="
echo "Backup saved to: $BACKUP_FILE"
echo ""
echo "Manual steps remaining:"
echo "  1. Remove WorkflowsPage from frontend/src/pages/"
echo "  2. Remove /workflows route from frontend/src/router.tsx"
echo "  3. Remove Workflows link from Sidebar.tsx"
echo "  4. Run: cd frontend && npm run build:scratch"
```

### Restore from Backup

```bash
#!/bin/bash
# Restore ABSURD database from backup
# Usage: ./restore_absurd.sh <backup_file.sql.gz>

BACKUP_FILE="$1"
if [[ -z "$BACKUP_FILE" ]]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Available backups:"
    ls -la /data/dsa110-contimg/state/backups/absurd_*.sql.gz 2>/dev/null
    exit 1
fi

# Drop existing database
dropdb dsa110_absurd 2>/dev/null || true

# Create fresh database
createdb dsa110_absurd

# Restore from backup
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | psql dsa110_absurd
else
    psql dsa110_absurd < "$BACKUP_FILE"
fi

echo "Database restored from: $BACKUP_FILE"
```

---

## Appendix C: Recovery File Cleanup

The recovery file mechanism (`/data/dsa110-contimg/state/absurd_recovery/`) stores
task results when the database is unavailable. These files need periodic cleanup.

### Automatic Cleanup (Recommended)

Add a systemd timer for daily cleanup:

**File:** `ops/systemd/absurd-cleanup.service`

```ini
[Unit]
Description=ABSURD Recovery File Cleanup
After=network.target

[Service]
Type=oneshot
User=dsa110
ExecStart=/bin/bash -c '\
    RECOVERY_DIR=/data/dsa110-contimg/state/absurd_recovery && \
    if [[ -d "$RECOVERY_DIR" ]]; then \
        find "$RECOVERY_DIR" -name "*.json" -mtime +7 -delete && \
        find "$RECOVERY_DIR" -name "*.json" -mtime +1 -exec \
            python -m dsa110_contimg.absurd.recovery process {} \; \
    fi'
```

**File:** `ops/systemd/absurd-cleanup.timer`

```ini
[Unit]
Description=Daily ABSURD Recovery Cleanup

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable the timer:

```bash
sudo cp ops/systemd/absurd-cleanup.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now absurd-cleanup.timer
```

### Manual Cleanup

```bash
# View recovery files
ls -la /data/dsa110-contimg/state/absurd_recovery/

# Process pending recovery files (re-attempt DB writes)
conda activate casa6
python -m dsa110_contimg.absurd.recovery process_all

# Remove old recovery files (>7 days)
find /data/dsa110-contimg/state/absurd_recovery -name "*.json" -mtime +7 -delete
```

### Recovery File Monitoring

Add to Prometheus alerting:

```yaml
- alert: AbsurdRecoveryFilesAccumulating
  expr: |
    count(node_directory_files{directory="/data/dsa110-contimg/state/absurd_recovery"}) > 10
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "Recovery files accumulating"
    description: "{{ $value }} recovery files pending - check database connectivity"
```

---

## Appendix D: Worker Scaling Guidelines

### Recommended Worker Limits

| Host Resources | Max Workers | Concurrency/Worker | Total Concurrent |
| -------------- | ----------- | ------------------ | ---------------- |
| 8 cores, 32GB  | 2           | 2                  | 4 tasks          |
| 16 cores, 64GB | 4           | 4                  | 16 tasks         |
| 32 cores, 128GB| 6           | 4                  | 24 tasks         |

### Memory Considerations

Each task type has different memory requirements:

| Task Type           | Typical Memory | Peak Memory | Notes                    |
| ------------------- | -------------- | ----------- | ------------------------ |
| `convert-uvh5-to-ms`| 4-8 GB         | 12 GB       | 16 subbands combined     |
| `calibration-solve` | 2-4 GB         | 6 GB        | Depends on MS size       |
| `calibration-apply` | 2-4 GB         | 6 GB        | Similar to solve         |
| `imaging`           | 8-32 GB        | 64 GB       | WSClean can use all RAM  |
| `validation`        | 1-2 GB         | 4 GB        | Lightweight              |
| `crossmatch`        | 2-4 GB         | 8 GB        | Catalog size dependent   |

**Formula for max workers:**

```
max_workers = floor(available_memory / peak_memory_per_task)
```

For a 64GB host running primarily imaging tasks:
```
max_workers = floor(64 / 32) = 2 workers with concurrency 1
# OR
max_workers = floor(64 / 8) = 8 workers for lighter tasks
```

### Multi-Worker Deployment

Use systemd template units for scaling:

```bash
# Enable 4 worker instances
sudo systemctl enable contimg-absurd-worker@{1..4}
sudo systemctl start contimg-absurd-worker@{1..4}

# Check status of all workers
systemctl list-units 'contimg-absurd-worker@*'

# View logs for specific worker
journalctl -u contimg-absurd-worker@2 -f
```

### Task Affinity Configuration

For tasks that shouldn't run in parallel (e.g., imaging using all GPUs):

```python
# In worker configuration
EXCLUSIVE_TASK_TYPES = {"imaging", "create-mosaic"}

# Only worker-1 handles exclusive tasks
if worker_id == "worker-1":
    task = await claim_task(include_types=EXCLUSIVE_TASK_TYPES)
else:
    task = await claim_task(exclude_types=EXCLUSIVE_TASK_TYPES)
```

---

## Appendix E: Health Check Integration

### Liveness and Readiness Probes

Add health check endpoint for Kubernetes/systemd:

**Backend health check** (already in router):

```bash
# Liveness - is the worker process alive?
curl -f http://localhost:8000/absurd/health

# Readiness - can the worker accept tasks?
curl -f http://localhost:8000/absurd/health | jq -e '.status == "ok"'
```

### Systemd Health Check

Update the worker service to include health monitoring:

```ini
# In contimg-absurd-worker.service [Service] section
ExecStartPre=/bin/bash -c 'pg_isready -h localhost -q'
WatchdogSec=60
NotifyAccess=all
```

Add watchdog notification to worker:

```python
# In worker.py main loop
import sdnotify

notifier = sdnotify.SystemdNotifier()

async def main_loop():
    while True:
        task = await claim_task()
        if task:
            await process_task(task)
        notifier.notify("WATCHDOG=1")  # Heartbeat to systemd
```

### Frontend Health Display

The `PipelineStatusPanel` already handles ABSURD availability gracefully with
placeholder data during outages and retry functionality.

---

## Appendix F: Revised Timeline Estimate

Based on complexity analysis and buffer for testing:

| Phase                | Optimistic | Realistic | Pessimistic | Notes                          |
| -------------------- | ---------- | --------- | ----------- | ------------------------------ |
| Pre-flight & Backup  | 0.5 day    | 1 day     | 1 day       | Run checklist, backup DBs      |
| Phase 1: Backend     | 1 day      | 2 days    | 3 days      | Migration + testing            |
| Phase 2: Frontend    | 2 days     | 3 days    | 4 days      | Components + integration       |
| Phase 3: Worker      | 1 day      | 1.5 days  | 2 days      | Systemd + initial testing      |
| Phase 4: Testing     | 2 days     | 3 days    | 5 days      | E2E + load testing             |
| Buffer               | 0 days     | 1 day     | 2 days      | Unexpected issues              |
| **Total**            | **6.5 days** | **11.5 days** | **17 days** |                          |

**Recommendation:** Plan for 10-14 business days with a 2-week target.

