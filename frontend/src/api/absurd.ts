/**
 * API client for Absurd workflow manager.
 *
 * Provides functions for spawning, querying, and managing Absurd tasks.
 */

import { apiClient } from "./client";

export interface SpawnTaskRequest {
  queue_name: string;
  task_name: string;
  params: Record<string, unknown>;
  priority?: number;
  timeout_sec?: number;
}

export interface TaskInfo {
  task_id: string;
  queue_name: string;
  task_name: string;
  params: Record<string, unknown>;
  priority: number;
  status: string;
  created_at: string | null;
  claimed_at: string | null;
  completed_at: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  retry_count: number;
}

export interface TaskListResponse {
  tasks: TaskInfo[];
  total: number;
}

export interface QueueStats {
  queue_name: string;
  pending: number;
  claimed: number;
  completed: number;
  failed: number;
  cancelled: number;
  total: number;
}

export interface HealthStatus {
  status: "healthy" | "disabled" | "error" | "degraded" | "critical" | "down";
  message: string;
  queue?: string;
}

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

export interface WorkerInfo {
  worker_id: string;
  state: "active" | "idle" | "stale" | "crashed";
  task_count: number;
  current_task_id: string | null;
  first_seen: string | null;
  last_seen: string | null;
  uptime_seconds: number;
}

export interface WorkerListResponse {
  workers: WorkerInfo[];
  total: number;
  active: number;
  idle: number;
  stale: number;
  crashed: number;
}

export interface WorkerMetrics {
  total_workers: number;
  active_workers: number;
  idle_workers: number;
  crashed_workers: number;
  timed_out_workers: number;
  avg_tasks_per_worker: number;
  avg_worker_uptime_sec: number;
}

export interface Alert {
  level: "alert" | "warning";
  message: string;
  timestamp: string | null;
}

export interface DetailedHealth {
  status: "healthy" | "degraded" | "critical" | "down" | "disabled" | "error";
  message: string;
  queue_depth: number;
  database_available: boolean;
  worker_pool_healthy: boolean;
  alerts: Alert[];
  warnings: Alert[];
}

/**
 * Spawn a new task in the Absurd queue.
 */
export async function spawnTask(request: SpawnTaskRequest): Promise<string> {
  const response = await apiClient.post<{ task_id: string }>("/absurd/tasks", request);
  return response.data.task_id;
}

/**
 * Get task details by ID.
 */
export async function getTask(taskId: string): Promise<TaskInfo> {
  const response = await apiClient.get<TaskInfo>(`/absurd/tasks/${taskId}`);
  return response.data;
}

/**
 * List tasks matching criteria.
 */
export async function listTasks(
  queueName?: string,
  status?: string,
  limit: number = 100
): Promise<TaskListResponse> {
  const params = new URLSearchParams();
  if (queueName) params.append("queue_name", queueName);
  if (status) params.append("status", status);
  params.append("limit", limit.toString());

  const response = await apiClient.get<TaskListResponse>(`/absurd/tasks?${params.toString()}`);
  return response.data;
}

/**
 * Cancel a pending task.
 */
export async function cancelTask(taskId: string): Promise<void> {
  await apiClient.delete(`/absurd/tasks/${taskId}`);
}

/**
 * Get queue statistics.
 */
export async function getQueueStats(queueName: string): Promise<QueueStats> {
  const response = await apiClient.get<QueueStats>(`/absurd/queues/${queueName}/stats`);
  return response.data;
}

/**
 * Check Absurd health status.
 */
export async function getHealthStatus(): Promise<HealthStatus> {
  const response = await apiClient.get<HealthStatus>("/absurd/health");
  return response.data;
}

/**
 * Get real-time metrics for Absurd workflow manager.
 */
export async function getMetrics(): Promise<AbsurdMetrics> {
  const response = await apiClient.get<AbsurdMetrics>("/absurd/metrics");
  return response.data;
}

/**
 * Get detailed health status with alerts and warnings.
 */
export async function getDetailedHealth(): Promise<DetailedHealth> {
  const response = await apiClient.get<DetailedHealth>("/absurd/health/detailed");
  return response.data;
}

/**
 * Get list of all registered workers.
 */
export async function listWorkers(): Promise<WorkerListResponse> {
  const response = await apiClient.get<WorkerListResponse>("/absurd/workers");
  return response.data;
}

/**
 * Get worker pool metrics.
 */
export async function getWorkerMetrics(): Promise<WorkerMetrics> {
  const response = await apiClient.get<WorkerMetrics>("/absurd/workers/metrics");
  return response.data;
}

/**
 * Send a worker heartbeat.
 */
export async function sendWorkerHeartbeat(workerId: string, taskId?: string): Promise<void> {
  const params = taskId ? `?task_id=${taskId}` : "";
  await apiClient.post(`/absurd/workers/${workerId}/heartbeat${params}`);
}

