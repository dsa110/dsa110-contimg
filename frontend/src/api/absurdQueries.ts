/**
 * React Query hooks for Absurd workflow manager API.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import {
  spawnTask,
  getTask,
  listTasks,
  cancelTask,
  getQueueStats,
  getHealthStatus,
  getMetrics,
  getDetailedHealth,
  listWorkers,
  getWorkerMetrics,
  listQueues,
  getAllQueueStats,
  listWorkflowTemplates,
  getWorkflowTemplate,
  createWorkflowTemplate,
  updateWorkflowTemplate,
  deleteWorkflowTemplate,
  runWorkflowTemplate,
  type SpawnTaskRequest,
  type TaskInfo,
  type TaskListResponse,
  type QueueStats,
  type HealthStatus,
  type AbsurdMetrics,
  type DetailedHealth,
  type WorkerListResponse,
  type WorkerMetrics,
  type WorkflowTemplate,
  type WorkflowTemplateListResponse,
} from "./absurd";
import { useNotifications } from "../contexts/NotificationContext";
import { getWebSocketClient } from "./queries";

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Hook to list tasks with optional filtering and real-time WebSocket updates.
 */
export function useAbsurdTasks(
  queueName?: string,
  status?: string,
  limit: number = 100
): UseQueryResult<TaskListResponse> {
  const queryClient = useQueryClient();
  const wsClient = getWebSocketClient();
  const subscribed = useRef(false);

  // Set up WebSocket subscription for task updates
  useEffect(() => {
    if (!wsClient || subscribed.current) return;

    const handleTaskUpdate = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "task_update" && data.queue_name === queueName) {
          // Invalidate queries to trigger refetch
          queryClient.invalidateQueries({ queryKey: ["absurd", "tasks"] });
          queryClient.invalidateQueries({ queryKey: ["absurd", "task", data.task_id] });
          queryClient.invalidateQueries({ queryKey: ["absurd", "queueStats"] });
        }
      } catch (error) {
        console.warn("Failed to parse WebSocket task update:", error);
      }
    };

    let unsubscribe: (() => void) | undefined;
    if (wsClient && wsClient.connected) {
      unsubscribe = wsClient.on("task_update", handleTaskUpdate);
      subscribed.current = true;
    }

    return () => {
      if (unsubscribe) {
        unsubscribe();
      }
      subscribed.current = false;
    };
  }, [wsClient, queueName, queryClient]);

  return useQuery({
    queryKey: ["absurd", "tasks", queueName, status, limit],
    queryFn: () => listTasks(queueName, status, limit),
    refetchInterval: (query) => {
      // Don't poll if WebSocket is connected OR if the last query failed
      if (wsClient?.connected || query.state.status === "error") return false;
      return 5000;
    },
    retry: false, // Don't retry if ABSURD is unavailable
  });
}

/**
 * Hook to get a specific task by ID with real-time WebSocket updates.
 */
export function useAbsurdTask(taskId: string): UseQueryResult<TaskInfo> {
  const queryClient = useQueryClient();
  const wsClient = getWebSocketClient();
  const subscribed = useRef(false);

  // Set up WebSocket subscription for this specific task
  useEffect(() => {
    if (!wsClient || !taskId || subscribed.current) return;

    const handleTaskUpdate = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "task_update" && data.task_id === taskId) {
          // Update task in cache directly
          queryClient.setQueryData(["absurd", "task", taskId], (old: TaskInfo | undefined) => {
            if (old) {
              return { ...old, ...data.update };
            }
            return old;
          });
        }
      } catch (error) {
        console.warn("Failed to parse WebSocket task update:", error);
      }
    };

    let unsubscribe: (() => void) | undefined;
    if (wsClient && wsClient.connected) {
      unsubscribe = wsClient.on("task_update", handleTaskUpdate);
      subscribed.current = true;
    }

    return () => {
      if (unsubscribe) {
        unsubscribe();
      }
      subscribed.current = false;
    };
  }, [wsClient, taskId, queryClient]);

  return useQuery({
    queryKey: ["absurd", "task", taskId],
    queryFn: () => getTask(taskId),
    enabled: !!taskId,
    refetchInterval: wsClient?.connected ? false : 2000, // Poll only if WebSocket not connected
  });
}

