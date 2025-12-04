/**
 * Pipeline Triggers Page
 *
 * Provides UI for:
 * - Creating and managing automated pipeline triggers
 * - Monitoring trigger execution history
 * - Configuring trigger conditions and schedules
 */

import React, { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  useTriggers,
  useCreateTrigger,
  useDeleteTrigger,
  useToggleTrigger,
  useExecuteTrigger,
  useRecentExecutions,
  useAvailablePipelines,
  formatTriggerEvent,
  getTriggerEventIcon,
  calculateSuccessRate,
  type PipelineTrigger,
  type TriggerExecution,
  type TriggerEvent,
  type TriggerCondition,
  type ScheduleConfig,
  type ConditionOperator,
} from "../api/triggers";
import { ROUTES } from "../constants/routes";

// ============================================================================
// Sub-components
// ============================================================================

interface TriggerCardProps {
  trigger: PipelineTrigger;
  onToggle: (id: string, enabled: boolean) => void;
  onExecute: (id: string) => void;
  onDelete: (id: string) => void;
}

function TriggerCard({
  trigger,
  onToggle,
  onExecute,
  onDelete,
}: TriggerCardProps) {
  const successRate = calculateSuccessRate(trigger);
  const isEnabled = trigger.status === "enabled";

  const statusColors: Record<string, string> = {
    enabled: "text-green-600 bg-green-100 dark:bg-green-900/30",
    disabled: "text-gray-600 bg-gray-100 dark:bg-gray-700",
    error: "text-red-600 bg-red-100 dark:bg-red-900/30",
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <span className="text-2xl">{getTriggerEventIcon(trigger.event)}</span>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-gray-100">
              {trigger.name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {formatTriggerEvent(trigger.event)} → {trigger.pipeline_name}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-1 text-xs font-medium rounded-full capitalize ${
              statusColors[trigger.status]
            }`}
          >
            {trigger.status}
          </span>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={isEnabled}
              onChange={() => onToggle(trigger.id, !isEnabled)}
              className="sr-only peer"
              aria-label={`Toggle ${trigger.name}`}
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:ring-2 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600" />
          </label>
        </div>
      </div>

      {trigger.description && (
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          {trigger.description}
        </p>
      )}

      {/* Conditions Summary */}
      {trigger.conditions.length > 0 && (
        <div className="mt-3 text-sm">
          <span className="text-gray-500 dark:text-gray-400">Conditions: </span>
          <span className="text-gray-700 dark:text-gray-300">
            {trigger.conditions.length} rule{trigger.conditions.length > 1 ? "s" : ""}
          </span>
        </div>
      )}

      {/* Schedule Info */}
      {trigger.schedule && (
        <div className="mt-2 text-sm">
          <span className="text-gray-500 dark:text-gray-400">Schedule: </span>
          <span className="text-gray-700 dark:text-gray-300">
            {trigger.schedule.description}
          </span>
          {trigger.schedule.next_run && (
            <span className="text-gray-400 dark:text-gray-500 ml-2">
              (next: {new Date(trigger.schedule.next_run).toLocaleString()})
            </span>
          )}
        </div>
      )}

      {/* Statistics */}
      <div className="mt-4 grid grid-cols-3 gap-4 text-center text-sm">
        <div>
          <div className="font-semibold text-gray-900 dark:text-gray-100">
            {trigger.total_executions}
          </div>
          <div className="text-gray-500 dark:text-gray-400">Executions</div>
        </div>
        <div>
          <div
            className={`font-semibold ${
              successRate >= 80
                ? "text-green-600"
                : successRate >= 50
                  ? "text-yellow-600"
                  : "text-red-600"
            }`}
          >
            {successRate}%
          </div>
          <div className="text-gray-500 dark:text-gray-400">Success Rate</div>
        </div>
        <div>
          <div className="font-semibold text-gray-900 dark:text-gray-100">
            {trigger.last_execution
              ? new Date(trigger.last_execution).toLocaleDateString()
              : "Never"}
          </div>
          <div className="text-gray-500 dark:text-gray-400">Last Run</div>
        </div>
      </div>

      {/* Actions */}
      <div className="mt-4 flex gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={() => onExecute(trigger.id)}
          disabled={!isEnabled}
          className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
        >
          <span>▶️</span>
          Run Now
        </button>
        <button
          onClick={() => onDelete(trigger.id)}
          className="px-3 py-1.5 text-sm border border-red-300 text-red-600 rounded hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-1"
        >
          <span>🗑️</span>
          Delete
        </button>
      </div>
    </div>
  );
}

interface CreateTriggerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

function CreateTriggerModal({ isOpen, onClose }: CreateTriggerModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [event, setEvent] = useState<TriggerEvent>("new_measurement_set");
  const [pipelineId, setPipelineId] = useState("");
  const [conditions, setConditions] = useState<TriggerCondition[]>([]);
  const [cronExpression, setCronExpression] = useState("0 0 * * *");
  const [cronDescription, setCronDescription] = useState("Daily at midnight");

  const { data: pipelines } = useAvailablePipelines();
  const createTrigger = useCreateTrigger();

  const addCondition = () => {
    setConditions([
      ...conditions,
      { field: "", operator: "equals", value: "" },
    ]);
  };

  const updateCondition = (
    index: number,
    field: keyof TriggerCondition,
    value: string | ConditionOperator
  ) => {
    const updated = [...conditions];
    updated[index] = { ...updated[index], [field]: value };
    setConditions(updated);
  };

  const removeCondition = (index: number) => {
    setConditions(conditions.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const schedule: ScheduleConfig | undefined =
        event === "schedule"
          ? {
              cron: cronExpression,
              description: cronDescription,
              timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            }
          : undefined;

      await createTrigger.mutateAsync({
        name,
        description: description || undefined,
        event,
        pipeline_id: pipelineId,
        conditions: conditions.filter((c) => c.field && c.value),
        schedule,
      });
      onClose();
      // Reset form
      setName("");
      setDescription("");
      setPipelineId("");
      setConditions([]);
    } catch {
      // Error handled by mutation
    }
  };

  if (!isOpen) return null;

  const eventOptions: TriggerEvent[] = [
    "new_measurement_set",
    "calibration_complete",
    "schedule",
    "manual",
    "data_quality_alert",
    "storage_threshold",
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div
          className="fixed inset-0 bg-black/50 transition-opacity"
          onClick={onClose}
        />
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <form onSubmit={handleSubmit}>
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Create Pipeline Trigger
              </h2>
            </div>

            <div className="p-6 space-y-6">
              {/* Name */}
              <div>
                <label
                  htmlFor="trigger-name"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Trigger Name
                </label>
                <input
                  id="trigger-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  placeholder="e.g., Auto-process new MS"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>

              {/* Description */}
              <div>
                <label
                  htmlFor="trigger-description"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Description (optional)
                </label>
                <textarea
                  id="trigger-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  placeholder="What does this trigger do?"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>

              {/* Event Type */}
              <div>
                <label
                  htmlFor="trigger-event"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Trigger Event
                </label>
                <select
                  id="trigger-event"
                  value={event}
                  onChange={(e) => setEvent(e.target.value as TriggerEvent)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                >
                  {eventOptions.map((e) => (
                    <option key={e} value={e}>
                      {getTriggerEventIcon(e)} {formatTriggerEvent(e)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Schedule (if event is schedule) */}
              {event === "schedule" && (
                <div className="space-y-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div>
                    <label
                      htmlFor="cron-expression"
                      className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                    >
                      Cron Expression
                    </label>
                    <input
                      id="cron-expression"
                      type="text"
                      value={cronExpression}
                      onChange={(e) => setCronExpression(e.target.value)}
                      placeholder="0 0 * * *"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 font-mono"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="cron-description"
                      className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                    >
                      Schedule Description
                    </label>
                    <input
                      id="cron-description"
                      type="text"
                      value={cronDescription}
                      onChange={(e) => setCronDescription(e.target.value)}
                      placeholder="e.g., Daily at midnight"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                    />
                  </div>
                </div>
              )}

              {/* Pipeline */}
              <div>
                <label
                  htmlFor="trigger-pipeline"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Pipeline to Execute
                </label>
                <select
                  id="trigger-pipeline"
                  value={pipelineId}
                  onChange={(e) => setPipelineId(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                >
                  <option value="">Select a pipeline...</option>
                  {pipelines?.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Conditions */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Filter Conditions (optional)
                  </label>
                  <button
                    type="button"
                    onClick={addCondition}
                    className="text-sm text-blue-600 hover:text-blue-700"
                  >
                    + Add Condition
                  </button>
                </div>
                {conditions.length === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    No conditions - trigger will fire on every matching event
                  </p>
                ) : (
                  <div className="space-y-2">
                    {conditions.map((condition, index) => (
                      <div key={index} className="flex gap-2 items-center">
                        <input
                          type="text"
                          value={condition.field}
                          onChange={(e) =>
                            updateCondition(index, "field", e.target.value)
                          }
                          placeholder="Field"
                          className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-sm"
                        />
                        <select
                          value={condition.operator}
                          onChange={(e) =>
                            updateCondition(
                              index,
                              "operator",
                              e.target.value as ConditionOperator
                            )
                          }
                          className="px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-sm"
                        >
                          <option value="equals">=</option>
                          <option value="not_equals">≠</option>
                          <option value="contains">contains</option>
                          <option value="gt">&gt;</option>
                          <option value="gte">≥</option>
                          <option value="lt">&lt;</option>
                          <option value="lte">≤</option>
                        </select>
                        <input
                          type="text"
                          value={condition.value as string}
                          onChange={(e) =>
                            updateCondition(index, "value", e.target.value)
                          }
                          placeholder="Value"
                          className="flex-1 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-sm"
                        />
                        <button
                          type="button"
                          onClick={() => removeCondition(index)}
                          className="text-red-500 hover:text-red-600 p-1"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {createTrigger.isError && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
                  Failed to create trigger:{" "}
                  {(createTrigger.error as Error)?.message || "Unknown error"}
                </div>
              )}
            </div>

            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createTrigger.isPending || !name || !pipelineId}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {createTrigger.isPending ? (
                  <>
                    <span className="animate-spin">⏳</span>
                    Creating...
                  </>
                ) : (
                  <>
                    <span>➕</span>
                    Create Trigger
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

function ExecutionHistoryPanel() {
  const { data: executions, isLoading, error } = useRecentExecutions(10);

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-red-500 dark:text-red-400">
        Failed to load execution history
      </div>
    );
  }

  if (!executions || executions.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <div className="text-4xl mb-2">📋</div>
        <div>No recent executions</div>
      </div>
    );
  }

  const statusColors: Record<string, string> = {
    pending: "text-yellow-600",
    running: "text-blue-600",
    success: "text-green-600",
    failed: "text-red-600",
    skipped: "text-gray-600",
  };

  const statusIcons: Record<string, string> = {
    pending: "⏳",
    running: "🔄",
    success: "✅",
    failed: "❌",
    skipped: "⏭️",
  };

  return (
    <div className="space-y-2">
      {executions.map((execution: TriggerExecution) => (
        <div
          key={execution.id}
          className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span>{statusIcons[execution.status]}</span>
              <span className="font-medium text-gray-900 dark:text-gray-100 text-sm">
                {execution.trigger_name}
              </span>
            </div>
            <span
              className={`text-xs capitalize ${statusColors[execution.status]}`}
            >
              {execution.status}
            </span>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {new Date(execution.started_at).toLocaleString()}
            {execution.duration_seconds !== undefined && (
              <span> • {execution.duration_seconds.toFixed(1)}s</span>
            )}
          </div>
          {execution.job_id && (
            <Link
              to={ROUTES.JOBS.DETAIL(execution.job_id)}
              className="text-xs text-blue-600 hover:text-blue-700 mt-1 inline-block"
            >
              View Job →
            </Link>
          )}
          {execution.error_message && (
            <div className="text-xs text-red-500 mt-1 truncate">
              {execution.error_message}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// Main Page Component
// ============================================================================

export function PipelineTriggersPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [eventFilter, setEventFilter] = useState<TriggerEvent | "all">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "enabled" | "disabled">("all");

  const { data: triggers, isLoading, error } = useTriggers({
    event: eventFilter === "all" ? undefined : eventFilter,
    status: statusFilter === "all" ? undefined : statusFilter,
  });
  const toggleTrigger = useToggleTrigger();
  const executeTrigger = useExecuteTrigger();
  const deleteTrigger = useDeleteTrigger();

  const handleToggle = async (id: string, enabled: boolean) => {
    await toggleTrigger.mutateAsync({ id, enabled });
  };

  const handleExecute = async (id: string) => {
    await executeTrigger.mutateAsync({ id });
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this trigger?")) {
      await deleteTrigger.mutateAsync(id);
    }
  };

  // Summary stats
  const stats = useMemo(() => {
    if (!triggers) return null;
    return {
      total: triggers.length,
      enabled: triggers.filter((t) => t.status === "enabled").length,
      totalExecutions: triggers.reduce((sum, t) => sum + t.total_executions, 0),
      avgSuccessRate:
        triggers.length > 0
          ? Math.round(
              triggers.reduce((sum, t) => sum + calculateSuccessRate(t), 0) /
                triggers.length
            )
          : 0,
    };
  }, [triggers]);

  const eventOptions: Array<{ value: TriggerEvent | "all"; label: string }> = [
    { value: "all", label: "All Events" },
    { value: "new_measurement_set", label: "📡 New Measurement Set" },
    { value: "calibration_complete", label: "✅ Calibration Complete" },
    { value: "schedule", label: "⏰ Scheduled" },
    { value: "manual", label: "👆 Manual" },
    { value: "data_quality_alert", label: "⚠️ Data Quality Alert" },
    { value: "storage_threshold", label: "💾 Storage Threshold" },
  ];

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Pipeline Triggers
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Automate pipeline execution based on events and schedules
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <span>➕</span>
              Create Trigger
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        {/* Stats Row */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {stats.total}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Total Triggers
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-center">
              <div className="text-2xl font-bold text-green-600">
                {stats.enabled}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Active
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {stats.totalExecutions.toLocaleString()}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Total Executions
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-center">
              <div
                className={`text-2xl font-bold ${
                  stats.avgSuccessRate >= 80
                    ? "text-green-600"
                    : stats.avgSuccessRate >= 50
                      ? "text-yellow-600"
                      : "text-red-600"
                }`}
              >
                {stats.avgSuccessRate}%
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Avg Success Rate
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Triggers List */}
          <div className="lg:col-span-2 space-y-4">
            {/* Filters */}
            <div className="flex gap-4">
              <select
                value={eventFilter}
                onChange={(e) =>
                  setEventFilter(e.target.value as TriggerEvent | "all")
                }
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                aria-label="Filter by event type"
              >
                {eventOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <select
                value={statusFilter}
                onChange={(e) =>
                  setStatusFilter(e.target.value as "all" | "enabled" | "disabled")
                }
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                aria-label="Filter by status"
              >
                <option value="all">All Status</option>
                <option value="enabled">Enabled</option>
                <option value="disabled">Disabled</option>
              </select>
            </div>

            {isLoading && (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="h-40 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse"
                  />
                ))}
              </div>
            )}

            {error && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
                Failed to load triggers: {(error as Error)?.message}
              </div>
            )}

            {triggers && triggers.length === 0 && (
              <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
                <div className="text-6xl mb-4">⚡</div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  No Triggers Yet
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mt-1">
                  Create your first trigger to automate pipeline execution
                </p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Create Trigger
                </button>
              </div>
            )}

            {triggers && triggers.length > 0 && (
              <div className="space-y-4">
                {triggers.map((trigger: PipelineTrigger) => (
                  <TriggerCard
                    key={trigger.id}
                    trigger={trigger}
                    onToggle={handleToggle}
                    onExecute={handleExecute}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Execution History */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Recent Executions
              </h3>
              <ExecutionHistoryPanel />
            </div>
          </div>
        </div>
      </main>

      {/* Create Modal */}
      <CreateTriggerModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />
    </div>
  );
}

export default PipelineTriggersPage;
