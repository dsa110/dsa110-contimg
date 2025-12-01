/**
 * WorkflowsPage - ABSURD Workflow Manager Dashboard.
 *
 * Provides an overview of the ABSURD task queue system including:
 * - Queue statistics
 * - Active workers
 * - Recent tasks
 * - System health
 */

import React, { useState } from "react";
import {
  useTasks,
  useQueueStats,
  useWorkers,
  useAbsurdHealth,
  useCancelTask,
  useRetryTask,
} from "../hooks/useAbsurdQueries";
import type { Task, TaskStatus } from "../types/absurd";

// =============================================================================
// Helper Components
// =============================================================================

/**
 * Status badge with color coding.
 */
function StatusBadge({
  status,
  className = "",
}: {
  status: string;
  className?: string;
}) {
  const colors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    claimed: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    cancelled: "bg-gray-100 text-gray-800",
    retrying: "bg-orange-100 text-orange-800",
    healthy: "bg-green-100 text-green-800",
    degraded: "bg-yellow-100 text-yellow-800",
    unhealthy: "bg-red-100 text-red-800",
    active: "bg-green-100 text-green-800",
    idle: "bg-gray-100 text-gray-800",
    stale: "bg-yellow-100 text-yellow-800",
    crashed: "bg-red-100 text-red-800",
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        colors[status] || "bg-gray-100 text-gray-800"
      } ${className}`}
    >
      {status}
    </span>
  );
}

/**
 * Stat card component.
 */
function StatCard({
  label,
  value,
  variant = "default",
}: {
  label: string;
  value: number | string;
  variant?: "default" | "warning" | "error" | "success";
}) {
  const variantColors = {
    default: "bg-white border-gray-200",
    warning: "bg-yellow-50 border-yellow-200",
    error: "bg-red-50 border-red-200",
    success: "bg-green-50 border-green-200",
  };

  return (
    <div className={`rounded-lg border p-4 ${variantColors[variant]}`}>
      <div className="text-sm text-gray-500">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
    </div>
  );
}

/**
 * Loading skeleton.
 */
function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse bg-gray-200 rounded ${className}`}
      aria-hidden="true"
    />
  );
}

// =============================================================================
// Section Components
// =============================================================================

/**
 * Health status section.
 */
