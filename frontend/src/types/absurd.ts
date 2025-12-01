/**
 * ABSURD Workflow Manager API Types.
 *
 * TypeScript interfaces for the ABSURD durable task queue system.
 */

// =============================================================================
// Task Types
// =============================================================================

/**
 * Task status values.
 */
export type TaskStatus =
  | "pending"
  | "claimed"
  | "completed"
  | "failed"
  | "cancelled"
  | "retrying";

/**
 * Task details response from API.
 */
export interface Task {
  task_id: string;
  queue_name: string;
  task_name: string;
  params: Record<string, unknown>;
  priority: number;
  status: TaskStatus;
  created_at: string | null;
  claimed_at: string | null;
  completed_at: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  retry_count: number;
}

/**
 * Paginated list of tasks.
 */
export interface TaskListResponse {
  tasks: Task[];
  total: number;
}

// =============================================================================
// Queue Types
// =============================================================================

/**
 * Queue statistics response.
 */
export interface QueueStats {
  queue_name: string;
  pending: number;
  claimed: number;
  completed: number;
  failed: number;
  cancelled: number;
  total: number;
}

// =============================================================================
// Worker Types
// =============================================================================

/**
 * Worker state values.
 */
export type WorkerState = "active" | "idle" | "stale" | "crashed";

/**
 * Worker information response.
 */
export interface Worker {
  worker_id: string;
  state: WorkerState;
  task_count: number;
  current_task_id: string | null;
  first_seen: string | null;
  last_seen: string | null;
  uptime_seconds: number;
}

/**
 * List of workers response.
 */
export interface WorkerListResponse {
  workers: Worker[];
  total: number;
  active: number;
  idle: number;
  stale: number;
  crashed: number;
}

/**
 * Worker pool metrics.
 */
export interface WorkerMetrics {
  total_workers: number;
  active_workers: number;
  idle_workers: number;
  crashed_workers: number;
  timed_out_workers: number;
  avg_tasks_per_worker: number;
  avg_worker_uptime_sec: number;
}

// =============================================================================
// Metrics Types
// =============================================================================

/**
 * ABSURD system metrics response.
 */
export interface AbsurdMetrics {
  total_spawned: number;
  total_claimed: number;
  total_completed: number;
  total_failed: number;
  total_cancelled: number;
  total_timed_out: number;
  current_pending: number;
  current_claimed: number;
  avg_wait_time_sec: number;
  avg_execution_time_sec: number;
  p50_wait_time_sec: number;
  p95_wait_time_sec: number;
  p99_wait_time_sec: number;
  p50_execution_time_sec: number;
  p95_execution_time_sec: number;
  p99_execution_time_sec: number;
  throughput_1min: number;
  throughput_5min: number;
  throughput_15min: number;
  success_rate_1min: number;
  success_rate_5min: number;
  success_rate_15min: number;
  error_rate_1min: number;
  error_rate_5min: number;
  error_rate_15min: number;
}

// =============================================================================
// Alert Types
// =============================================================================

/**
 * Alert severity level.
 */
export type AlertLevel = "alert" | "warning";

/**
 * Alert information.
 */
export interface Alert {
  level: AlertLevel;
  message: string;
  timestamp: string | null;
}

// =============================================================================
// Health Types
// =============================================================================

/**
 * Health check response with alerts.
 */
export interface AbsurdHealth {
  status: "healthy" | "degraded" | "unhealthy";
  message: string;
  queue_depth: number;
  database_available: boolean;
  worker_pool_healthy: boolean;
  alerts: Alert[];
  warnings: Alert[];
}

// =============================================================================
// Workflow Types
// =============================================================================

/**
 * Workflow status values.
 */
export type WorkflowStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

/**
 * Workflow information.
 */
export interface Workflow {
  workflow_id: string;
  name: string;
  status: WorkflowStatus;
  task_count: number;
  completed_tasks: number;
  failed_tasks: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  metadata: Record<string, unknown>;
}

/**
 * Workflow task with dependency info.
 */
export interface WorkflowTask {
  task_id: string;
  task_name: string;
  status: TaskStatus;
  depends_on: string[];
  result: Record<string, unknown> | null;
  error: string | null;
}

/**
 * Workflow detail with tasks.
 */
export interface WorkflowDetail extends Workflow {
  tasks: WorkflowTask[];
  dag_edges: Array<[string, string]>;
}

// =============================================================================
// Request Types
// =============================================================================

/**
 * Request to spawn a new task.
 */
export interface SpawnTaskRequest {
  queue_name: string;
  task_name: string;
  params?: Record<string, unknown>;
  priority?: number;
  timeout_sec?: number;
}

/**
 * Request to spawn a workflow.
 */
export interface SpawnWorkflowRequest {
  name: string;
  tasks: Array<{
    task_name: string;
    params?: Record<string, unknown>;
    depends_on?: string[];
  }>;
  metadata?: Record<string, unknown>;
}

/**
 * Request to cancel a task.
 */
export interface CancelTaskRequest {
  reason?: string;
}
