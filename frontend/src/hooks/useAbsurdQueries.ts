/**
 * React Query hooks for ABSURD Workflow Manager.
 *
 * Provides useQuery and useMutation hooks for all ABSURD API operations
 * with automatic cache invalidation and optimistic updates.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  spawnTask,
  getTask,
  listTasks,
  cancelTask,
  retryTask,
  getQueueStats,
  listQueues,
  listWorkers,
  getWorker,
  getWorkerMetrics,
  getMetrics,
  getHealth,
  spawnWorkflow,
  getWorkflow,
  listWorkflows,
  cancelWorkflow,
  listDeadLetterTasks,
  replayDeadLetterTask,
  pruneTasks,
} from "../api/absurd";
import type {
  Task,
  TaskListResponse,
  QueueStats,
  WorkerListResponse,
  WorkerMetrics,
  AbsurdMetrics,
  AbsurdHealth,
  WorkflowDetail,
  Workflow,
  SpawnTaskRequest,
  SpawnWorkflowRequest,
} from "../types/absurd";

// =============================================================================
// Query Keys - centralized for cache invalidation
// =============================================================================

export const absurdQueryKeys = {
  // Root
  all: ["absurd"] as const,

  // Tasks
  tasks: ["absurd", "tasks"] as const,
  taskList: (params?: { queue_name?: string; status?: string }) =>
    ["absurd", "tasks", "list", params ?? {}] as const,
  task: (taskId: string) => ["absurd", "tasks", taskId] as const,

  // Queues
  queues: ["absurd", "queues"] as const,
  queueList: () => ["absurd", "queues", "list"] as const,
  queueStats: (queueName: string) =>
    ["absurd", "queues", queueName, "stats"] as const,

  // Workers
  workers: ["absurd", "workers"] as const,
  workerList: () => ["absurd", "workers", "list"] as const,
  worker: (workerId: string) => ["absurd", "workers", workerId] as const,
  workerMetrics: () => ["absurd", "workers", "metrics"] as const,

  // Metrics & Health
  metrics: () => ["absurd", "metrics"] as const,
  health: () => ["absurd", "health"] as const,

  // Workflows
  workflows: ["absurd", "workflows"] as const,
  workflowList: (params?: { status?: string }) =>
    ["absurd", "workflows", "list", params ?? {}] as const,
  workflow: (workflowId: string) => ["absurd", "workflows", workflowId] as const,

  // DLQ
  dlq: ["absurd", "dlq"] as const,
  dlqList: (params?: { limit?: number; offset?: number }) =>
    ["absurd", "dlq", "list", params ?? {}] as const,
};

// =============================================================================
// Task Hooks
// =============================================================================

/**
 * Fetch list of tasks with optional filters.
 */
export function useTasks(params?: {
  queue_name?: string;
  status?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery<TaskListResponse>({
    queryKey: absurdQueryKeys.taskList(params),
    queryFn: () => listTasks(params),
    refetchInterval: 5000, // Auto-refresh every 5s
  });
}

/**
 * Fetch a single task by ID.
 */
export function useTask(taskId: string | undefined) {
  return useQuery<Task>({
    queryKey: absurdQueryKeys.task(taskId ?? ""),
    queryFn: () => getTask(taskId!),
    enabled: !!taskId,
    refetchInterval: (data) =>
      data?.status === "claimed" ? 2000 : 10000, // Faster refresh for running tasks
  });
}

/**
 * Spawn a new task.
 */
export function useSpawnTask() {
  const queryClient = useQueryClient();

  return useMutation<string, Error, SpawnTaskRequest>({
    mutationFn: spawnTask,
    onSuccess: () => {
      // Invalidate task lists and queue stats
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.tasks });
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.queues });
    },
  });
}

/**
 * Cancel a task.
 */
export function useCancelTask() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { taskId: string; reason?: string }>({
    mutationFn: ({ taskId, reason }) => cancelTask(taskId, reason),
    onSuccess: (_, { taskId }) => {
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.task(taskId) });
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.tasks });
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.queues });
    },
  });
}

/**
 * Retry a failed task.
 */
export function useRetryTask() {
  const queryClient = useQueryClient();

  return useMutation<string, Error, string>({
    mutationFn: retryTask,
    onSuccess: (_, taskId) => {
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.task(taskId) });
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.tasks });
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.queues });
    },
  });
}

// =============================================================================
// Queue Hooks
// =============================================================================

/**
 * Fetch list of known queues.
 */
export function useQueues() {
  return useQuery<string[]>({
    queryKey: absurdQueryKeys.queueList(),
    queryFn: listQueues,
  });
}

/**
 * Fetch statistics for a specific queue.
 */
