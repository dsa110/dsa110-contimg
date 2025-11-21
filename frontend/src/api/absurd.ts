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