/**
 * Hook to get queue statistics with real-time WebSocket updates.
 */
export function useQueueStats(queueName: string): UseQueryResult<QueueStats> {
  const queryClient = useQueryClient();
  const wsClient = getWebSocketClient();
  const subscribed = useRef(false);

  // Set up WebSocket subscription for queue stats updates
  useEffect(() => {
    if (!wsClient || subscribed.current) return;

    const handleQueueUpdate = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "queue_stats_update" && data.queue_name === queueName) {
          queryClient.invalidateQueries({ queryKey: ["absurd", "queueStats", queueName] });
        }
      } catch (error) {
        console.warn("Failed to parse WebSocket queue update:", error);
      }
    };

    let unsubscribe: (() => void) | undefined;
    if (wsClient && wsClient.connected) {
      unsubscribe = wsClient.on("queue_stats_update", handleQueueUpdate);
      subscribed.current = true;
    }

    return () => {
      if (unsubscribe) {
        unsubscribe();
      }
      subscribed.current = false;
    };
  }, [wsClient, queueName, queryClient]);

  return useQuery({
    queryKey: ["absurd", "queueStats", queueName],
    queryFn: () => getQueueStats(queueName),
    refetchInterval: (query) => {
      // Don't poll if WebSocket is connected OR if the last query failed
      if (wsClient?.connected || query.state.status === "error") return false;
      return 5000;
    },
    retry: false, // Don't retry if ABSURD is unavailable
  });
}

/**
 * Hook to get Absurd health status.
 */