/**
 * List all available queues.
 */
export async function listQueues(): Promise<string[]> {
  const response = await apiClient.get<string[]>("/absurd/queues");
  return response.data;
}

/**
 * Get statistics for all queues.
 */
export async function getAllQueueStats(): Promise<QueueStats[]> {
  const response = await apiClient.get<QueueStats[]>("/absurd/queues/stats");
  return response.data;
}

// ============================================================================
// Workflow Templates
// ============================================================================

export interface WorkflowTemplateStep {
  task_name: string;
  params: Record<string, unknown>;
  priority: number;
  timeout_sec: number | null;
}

export interface WorkflowTemplate {
  name: string;
  description: string;
  queue_name: string;
  steps: WorkflowTemplateStep[];
  created_at: string | null;
  updated_at: string | null;
}

export interface WorkflowTemplateListResponse {
  templates: WorkflowTemplate[];
  total: number;
}

/**
 * List all workflow templates.
 */
export async function listWorkflowTemplates(): Promise<WorkflowTemplateListResponse> {
  const response = await apiClient.get<WorkflowTemplateListResponse>("/absurd/templates");
  return response.data;
}

/**
 * Get a specific workflow template.
 */
export async function getWorkflowTemplate(name: string): Promise<WorkflowTemplate> {
  const response = await apiClient.get<WorkflowTemplate>(`/absurd/templates/${name}`);
  return response.data;
}

/**
 * Create a new workflow template.
 */
export async function createWorkflowTemplate(
  template: Omit<WorkflowTemplate, "created_at" | "updated_at">
): Promise<WorkflowTemplate> {
  const response = await apiClient.post<WorkflowTemplate>("/absurd/templates", template);
  return response.data;
}

/**
 * Update an existing workflow template.
 */
export async function updateWorkflowTemplate(
  name: string,
  template: Omit<WorkflowTemplate, "created_at" | "updated_at">
): Promise<WorkflowTemplate> {
  const response = await apiClient.put<WorkflowTemplate>(`/absurd/templates/${name}`, template);
  return response.data;
}

/**
 * Delete a workflow template.
 */
export async function deleteWorkflowTemplate(name: string): Promise<void> {
  await apiClient.delete(`/absurd/templates/${name}`);
}

/**
 * Run a workflow template.
 */
export async function runWorkflowTemplate(
  name: string,
  paramsOverride?: Record<string, unknown>
): Promise<{ task_ids: string[]; template_name: string }> {
  const response = await apiClient.post<{ task_ids: string[]; template_name: string }>(
    `/absurd/templates/${name}/run`,
    paramsOverride || {}
  );
  return response.data;
}

// ============================================================================
// Scheduled Tasks
// ============================================================================

export interface ScheduledTask {
  schedule_id: string;
  name: string;
  queue_name: string;
  task_name: string;
  cron_expression: string;
  params: Record<string, unknown>;
  priority: number;
  timeout_sec: number | null;
  max_retries: number;
  state: "active" | "paused" | "disabled";
  timezone: string;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  description: string | null;
}

export interface ScheduleCreateRequest {
  name: string;
  queue_name?: string;
  task_name: string;
  cron_expression: string;
  params?: Record<string, unknown>;
  priority?: number;
  timeout_sec?: number;
  max_retries?: number;
  timezone?: string;
  description?: string;
}

export interface ScheduleUpdateRequest {
  cron_expression?: string;
  params?: Record<string, unknown>;
  state?: "active" | "paused" | "disabled";
  priority?: number;
  description?: string;
}

export interface ScheduleListResponse {
  schedules: ScheduledTask[];
  total: number;
}

/**
 * List all scheduled tasks.
 */
export async function listSchedules(
  queueName?: string,
  state?: string
): Promise<ScheduleListResponse> {
  const params = new URLSearchParams();
  if (queueName) params.append("queue_name", queueName);
  if (state) params.append("state", state);

  const response = await apiClient.get<ScheduleListResponse>(
    `/absurd/schedules?${params.toString()}`
  );
  return response.data;
}

/**
 * Get a specific scheduled task.
 */
export async function getSchedule(name: string): Promise<ScheduledTask> {
  const response = await apiClient.get<ScheduledTask>(`/absurd/schedules/${name}`);
  return response.data;
}

/**
 * Create a new scheduled task.
 */
export async function createSchedule(
  request: ScheduleCreateRequest
): Promise<{ schedule_id: string; name: string; next_run_at: string | null }> {
  const response = await apiClient.post<{
    schedule_id: string;
    name: string;
    next_run_at: string | null;
  }>("/absurd/schedules", request);
  return response.data;
}

/**
 * Update a scheduled task.
 */
