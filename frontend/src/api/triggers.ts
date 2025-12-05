/**
 * Pipeline Triggers API
 *
 * Provides hooks for managing automated pipeline triggers including:
 * - Creating event-based triggers (new data, schedule, manual)
 * - Monitoring trigger history
 * - Managing trigger rules and conditions
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

// ============================================================================
// Types
// ============================================================================

/** Trigger event types */
export type TriggerEvent =
  | "new_measurement_set"
  | "calibration_complete"
  | "schedule"
  | "manual"
  | "data_quality_alert"
  | "storage_threshold";

/** Trigger status */
export type TriggerStatus = "enabled" | "disabled" | "error";

/** Execution status */
export type ExecutionStatus =
  | "pending"
  | "running"
  | "success"
  | "failed"
  | "skipped";

/** Filter condition operators */
export type ConditionOperator =
  | "equals"
  | "not_equals"
  | "contains"
  | "gt"
  | "gte"
  | "lt"
  | "lte"
  | "in"
  | "not_in";

/** Trigger condition */
export interface TriggerCondition {
  field: string;
  operator: ConditionOperator;
  value: string | number | string[];
}

/** Schedule configuration for scheduled triggers */
export interface ScheduleConfig {
  /** Cron expression */
  cron: string;
  /** Human-readable description */
  description: string;
  /** Timezone */
  timezone: string;
  /** Next scheduled run */
  next_run?: string;
}

/** Pipeline trigger definition */
export interface PipelineTrigger {
  id: string;
  name: string;
  description?: string;
  event: TriggerEvent;
  status: TriggerStatus;
  /** Pipeline to execute */
  pipeline_id: string;
  pipeline_name: string;
  /** Filter conditions (all must match) */
  conditions: TriggerCondition[];
  /** Schedule config (for scheduled triggers) */
  schedule?: ScheduleConfig;
  /** Pipeline parameters to pass */
  parameters: Record<string, unknown>;
  /** Priority (lower = higher priority) */
  priority: number;
  /** Maximum concurrent executions */
  max_concurrent: number;
  /** Retry configuration */
  retry_count: number;
  retry_delay_seconds: number;
  /** Rate limiting */
  cooldown_seconds: number;
  /** Statistics */
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  last_execution?: string;
  /** Audit info */
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
}

/** Trigger execution record */
export interface TriggerExecution {
  id: string;
  trigger_id: string;
  trigger_name: string;
  pipeline_id: string;
  pipeline_name: string;
  status: ExecutionStatus;
  /** What triggered this execution */
  event_type: TriggerEvent;
  event_data?: Record<string, unknown>;
  /** Resulting pipeline job */
  job_id?: string;
  /** Execution details */
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  error_message?: string;
  /** Skip reason if skipped */
  skip_reason?: string;
}

/** Create trigger request */
export interface CreateTriggerRequest {
  name: string;
  description?: string;
  event: TriggerEvent;
  pipeline_id: string;
  conditions?: TriggerCondition[];
  schedule?: ScheduleConfig;
  parameters?: Record<string, unknown>;
  priority?: number;
  max_concurrent?: number;
  retry_count?: number;
  retry_delay_seconds?: number;
  cooldown_seconds?: number;
}

/** Update trigger request */
export interface UpdateTriggerRequest {
  name?: string;
  description?: string;
  conditions?: TriggerCondition[];
  schedule?: ScheduleConfig;
  parameters?: Record<string, unknown>;
  priority?: number;
  max_concurrent?: number;
  retry_count?: number;
  retry_delay_seconds?: number;
  cooldown_seconds?: number;
}

/** Available pipeline for trigger configuration */
export interface AvailablePipeline {
  id: string;
  name: string;
  description?: string;
  parameters: Array<{
    name: string;
    type: "string" | "number" | "boolean" | "array";
    required: boolean;
    default?: unknown;
    description?: string;
  }>;
}

// ============================================================================
// Query Keys
// ============================================================================

export const triggerKeys = {
  all: ["triggers"] as const,
  lists: () => [...triggerKeys.all, "list"] as const,
  list: (filters: Record<string, unknown>) =>
    [...triggerKeys.lists(), filters] as const,
  details: () => [...triggerKeys.all, "detail"] as const,
  detail: (id: string) => [...triggerKeys.details(), id] as const,
  executions: (id: string) => [...triggerKeys.all, "executions", id] as const,
  recentExecutions: () => [...triggerKeys.all, "recent-executions"] as const,
  pipelines: () => [...triggerKeys.all, "pipelines"] as const,
};

// ============================================================================
// Hooks
// ============================================================================

/**
 * Fetch list of triggers
 */
export function useTriggers(options?: {
  event?: TriggerEvent;
  status?: TriggerStatus;
  limit?: number;
}) {
  return useQuery({
    queryKey: triggerKeys.list(options ?? {}),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (options?.event) params.append("event", options.event);
      if (options?.status) params.append("status", options.status);
      if (options?.limit) params.append("limit", options.limit.toString());

      const response = await apiClient.get<{ triggers: PipelineTrigger[] }>(
        `/api/v1/triggers?${params}`
      );
      return response.data.triggers;
    },
    staleTime: 30_000,
  });
}

/**
 * Fetch single trigger details
 */
export function useTrigger(id: string) {
  return useQuery({
    queryKey: triggerKeys.detail(id),
    queryFn: async () => {
      const response = await apiClient.get<PipelineTrigger>(
        `/api/v1/triggers/${id}`
      );
      return response.data;
    },
    enabled: !!id,
  });
}