export function useAbsurdHealth(): UseQueryResult<HealthStatus> {
  return useQuery({
    queryKey: ["absurd", "health"],
    queryFn: getHealthStatus,
    refetchInterval: (query) => {
      // Don't poll if the last query failed
      if (query.state.status === "error") return false;
      return 10000; // Refresh every 10 seconds
    },
    retry: false, // Don't retry if ABSURD is unavailable
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Hook to spawn a new task.
 */
export function useSpawnTask() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useNotifications();

  return useMutation({
    mutationFn: (request: SpawnTaskRequest) => spawnTask(request),
    onSuccess: (taskId, _variables) => {
      showSuccess(`Task spawned successfully: ${taskId.substring(0, 8)}...`);
      // Invalidate task list to show new task
      queryClient.invalidateQueries({ queryKey: ["absurd", "tasks"] });
      queryClient.invalidateQueries({ queryKey: ["absurd", "queueStats"] });
    },
    onError: (error: any) => {
      showError(`Failed to spawn task: ${error.message}`);
    },
  });
}

/**
 * Hook to cancel a task.
 */
export function useCancelTask() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useNotifications();

  return useMutation({
    mutationFn: (taskId: string) => cancelTask(taskId),
    onSuccess: (_, taskId) => {
      showSuccess(`Task cancelled: ${taskId.substring(0, 8)}...`);
      // Invalidate to refresh task list and specific task
      queryClient.invalidateQueries({ queryKey: ["absurd", "tasks"] });
      queryClient.invalidateQueries({ queryKey: ["absurd", "task", taskId] });
      queryClient.invalidateQueries({ queryKey: ["absurd", "queueStats"] });
    },
    onError: (error: any) => {
      showError(`Failed to cancel task: ${error.message}`);
    },
  });
}

/**
 * Hook to retry a failed task (spawns new task with same params).
 */
export function useRetryTask() {
  const spawnMutation = useSpawnTask();

  return useMutation({
    mutationFn: async (task: TaskInfo) => {
      // Spawn new task with same params
      return spawnMutation.mutateAsync({
        queue_name: task.queue_name,
        task_name: task.task_name,
        params: task.params,
        priority: task.priority,
      });
    },
  });
}

// ============================================================================
// Filtered Query Hooks
// ============================================================================

/**
 * Hook to get pending tasks.
 */
export function usePendingTasks(queueName?: string, limit: number = 50) {
  return useAbsurdTasks(queueName, "pending", limit);
}

/**
 * Hook to get claimed (in-progress) tasks.
 */
export function useClaimedTasks(queueName?: string, limit: number = 50) {
  return useAbsurdTasks(queueName, "claimed", limit);
}

/**
 * Hook to get completed tasks.
 */
export function useCompletedTasks(queueName?: string, limit: number = 50) {
  return useAbsurdTasks(queueName, "completed", limit);
}

/**
 * Hook to get failed tasks.
 */
export function useFailedTasks(queueName?: string, limit: number = 50) {
  return useAbsurdTasks(queueName, "failed", limit);
}

/**
 * Hook to get detailed metrics for a queue.
 * Returns timing percentiles, throughput rates, and worker statistics.
 */
export function useAbsurdMetrics(queueName?: string): UseQueryResult<AbsurdMetrics> {
  return useQuery({
    queryKey: ["absurd", "metrics", queueName],
    queryFn: () => getMetrics(),
    refetchInterval: 10000, // Refresh every 10 seconds
    retry: false,
  });
}

/**
 * Hook to get detailed health status with alerts.
 */
export function useDetailedHealth(): UseQueryResult<DetailedHealth> {
  return useQuery({
    queryKey: ["absurd", "health", "detailed"],
    queryFn: () => getDetailedHealth(),
    refetchInterval: 10000, // Refresh every 10 seconds
    retry: false,
  });
}

/**
 * Hook to get list of workers.
 */
export function useWorkers(): UseQueryResult<WorkerListResponse> {
  return useQuery({
    queryKey: ["absurd", "workers"],
    queryFn: () => listWorkers(),
    refetchInterval: 5000, // Refresh every 5 seconds
    retry: false,
  });
}

/**
 * Hook to get worker pool metrics.
 */
export function useWorkerMetrics(): UseQueryResult<WorkerMetrics> {
  return useQuery({
    queryKey: ["absurd", "workers", "metrics"],
    queryFn: () => getWorkerMetrics(),
    refetchInterval: 10000, // Refresh every 10 seconds
    retry: false,
  });
}

/**
 * Hook to list all available queues.
 */
export function useQueues(): UseQueryResult<string[]> {
  return useQuery({
    queryKey: ["absurd", "queues"],
    queryFn: () => listQueues(),
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: false,
  });
}

/**
 * Hook to get statistics for all queues.
 */
export function useAllQueueStats(): UseQueryResult<QueueStats[]> {
  return useQuery({
    queryKey: ["absurd", "queues", "stats"],
    queryFn: () => getAllQueueStats(),
    refetchInterval: 10000, // Refresh every 10 seconds
    retry: false,
  });
}

// ============================================================================
// Workflow Template Hooks
// ============================================================================

/**
 * Hook to list all workflow templates.
 */
export function useWorkflowTemplates(): UseQueryResult<WorkflowTemplateListResponse> {
  return useQuery({
    queryKey: ["absurd", "templates"],
    queryFn: () => listWorkflowTemplates(),
    retry: false,
  });
}

/**
 * Hook to get a specific workflow template.
 */
export function useWorkflowTemplate(name: string): UseQueryResult<WorkflowTemplate> {
  return useQuery({
    queryKey: ["absurd", "templates", name],
    queryFn: () => getWorkflowTemplate(name),
    enabled: !!name,
    retry: false,
  });
}

/**
 * Hook to create a workflow template.
 */
export function useCreateWorkflowTemplate() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useNotifications();

  return useMutation({
    mutationFn: (template: Omit<WorkflowTemplate, "created_at" | "updated_at">) =>
      createWorkflowTemplate(template),
    onSuccess: (data) => {
      showSuccess(`Template '${data.name}' created`);
      queryClient.invalidateQueries({ queryKey: ["absurd", "templates"] });
    },
    onError: (error: Error) => {
      showError(`Failed to create template: ${error.message}`);
    },
  });
}

/**
 * Hook to update a workflow template.
 */
export function useUpdateWorkflowTemplate() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useNotifications();

  return useMutation({
    mutationFn: ({
      name,
      template,
    }: {
      name: string;
      template: Omit<WorkflowTemplate, "created_at" | "updated_at">;
    }) => updateWorkflowTemplate(name, template),
    onSuccess: (data) => {
      showSuccess(`Template '${data.name}' updated`);
      queryClient.invalidateQueries({ queryKey: ["absurd", "templates"] });
      queryClient.invalidateQueries({ queryKey: ["absurd", "templates", data.name] });
    },
    onError: (error: Error) => {
      showError(`Failed to update template: ${error.message}`);
    },
  });
}

/**
 * Hook to delete a workflow template.
 */
