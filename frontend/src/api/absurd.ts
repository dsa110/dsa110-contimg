/**
 * API client for Absurd workflow manager.
 *
 * Provides functions for spawning, querying, and managing Absurd tasks.
 */

import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface SpawnTaskRequest {
  queue_name: string;
  task_name: string;
  params: Record<string, any>;
  priority?: number;
  timeout_sec?: number;
}

export interface TaskInfo {
  task_id: string;
  queue_name: string;
  task_name: string;
  params: Record<string, any>;
  priority: number;
  status: string;
  created_at: string | null;
  claimed_at: string | null;
  completed_at: string | null;
  result: Record<string, any> | null;
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
  status: "healthy" | "disabled" | "error";
  message: string;
  queue?: string;
}

/**
 * Spawn a new task in the Absurd queue.
 */
export async function spawnTask(request: SpawnTaskRequest): Promise<string> {
  const response = await axios.post<{ task_id: string }>(
    `${API_BASE_URL}/api/absurd/tasks`,
    request
  );
  return response.data.task_id;
}

/**
 * Get task details by ID.
 */
export async function getTask(taskId: string): Promise<TaskInfo> {
  const response = await axios.get<TaskInfo>(`${API_BASE_URL}/api/absurd/tasks/${taskId}`);
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

  const response = await axios.get<TaskListResponse>(
    `${API_BASE_URL}/api/absurd/tasks?${params.toString()}`
  );
  return response.data;
}

/**
 * Cancel a pending task.
 */
export async function cancelTask(taskId: string): Promise<void> {
  await axios.delete(`${API_BASE_URL}/api/absurd/tasks/${taskId}`);
}

/**
 * Get queue statistics.
 */
export async function getQueueStats(queueName: string): Promise<QueueStats> {
  const response = await axios.get<QueueStats>(
    `${API_BASE_URL}/api/absurd/queues/${queueName}/stats`
  );
  return response.data;
}

/**
 * Check Absurd health status.
 */
export async function getHealthStatus(): Promise<HealthStatus> {
  const response = await axios.get<HealthStatus>(`${API_BASE_URL}/api/absurd/health`);
  return response.data;
}
