/**
 * ABSURD Workflow Manager API Client.
 *
 * Provides functions for interacting with the ABSURD durable task queue
 * REST API. All functions use the shared axios client with resilience features.
 */

import apiClient from "./client";
import type {
  Task,
  TaskListResponse,
  QueueStats,
  Worker,
  WorkerListResponse,
  WorkerMetrics,
  AbsurdMetrics,
  AbsurdHealth,
  Workflow,
  WorkflowDetail,
  SpawnTaskRequest,
  SpawnWorkflowRequest,
} from "../types/absurd";

// =============================================================================
// Base Path
// =============================================================================

const BASE_PATH = "/v1/absurd";

// =============================================================================
// Task Operations
// =============================================================================

/**
 * Spawn a new task in the queue.
 */
export async function spawnTask(request: SpawnTaskRequest): Promise<string> {
  const response = await apiClient.post<{ task_id: string }>(
    `${BASE_PATH}/spawn`,
    request
  );
  return response.data.task_id;
}

/**
 * Get task details by ID.
 */
export async function getTask(taskId: string): Promise<Task> {
  const response = await apiClient.get<Task>(`${BASE_PATH}/tasks/${taskId}`);
  return response.data;
}

/**
 * List tasks with optional filters.
 */
export async function listTasks(params?: {
  queue_name?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<TaskListResponse> {
  const response = await apiClient.get<TaskListResponse>(`${BASE_PATH}/tasks`, {
    params,
  });
  return response.data;
}

/**
 * Cancel a pending or running task.
 */
export async function cancelTask(
  taskId: string,
  reason?: string
): Promise<void> {
  await apiClient.delete(`${BASE_PATH}/tasks/${taskId}`, {
    data: reason ? { reason } : undefined,
  });
}

/**
 * Retry a failed task.
 */
export async function retryTask(taskId: string): Promise<string> {
  const response = await apiClient.post<{ task_id: string }>(
    `${BASE_PATH}/tasks/${taskId}/retry`
  );
  return response.data.task_id;
}

// =============================================================================
// Queue Operations
// =============================================================================

/**
 * Get statistics for a queue.
 */
export async function getQueueStats(queueName: string): Promise<QueueStats> {
  const response = await apiClient.get<QueueStats>(
    `${BASE_PATH}/queues/${queueName}/stats`
  );
  return response.data;
}

/**
 * List all known queues.
 */
export async function listQueues(): Promise<string[]> {
  const response = await apiClient.get<{ queues: string[] }>(
    `${BASE_PATH}/queues`
  );
  return response.data.queues;
}

// =============================================================================
// Worker Operations
// =============================================================================

/**
 * List all workers.
 */
export async function listWorkers(): Promise<WorkerListResponse> {
  const response = await apiClient.get<WorkerListResponse>(
    `${BASE_PATH}/workers`
  );
  return response.data;
}

/**
 * Get worker details.
 */
export async function getWorker(workerId: string): Promise<Worker> {
  const response = await apiClient.get<Worker>(
    `${BASE_PATH}/workers/${workerId}`
  );
  return response.data;
}

/**
 * Get worker pool metrics.
 */
export async function getWorkerMetrics(): Promise<WorkerMetrics> {
  const response = await apiClient.get<WorkerMetrics>(
    `${BASE_PATH}/workers/metrics`
  );
  return response.data;
}

// =============================================================================
// Metrics & Health
// =============================================================================

/**
 * Get ABSURD system metrics.
 */
export async function getMetrics(): Promise<AbsurdMetrics> {
  const response = await apiClient.get<AbsurdMetrics>(`${BASE_PATH}/metrics`);
  return response.data;
}

/**
 * Get ABSURD health status.
 */
export async function getHealth(): Promise<AbsurdHealth> {
  const response = await apiClient.get<AbsurdHealth>(`${BASE_PATH}/health`);
  return response.data;
}

// =============================================================================
// Workflow Operations
// =============================================================================

/**
 * Spawn a new workflow.
 */
export async function spawnWorkflow(
  request: SpawnWorkflowRequest
): Promise<string> {
  const response = await apiClient.post<{ workflow_id: string }>(
    `${BASE_PATH}/workflows`,
    request
  );
  return response.data.workflow_id;
}

/**
 * Get workflow details by ID.
 */
export async function getWorkflow(workflowId: string): Promise<WorkflowDetail> {
  const response = await apiClient.get<WorkflowDetail>(
    `${BASE_PATH}/workflows/${workflowId}`
  );
  return response.data;
}

/**
 * List all workflows.
 */
export async function listWorkflows(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<{ workflows: Workflow[]; total: number }> {
  const response = await apiClient.get<{
    workflows: Workflow[];
    total: number;
  }>(`${BASE_PATH}/workflows`, { params });
  return response.data;
}

/**
 * Cancel a running workflow.
 */
export async function cancelWorkflow(
  workflowId: string,
  reason?: string
): Promise<void> {
  await apiClient.delete(`${BASE_PATH}/workflows/${workflowId}`, {
    data: reason ? { reason } : undefined,
  });
}

// =============================================================================
// Scheduling Operations
// =============================================================================

/**
 * List scheduled tasks.
 */
export async function listScheduledTasks(): Promise<TaskListResponse> {
  const response = await apiClient.get<TaskListResponse>(
    `${BASE_PATH}/scheduled`
  );
  return response.data;
}

/**
 * Spawn a scheduled task.
 */
export async function scheduleTask(
  request: SpawnTaskRequest & {
    run_at?: string; // ISO timestamp
    cron?: string; // Cron expression
  }
): Promise<string> {
  const response = await apiClient.post<{ task_id: string }>(
    `${BASE_PATH}/scheduled`,
    request
  );
  return response.data.task_id;
}

// =============================================================================
// Dead Letter Queue Operations
// =============================================================================

/**
 * List tasks in the dead letter queue.
 */
export async function listDeadLetterTasks(params?: {
  limit?: number;
  offset?: number;
}): Promise<TaskListResponse> {
  const response = await apiClient.get<TaskListResponse>(`${BASE_PATH}/dlq`, {
    params,
  });
  return response.data;
}

/**
 * Replay a task from the dead letter queue.
 */
export async function replayDeadLetterTask(taskId: string): Promise<string> {
  const response = await apiClient.post<{ task_id: string }>(
    `${BASE_PATH}/dlq/${taskId}/replay`
  );
  return response.data.task_id;
}

/**
 * Purge tasks from the dead letter queue.
 */
export async function purgeDeadLetterQueue(params?: {
  before?: string; // ISO timestamp
}): Promise<{ purged: number }> {
  const response = await apiClient.delete<{ purged: number }>(
    `${BASE_PATH}/dlq`,
    { params }
  );
  return response.data;
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Prune old completed/failed tasks.
 */
export async function pruneTasks(params?: {
  retention_days?: number;
  queue_name?: string;
  statuses?: string[];
}): Promise<{ pruned: number }> {
  const response = await apiClient.post<{ pruned: number }>(
    `${BASE_PATH}/prune`,
    params
  );
  return response.data;
}

// =============================================================================
// Export all functions as named exports and as default object
// =============================================================================

const absurdApi = {
  // Tasks
  spawnTask,
  getTask,
  listTasks,
  cancelTask,
  retryTask,
  // Queues
  getQueueStats,
  listQueues,
  // Workers
  listWorkers,
  getWorker,
  getWorkerMetrics,
  // Metrics & Health
  getMetrics,
  getHealth,
  // Workflows
  spawnWorkflow,
  getWorkflow,
  listWorkflows,
  cancelWorkflow,
  // Scheduling
  listScheduledTasks,
  scheduleTask,
  // DLQ
  listDeadLetterTasks,
  replayDeadLetterTask,
  purgeDeadLetterQueue,
  // Utility
  pruneTasks,
};

export default absurdApi;