export function useDeleteWorkflowTemplate() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useNotifications();

  return useMutation({
    mutationFn: (name: string) => deleteWorkflowTemplate(name),
    onSuccess: (_, name) => {
      showSuccess(`Template '${name}' deleted`);
      queryClient.invalidateQueries({ queryKey: ["absurd", "templates"] });
    },
    onError: (error: Error) => {
      showError(`Failed to delete template: ${error.message}`);
    },
  });
}

/**
 * Hook to run a workflow template.
 */
export function useRunWorkflowTemplate() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useNotifications();

  return useMutation({
    mutationFn: ({
      name,
      paramsOverride,
    }: {
      name: string;
      paramsOverride?: Record<string, unknown>;
    }) => runWorkflowTemplate(name, paramsOverride),
    onSuccess: (data) => {
      showSuccess(`Template '${data.template_name}' started with ${data.task_ids.length} tasks`);
      queryClient.invalidateQueries({ queryKey: ["absurd", "tasks"] });
      queryClient.invalidateQueries({ queryKey: ["absurd", "queueStats"] });
    },
    onError: (error: Error) => {
      showError(`Failed to run template: ${error.message}`);
    },
  });
}

// ============================================================================
// Scheduled Tasks Hooks
// ============================================================================

import {
  listSchedules,
  getSchedule,
  createSchedule,
  updateSchedule,
  deleteSchedule,
  triggerSchedule,
  listWorkflows,
  createWorkflow,
  getWorkflowStatus,
  getWorkflowDAG,
  getReadyTasks,
  spawnTaskWithDeps,
  getMetricsHistory,
  type ScheduledTask,
  type ScheduleListResponse,
  type ScheduleCreateRequest,
  type ScheduleUpdateRequest,
  type Workflow,
  type WorkflowStatus,
  type WorkflowDAG,
  type TaskWithDepsRequest,
  type MetricsHistory,
} from "./absurd";

/**
 * Hook to list scheduled tasks.
 */
export function useSchedules(
  queueName?: string,
  state?: string
): UseQueryResult<ScheduleListResponse> {
  return useQuery({
    queryKey: ["absurd", "schedules", queueName, state],
    queryFn: () => listSchedules(queueName, state),
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: false,
  });
}

/**
 * Hook to get a specific scheduled task.
 */
export function useSchedule(name: string): UseQueryResult<ScheduledTask> {
  return useQuery({
    queryKey: ["absurd", "schedules", name],
    queryFn: () => getSchedule(name),
    enabled: !!name,
    retry: false,
  });
}

/**
 * Hook to create a scheduled task.
 */
export function useCreateSchedule() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useNotifications();

  return useMutation({
    mutationFn: (request: ScheduleCreateRequest) => createSchedule(request),
    onSuccess: (data) => {
      showSuccess(`Schedule '${data.name}' created, next run at ${data.next_run_at || "N/A"}`);
      queryClient.invalidateQueries({ queryKey: ["absurd", "schedules"] });
    },
    onError: (error: Error) => {
      showError(`Failed to create schedule: ${error.message}`);
    },
  });
}

/**
 * Hook to update a scheduled task.
 */
export function useUpdateSchedule() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useNotifications();

  return useMutation({
    mutationFn: ({ name, request }: { name: string; request: ScheduleUpdateRequest }) =>
      updateSchedule(name, request),
    onSuccess: (data) => {
      showSuccess(`Schedule '${data.name}' updated`);
      queryClient.invalidateQueries({ queryKey: ["absurd", "schedules"] });
    },
    onError: (error: Error) => {
      showError(`Failed to update schedule: ${error.message}`);
    },
  });
}

/**
 * Hook to delete a scheduled task.
 */
export function useDeleteSchedule() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useNotifications();

  return useMutation({
    mutationFn: (name: string) => deleteSchedule(name),
    onSuccess: (_, name) => {
      showSuccess(`Schedule '${name}' deleted`);
      queryClient.invalidateQueries({ queryKey: ["absurd", "schedules"] });
    },
    onError: (error: Error) => {
      showError(`Failed to delete schedule: ${error.message}`);
    },
  });
}

/**
 * Hook to trigger a scheduled task immediately.
 */