export async function updateSchedule(
  name: string,
  request: ScheduleUpdateRequest
): Promise<{ schedule_id: string; name: string; state: string; next_run_at: string | null }> {
  const response = await apiClient.patch<{
    schedule_id: string;
    name: string;
    state: string;
    next_run_at: string | null;
  }>(`/absurd/schedules/${name}`, request);
  return response.data;
}

/**
 * Delete a scheduled task.
 */
export async function deleteSchedule(name: string): Promise<void> {
  await apiClient.delete(`/absurd/schedules/${name}`);
}

/**
 * Trigger a scheduled task immediately.
 */
export async function triggerSchedule(
  name: string
): Promise<{ task_id: string; schedule_name: string }> {
  const response = await apiClient.post<{ task_id: string; schedule_name: string }>(
    `/absurd/schedules/${name}/trigger`
  );
  return response.data;
}

// ============================================================================
// Workflow DAG (Directed Acyclic Graph)
// ============================================================================

export interface Workflow {
  workflow_id: string;
  name: string;
  description: string | null;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  created_at: string | null;
  completed_at: string | null;
}

export interface WorkflowStatus {
  workflow_id: string;
  name: string;
  description: string | null;
  status: string;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  tasks: {
    total: number;
    pending: number;
    running: number;
    completed: number;
    failed: number;
    blocked: number;
  };
  progress: number;
}

export interface DAGNode {
  task_id: string;
  task_name: string;
  status: string;
  depends_on: string[];
  dependents: string[];
  depth: number;
}

export interface WorkflowDAG {
  workflow_id: string;
  name: string;
  total_depth: number;
  root_tasks: string[];
  leaf_tasks: string[];
  nodes: DAGNode[];
}

export interface TaskWithDepsRequest {
  queue_name?: string;
  task_name: string;
  params?: Record<string, unknown>;
  depends_on?: string[];
  workflow_id?: string;
  priority?: number;
  timeout_sec?: number;
  max_retries?: number;
}

/**
 * List all workflows.
 */
export async function listWorkflows(
  status?: string,
  limit: number = 100
): Promise<{ workflows: Workflow[]; total: number }> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  params.append("limit", limit.toString());

  const response = await apiClient.get<{ workflows: Workflow[]; total: number }>(
    `/absurd/workflows?${params.toString()}`
  );
  return response.data;
}

/**
 * Create a new workflow.
 */
export async function createWorkflow(
  name: string,
  description?: string,
  metadata?: Record<string, unknown>
): Promise<{ workflow_id: string; name: string }> {
  const response = await apiClient.post<{ workflow_id: string; name: string }>(
    "/absurd/workflows",
    { name, description, metadata }
  );
  return response.data;
}

/**
 * Get workflow status.
 */
export async function getWorkflowStatus(workflowId: string): Promise<WorkflowStatus> {
  const response = await apiClient.get<WorkflowStatus>(`/absurd/workflows/${workflowId}`);
  return response.data;
}

/**
 * Get workflow DAG for visualization.
 */
export async function getWorkflowDAG(workflowId: string): Promise<WorkflowDAG> {
  const response = await apiClient.get<WorkflowDAG>(`/absurd/workflows/${workflowId}/dag`);
  return response.data;
}

/**
 * Get tasks that are ready to execute in a workflow.
 */
export async function getReadyTasks(
  workflowId: string
): Promise<{ workflow_id: string; ready_tasks: string[]; count: number }> {
  const response = await apiClient.get<{
    workflow_id: string;
    ready_tasks: string[];
    count: number;
  }>(`/absurd/workflows/${workflowId}/ready`);
  return response.data;
}

/**
 * Spawn a task with dependencies.
 */
export async function spawnTaskWithDeps(
  request: TaskWithDepsRequest
): Promise<{ task_id: string; depends_on: string[]; workflow_id: string | null }> {
  const response = await apiClient.post<{
    task_id: string;
    depends_on: string[];
    workflow_id: string | null;
  }>("/absurd/tasks/with-deps", request);
  return response.data;
}

// ============================================================================
// Historical Metrics
// ============================================================================

export interface MetricsTimeSeries {
  throughput: number[];
  success_rate: number[];
  avg_latency: number[];
  p95_latency: number[];
}

export interface MetricsHistory {
  queue_name: string;
  hours: number;
  resolution: string;
  timestamps: string[];
  series: MetricsTimeSeries;
}

/**
 * Get historical metrics for time-series charts.
 */
export async function getMetricsHistory(
  queueName: string = "dsa110-pipeline",
  hours: number = 24,
  resolution: string = "1h"
): Promise<MetricsHistory> {
  const params = new URLSearchParams();
  params.append("queue_name", queueName);
  params.append("hours", hours.toString());
  params.append("resolution", resolution);

  const response = await apiClient.get<MetricsHistory>(
    `/absurd/metrics/history?${params.toString()}`
  );
  return response.data;
}
