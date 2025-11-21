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
  type SpawnTaskRequest,
  type TaskInfo,
  type TaskListResponse,
  type QueueStats,
  type HealthStatus,
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