export function useTriggerSchedule() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useNotifications();

  return useMutation({
    mutationFn: (name: string) => triggerSchedule(name),
    onSuccess: (data) => {
      showSuccess(`Schedule '${data.schedule_name}' triggered, task ${data.task_id} spawned`);
      queryClient.invalidateQueries({ queryKey: ["absurd", "schedules"] });
      queryClient.invalidateQueries({ queryKey: ["absurd", "tasks"] });
    },
    onError: (error: Error) => {
      showError(`Failed to trigger schedule: ${error.message}`);
    },
  });
}

// ============================================================================
// Workflow DAG Hooks
// ============================================================================

/**
 * Hook to list workflows.
 */
export function useWorkflows(
  status?: string,
  limit: number = 100
): UseQueryResult<{ workflows: Workflow[]; total: number }> {
  return useQuery({
    queryKey: ["absurd", "workflows", status, limit],
    queryFn: () => listWorkflows(status, limit),
    refetchInterval: 10000, // Refresh every 10 seconds
    retry: false,
  });
}

/**
 * Hook to create a workflow.
 */
export function useCreateWorkflow() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useNotifications();

  return useMutation({
    mutationFn: ({
      name,
      description,
      metadata,
    }: {
      name: string;
      description?: string;
      metadata?: Record<string, unknown>;
    }) => createWorkflow(name, description, metadata),
    onSuccess: (data) => {
      showSuccess(`Workflow '${data.name}' created`);
      queryClient.invalidateQueries({ queryKey: ["absurd", "workflows"] });
    },
    onError: (error: Error) => {
      showError(`Failed to create workflow: ${error.message}`);
    },
  });
}

/**
 * Hook to get workflow status.
 */
export function useWorkflowStatus(workflowId: string): UseQueryResult<WorkflowStatus> {
  return useQuery({
    queryKey: ["absurd", "workflows", workflowId, "status"],
    queryFn: () => getWorkflowStatus(workflowId),
    enabled: !!workflowId,
    refetchInterval: 5000, // Refresh every 5 seconds
    retry: false,
  });
}

/**
 * Hook to get workflow DAG for visualization.
 */
export function useWorkflowDAG(workflowId: string): UseQueryResult<WorkflowDAG> {
  return useQuery({
    queryKey: ["absurd", "workflows", workflowId, "dag"],
    queryFn: () => getWorkflowDAG(workflowId),
    enabled: !!workflowId,
    refetchInterval: 5000, // Refresh every 5 seconds
    retry: false,
  });
}

/**
 * Hook to get ready tasks in a workflow.
 */
export function useReadyTasks(
  workflowId: string
): UseQueryResult<{ workflow_id: string; ready_tasks: string[]; count: number }> {
  return useQuery({
    queryKey: ["absurd", "workflows", workflowId, "ready"],
    queryFn: () => getReadyTasks(workflowId),
    enabled: !!workflowId,
    refetchInterval: 5000,
    retry: false,
  });
}

/**
 * Hook to spawn a task with dependencies.
 */
export function useSpawnTaskWithDeps() {
  const queryClient = useQueryClient();
  const { showSuccess, showError } = useNotifications();

  return useMutation({
    mutationFn: (request: TaskWithDepsRequest) => spawnTaskWithDeps(request),
    onSuccess: (data) => {
      showSuccess(
        `Task ${data.task_id.substring(0, 8)}... spawned with ${data.depends_on.length} dependencies`
      );
      queryClient.invalidateQueries({ queryKey: ["absurd", "tasks"] });
      queryClient.invalidateQueries({ queryKey: ["absurd", "workflows"] });
    },
    onError: (error: Error) => {
      showError(`Failed to spawn task: ${error.message}`);
    },
  });
}

// ============================================================================
// Historical Metrics Hooks
// ============================================================================

/**
 * Hook to get historical metrics for time-series charts.
 */
export function useMetricsHistory(
  queueName: string = "dsa110-pipeline",
  hours: number = 24,
  resolution: string = "1h"
): UseQueryResult<MetricsHistory> {
  return useQuery({
    queryKey: ["absurd", "metrics", "history", queueName, hours, resolution],
    queryFn: () => getMetricsHistory(queueName, hours, resolution),
    refetchInterval: 60000, // Refresh every minute
    retry: false,
    staleTime: 30000, // Consider data stale after 30 seconds
  });
}