export function useQueueStats(queueName: string | undefined) {
  return useQuery<QueueStats>({
    queryKey: absurdQueryKeys.queueStats(queueName ?? ""),
    queryFn: () => getQueueStats(queueName!),
    enabled: !!queueName,
    refetchInterval: 5000,
  });
}

// =============================================================================
// Worker Hooks
// =============================================================================

/**
 * Fetch list of workers.
 */
export function useWorkers() {
  return useQuery<WorkerListResponse>({
    queryKey: absurdQueryKeys.workerList(),
    queryFn: listWorkers,
    refetchInterval: 10000,
  });
}

/**
 * Fetch a specific worker.
 */
export function useWorker(workerId: string | undefined) {
  return useQuery({
    queryKey: absurdQueryKeys.worker(workerId ?? ""),
    queryFn: () => getWorker(workerId!),
    enabled: !!workerId,
  });
}

/**
 * Fetch worker pool metrics.
 */
export function useWorkerMetrics() {
  return useQuery<WorkerMetrics>({
    queryKey: absurdQueryKeys.workerMetrics(),
    queryFn: getWorkerMetrics,
    refetchInterval: 10000,
  });
}

// =============================================================================
// Metrics & Health Hooks
// =============================================================================

/**
 * Fetch ABSURD system metrics.
 */
export function useAbsurdMetrics() {
  return useQuery<AbsurdMetrics>({
    queryKey: absurdQueryKeys.metrics(),
    queryFn: getMetrics,
    refetchInterval: 10000,
  });
}

/**
 * Fetch ABSURD health status.
 */
export function useAbsurdHealth() {
  return useQuery<AbsurdHealth>({
    queryKey: absurdQueryKeys.health(),
    queryFn: getHealth,
    refetchInterval: 30000, // Less frequent for health
  });
}

// =============================================================================
// Workflow Hooks
// =============================================================================

/**
 * Fetch list of workflows.
 */
export function useWorkflows(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery<{ workflows: Workflow[]; total: number }>({
    queryKey: absurdQueryKeys.workflowList(params),
    queryFn: () => listWorkflows(params),
    refetchInterval: 5000,
  });
}

/**
 * Fetch a single workflow by ID.
 */
export function useWorkflow(workflowId: string | undefined) {
  return useQuery<WorkflowDetail>({
    queryKey: absurdQueryKeys.workflow(workflowId ?? ""),
    queryFn: () => getWorkflow(workflowId!),
    enabled: !!workflowId,
    refetchInterval: (data) =>
      data?.status === "running" ? 2000 : 10000,
  });
}

/**
 * Spawn a new workflow.
 */
export function useSpawnWorkflow() {
  const queryClient = useQueryClient();

  return useMutation<string, Error, SpawnWorkflowRequest>({
    mutationFn: spawnWorkflow,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.workflows });
    },
  });
}

/**
 * Cancel a workflow.
 */
export function useCancelWorkflow() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { workflowId: string; reason?: string }>({
    mutationFn: ({ workflowId, reason }) => cancelWorkflow(workflowId, reason),
    onSuccess: (_, { workflowId }) => {
      queryClient.invalidateQueries({
        queryKey: absurdQueryKeys.workflow(workflowId),
      });
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.workflows });
    },
  });
}

// =============================================================================
// Dead Letter Queue Hooks
// =============================================================================

/**
 * Fetch tasks in the dead letter queue.
 */
export function useDeadLetterTasks(params?: {
  limit?: number;
  offset?: number;
}) {
  return useQuery<TaskListResponse>({
    queryKey: absurdQueryKeys.dlqList(params),
    queryFn: () => listDeadLetterTasks(params),
  });
}

/**
 * Replay a task from the DLQ.
 */
export function useReplayDeadLetterTask() {
  const queryClient = useQueryClient();

  return useMutation<string, Error, string>({
    mutationFn: replayDeadLetterTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.dlq });
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.tasks });
    },
  });
}

// =============================================================================
// Utility Hooks
// =============================================================================

/**
 * Prune old tasks.
 */
export function usePruneTasks() {
  const queryClient = useQueryClient();

  return useMutation<
    { pruned: number },
    Error,
    { retention_days?: number; queue_name?: string; statuses?: string[] }
  >({
    mutationFn: pruneTasks,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.tasks });
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.queues });
    },
  });
}

// =============================================================================
// Re-export types for convenience
// =============================================================================

export type {
  Task,
  TaskListResponse,
  QueueStats,
  WorkerListResponse,
  WorkerMetrics,
  AbsurdMetrics,
  AbsurdHealth,
  Workflow,
  WorkflowDetail,
  SpawnTaskRequest,
  SpawnWorkflowRequest,
};