function HealthSection() {
  const { data: health, isLoading, error } = useAbsurdHealth();

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h2 className="text-lg font-semibold mb-3">System Health</h2>
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  if (error || !health) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <h2 className="text-lg font-semibold text-red-800 mb-2">
          System Health Unavailable
        </h2>
        <p className="text-sm text-red-600">
          Unable to fetch health status. The ABSURD service may not be running.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">System Health</h2>
        <StatusBadge status={health.status} />
      </div>
      <p className="text-sm text-gray-600 mb-3">{health.message}</p>
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Database:</span>
          <span
            className={`ml-2 ${
              health.database_available ? "text-green-600" : "text-red-600"
            }`}
          >
            {health.database_available ? "Connected" : "Disconnected"}
          </span>
        </div>
        <div>
          <span className="text-gray-500">Workers:</span>
          <span
            className={`ml-2 ${
              health.worker_pool_healthy ? "text-green-600" : "text-red-600"
            }`}
          >
            {health.worker_pool_healthy ? "Healthy" : "Unhealthy"}
          </span>
        </div>
        <div>
          <span className="text-gray-500">Queue Depth:</span>
          <span className="ml-2">{health.queue_depth}</span>
        </div>
      </div>
      {health.alerts.length > 0 && (
        <div className="mt-3 pt-3 border-t">
          <h3 className="text-sm font-medium text-red-800 mb-2">Alerts</h3>
          {health.alerts.map((alert, i) => (
            <div key={i} className="text-sm text-red-600">
              {alert.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Queue statistics section.
 */
function QueueStatsSection({ queueName }: { queueName: string }) {
  const { data: stats, isLoading } = useQueueStats(queueName);

  if (isLoading || !stats) {
    return (
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h2 className="text-lg font-semibold mb-3">Queue: {queueName}</h2>
        <div className="grid grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-4 mb-6">
      <h2 className="text-lg font-semibold mb-3">Queue: {queueName}</h2>
      <div className="grid grid-cols-5 gap-4">
        <StatCard
          label="Pending"
          value={stats.pending}
          variant={stats.pending > 100 ? "warning" : "default"}
        />
        <StatCard
          label="Processing"
          value={stats.claimed}
          variant={stats.claimed > 0 ? "success" : "default"}
        />
        <StatCard label="Completed" value={stats.completed} />
        <StatCard
          label="Failed"
          value={stats.failed}
          variant={stats.failed > 0 ? "error" : "default"}
        />
        <StatCard label="Total" value={stats.total} />
      </div>
    </div>
  );
}

/**
 * Workers section.
 */
function WorkersSection() {
  const { data, isLoading } = useWorkers();

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h2 className="text-lg font-semibold mb-3">Workers</h2>
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!data || data.workers.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h2 className="text-lg font-semibold mb-3">Workers</h2>
        <p className="text-sm text-gray-500">No workers connected</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Workers</h2>
        <div className="text-sm text-gray-500">
          {data.active} active / {data.total} total
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Worker ID
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                State
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Tasks
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Current Task
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                Uptime
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {data.workers.map((worker) => (
              <tr key={worker.worker_id}>
                <td className="px-3 py-2 text-sm font-mono">
                  {worker.worker_id.slice(0, 20)}...
                </td>
                <td className="px-3 py-2">
                  <StatusBadge status={worker.state} />
                </td>
                <td className="px-3 py-2 text-sm">{worker.task_count}</td>
                <td className="px-3 py-2 text-sm font-mono">
                  {worker.current_task_id
                    ? `${worker.current_task_id.slice(0, 8)}...`
                    : "-"}
                </td>
                <td className="px-3 py-2 text-sm">
                  {formatDuration(worker.uptime_seconds)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/**
 * Tasks list section.
 */
function TasksSection() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const { data, isLoading } = useTasks({
    status: statusFilter || undefined,
    limit: 20,
  });
  const cancelTask = useCancelTask();
  const retryTask = useRetryTask();

  const handleCancel = async (taskId: string) => {
    if (confirm("Are you sure you want to cancel this task?")) {
      cancelTask.mutate({ taskId, reason: "Cancelled by user" });
    }
  };

  const handleRetry = async (taskId: string) => {
    retryTask.mutate(taskId);
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Recent Tasks</h2>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-sm border rounded px-2 py-1"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="claimed">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : !data || data.tasks.length === 0 ? (
        <p className="text-sm text-gray-500 py-8 text-center">No tasks found</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead>
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Task ID
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Name
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Priority
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Created
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {data.tasks.map((task) => (
                <tr key={task.task_id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 text-sm font-mono">
                    {task.task_id.slice(0, 8)}...
                  </td>
                  <td className="px-3 py-2 text-sm">{task.task_name}</td>
                  <td className="px-3 py-2">
                    <StatusBadge status={task.status} />
                  </td>
                  <td className="px-3 py-2 text-sm">{task.priority}</td>
                  <td className="px-3 py-2 text-sm">
                    {task.created_at
                      ? new Date(task.created_at).toLocaleString()
                      : "-"}
                  </td>
                  <td className="px-3 py-2 text-sm">
                    <div className="flex gap-2">
                      {(task.status === "pending" ||
                        task.status === "claimed") && (
                        <button
                          onClick={() => handleCancel(task.task_id)}
                          className="text-red-600 hover:text-red-800 text-xs"
                          disabled={cancelTask.isPending}
                        >
                          Cancel
                        </button>
                      )}
                      {task.status === "failed" && (
                        <button
                          onClick={() => handleRetry(task.task_id)}
                          className="text-blue-600 hover:text-blue-800 text-xs"
                          disabled={retryTask.isPending}
                        >
                          Retry
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3 text-sm text-gray-500 text-right">
            Showing {data.tasks.length} of {data.total} tasks
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Format duration in seconds to human readable string.
 */
function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
}

// =============================================================================
// Main Component
// =============================================================================

/**
 * WorkflowsPage - Main dashboard for ABSURD workflow manager.
 */
export default function WorkflowsPage() {
  const defaultQueue = "dsa110-pipeline";

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Workflow Manager</h1>
        <p className="text-sm text-gray-500 mt-1">
          ABSURD durable task queue dashboard
        </p>
      </div>

      <HealthSection />
      <QueueStatsSection queueName={defaultQueue} />
      <WorkersSection />
      <TasksSection />
    </div>
  );
}