/**
 * Fetch trigger executions
 */
export function useTriggerExecutions(triggerId: string, limit = 20) {
  return useQuery({
    queryKey: triggerKeys.executions(triggerId),
    queryFn: async () => {
      const response = await apiClient.get<{ executions: TriggerExecution[] }>(
        `/api/v1/triggers/${triggerId}/executions?limit=${limit}`
      );
      return response.data.executions;
    },
    enabled: !!triggerId,
    staleTime: 10_000,
  });
}

/**
 * Fetch recent executions across all triggers
 */
export function useRecentExecutions(limit = 20) {
  return useQuery({
    queryKey: triggerKeys.recentExecutions(),
    queryFn: async () => {
      const response = await apiClient.get<{ executions: TriggerExecution[] }>(
        `/api/v1/triggers/executions/recent?limit=${limit}`
      );
      return response.data.executions;
    },
    staleTime: 10_000,
    refetchInterval: 30_000, // Auto-refresh every 30s
  });
}

/**
 * Fetch available pipelines for trigger configuration
 */
export function useAvailablePipelines() {
  return useQuery({
    queryKey: triggerKeys.pipelines(),
    queryFn: async () => {
      const response = await apiClient.get<{ pipelines: AvailablePipeline[] }>(
        `/api/v1/pipelines/available`
      );
      return response.data.pipelines;
    },
    staleTime: 300_000, // Cache for 5 minutes
  });
}

/**
 * Create a new trigger
 */
export function useCreateTrigger() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: CreateTriggerRequest) => {
      const response = await apiClient.post<PipelineTrigger>(
        "/triggers",
        request
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: triggerKeys.lists() });
    },
  });
}

/**
 * Update an existing trigger
 */
export function useUpdateTrigger() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      ...data
    }: UpdateTriggerRequest & { id: string }) => {
      const response = await apiClient.patch<PipelineTrigger>(
        `/triggers/${id}`,
        data
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: triggerKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: triggerKeys.detail(variables.id),
      });
    },
  });
}

/**
 * Delete a trigger
 */
export function useDeleteTrigger() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/triggers/${id}`);
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: triggerKeys.lists() });
    },
  });
}

/**
 * Enable/disable a trigger
 */
export function useToggleTrigger() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, enabled }: { id: string; enabled: boolean }) => {
      const response = await apiClient.patch<PipelineTrigger>(
        `/triggers/${id}/status`,
        { status: enabled ? "enabled" : "disabled" }
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: triggerKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: triggerKeys.detail(variables.id),
      });
    },
  });
}

/**
 * Manually execute a trigger
 */
export function useExecuteTrigger() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      eventData,
    }: {
      id: string;
      eventData?: Record<string, unknown>;
    }) => {
      const response = await apiClient.post<TriggerExecution>(
        `/triggers/${id}/execute`,
        { event_data: eventData }
      );
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: triggerKeys.executions(variables.id),
      });
      queryClient.invalidateQueries({
        queryKey: triggerKeys.recentExecutions(),
      });
    },
  });
}

/**
 * Test trigger conditions without executing
 */
export function useTestTrigger() {
  return useMutation({
    mutationFn: async ({
      id,
      testData,
    }: {
      id: string;
      testData: Record<string, unknown>;
    }) => {
      const response = await apiClient.post<{
        would_trigger: boolean;
        matched_conditions: string[];
        failed_conditions: string[];
      }>(`/triggers/${id}/test`, { test_data: testData });
      return response.data;
    },
  });
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Format trigger event for display
 */
export function formatTriggerEvent(event: TriggerEvent): string {
  const labels: Record<TriggerEvent, string> = {
    new_measurement_set: "New Measurement Set",
    calibration_complete: "Calibration Complete",
    schedule: "Scheduled",
    manual: "Manual",
    data_quality_alert: "Data Quality Alert",
    storage_threshold: "Storage Threshold",
  };
  return labels[event];
}

/**
 * Get trigger event icon
 */
export function getTriggerEventIcon(event: TriggerEvent): string {
  const icons: Record<TriggerEvent, string> = {
    new_measurement_set: "📡",
    calibration_complete: "✅",
    schedule: "⏰",
    manual: "👆",
    data_quality_alert: "⚠️",
    storage_threshold: "💾",
  };
  return icons[event];
}

/**
 * Format condition operator for display
 */
export function formatConditionOperator(op: ConditionOperator): string {
  const labels: Record<ConditionOperator, string> = {
    equals: "equals",
    not_equals: "not equals",
    contains: "contains",
    gt: ">",
    gte: ">=",
    lt: "<",
    lte: "<=",
    in: "in",
    not_in: "not in",
  };
  return labels[op];
}

/**
 * Format cron expression to human readable
 */
export function formatCronExpression(cron: string): string {
  const parts = cron.split(" ");
  if (parts.length !== 5) return cron;

  const [minute, hour, dayOfMonth, _month, dayOfWeek] = parts;

  if (minute === "0" && hour === "*") return "Every hour";
  if (minute === "0" && hour === "0" && dayOfMonth === "*")
    return "Daily at midnight";
  if (minute === "0" && hour === "0" && dayOfWeek === "0")
    return "Weekly on Sunday";
  if (minute === "0" && hour === "0" && dayOfMonth === "1")
    return "Monthly on 1st";

  return cron;
}

/**
 * Calculate trigger success rate
 */
export function calculateSuccessRate(trigger: PipelineTrigger): number {
  if (trigger.total_executions === 0) return 0;
  return Math.round(
    (trigger.successful_executions / trigger.total_executions) * 100
  );
}
