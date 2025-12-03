/**
 * RetentionPolicyCard Component
 *
 * Displays a single retention policy with status, rules, and actions.
 */

import React from "react";
import { formatDistanceToNow } from "date-fns";
import type { RetentionPolicy } from "../../types/retention";
import {
  DATA_TYPE_LABELS,
  PRIORITY_LABELS,
  STATUS_LABELS,
  formatBytes,
} from "../../types/retention";

interface RetentionPolicyCardProps {
  /** The retention policy to display */
  policy: RetentionPolicy;
  /** Whether this policy is selected */
  isSelected?: boolean;
  /** Callback when policy is selected */
  onSelect?: (policy: RetentionPolicy) => void;
  /** Callback to edit policy */
  onEdit?: (policy: RetentionPolicy) => void;
  /** Callback to delete policy */
  onDelete?: (policy: RetentionPolicy) => void;
  /** Callback to toggle policy status */
  onToggleStatus?: (policy: RetentionPolicy) => void;
  /** Callback to run simulation */
  onSimulate?: (policy: RetentionPolicy) => void;
  /** Callback to execute policy */
  onExecute?: (policy: RetentionPolicy) => void;
  /** Whether simulation is running */
  isSimulating?: boolean;
  /** Whether execution is running */
  isExecuting?: boolean;
  /** Compact display mode */
  compact?: boolean;
}

/**
 * Status badge colors
 */
const statusColors: Record<RetentionPolicy["status"], string> = {
  active: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  paused:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  disabled: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
  expired: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

/**
 * Priority badge colors
 */
const priorityColors: Record<RetentionPolicy["priority"], string> = {
  low: "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300",
  medium: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-200",
  critical: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200",
};

export function RetentionPolicyCard({
  policy,
  isSelected = false,
  onSelect,
  onEdit,
  onDelete,
  onToggleStatus,
  onSimulate,
  onExecute,
  isSimulating = false,
  isExecuting = false,
  compact = false,
}: RetentionPolicyCardProps) {
  const handleClick = () => {
    onSelect?.(policy);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit?.(policy);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.(policy);
  };

  const handleToggleStatus = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleStatus?.(policy);
  };

  const handleSimulate = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSimulate?.(policy);
  };

  const handleExecute = (e: React.MouseEvent) => {
    e.stopPropagation();
    onExecute?.(policy);
  };

  const enabledRules = policy.rules.filter((r) => r.enabled);

  if (compact) {
    return (
      <div
        className={`
          p-3 rounded-lg border cursor-pointer transition-all
          ${
            isSelected
              ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
              : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
          }
        `}
        onClick={handleClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && handleClick()}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm text-gray-900 dark:text-gray-100">
              {policy.name}
            </span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                statusColors[policy.status]
              }`}
            >
              {STATUS_LABELS[policy.status]}
            </span>
          </div>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {DATA_TYPE_LABELS[policy.dataType]}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`
        p-4 rounded-lg border cursor-pointer transition-all
        ${
          isSelected
            ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 ring-2 ring-blue-200 dark:ring-blue-800"
            : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 bg-white dark:bg-gray-800"
        }
      `}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && handleClick()}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
            {policy.name}
          </h3>
          {policy.description && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              {policy.description}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`text-xs px-2 py-1 rounded-full ${
              priorityColors[policy.priority]
            }`}
          >
            {PRIORITY_LABELS[policy.priority]}
          </span>
          <span
            className={`text-xs px-2 py-1 rounded-full ${
              statusColors[policy.status]
            }`}
          >
            {STATUS_LABELS[policy.status]}
          </span>
        </div>
      </div>

      {/* Info */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3 text-sm">
        <div>
          <span className="text-gray-500 dark:text-gray-400">Data Type</span>
          <p className="font-medium text-gray-900 dark:text-gray-100">
            {DATA_TYPE_LABELS[policy.dataType]}
          </p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">Active Rules</span>
          <p className="font-medium text-gray-900 dark:text-gray-100">
            {enabledRules.length} / {policy.rules.length}
          </p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">
            Last Executed
          </span>
          <p className="font-medium text-gray-900 dark:text-gray-100">
            {policy.lastExecutedAt
              ? formatDistanceToNow(new Date(policy.lastExecutedAt), {
                  addSuffix: true,
                })
              : "Never"}
          </p>
        </div>
        <div>
          <span className="text-gray-500 dark:text-gray-400">
            Next Scheduled
          </span>
          <p className="font-medium text-gray-900 dark:text-gray-100">
            {policy.nextScheduledAt
              ? formatDistanceToNow(new Date(policy.nextScheduledAt), {
                  addSuffix: true,
                })
              : "Not scheduled"}
          </p>
        </div>
      </div>

      {/* Rules Summary */}
      {enabledRules.length > 0 && (
        <div className="mb-3">
          <span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Rules
          </span>
          <div className="mt-1 flex flex-wrap gap-2">
            {enabledRules.map((rule) => (
              <span
                key={rule.id}
                className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded"
                title={rule.description}
              >
                {rule.name}: {rule.threshold} {rule.thresholdUnit} →{" "}
                {rule.action}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* File Pattern */}
      {policy.filePattern && (
        <div className="mb-3 text-sm">
          <span className="text-gray-500 dark:text-gray-400">Pattern: </span>
          <code className="text-xs bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded">
            {policy.filePattern}
          </code>
        </div>
      )}

      {/* Size Constraints */}
      {(policy.minFileSize || policy.maxFileSize) && (
        <div className="mb-3 text-sm text-gray-500 dark:text-gray-400">
          Size:{" "}
          {policy.minFileSize ? `>${formatBytes(policy.minFileSize)}` : ""}
          {policy.minFileSize && policy.maxFileSize ? " - " : ""}
          {policy.maxFileSize ? `<${formatBytes(policy.maxFileSize)}` : ""}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
          {policy.requireConfirmation && (
            <span
              className="flex items-center gap-1"
              title="Requires confirmation"
            >
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              Confirm
            </span>
          )}
          {policy.createBackupBeforeDelete && (
            <span
              className="flex items-center gap-1 ml-2"
              title="Creates backup before delete"
            >
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"
                />
              </svg>
              Backup
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {onSimulate && (
            <button
              onClick={handleSimulate}
              disabled={isSimulating}
              className="text-xs px-2 py-1 text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 disabled:opacity-50"
              title="Run simulation"
            >
              {isSimulating ? "Simulating..." : "Simulate"}
            </button>
          )}
          {onExecute && policy.status === "active" && (
            <button
              onClick={handleExecute}
              disabled={isExecuting}
              className="text-xs px-2 py-1 text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300 disabled:opacity-50"
              title="Execute policy"
            >
              {isExecuting ? "Running..." : "Execute"}
            </button>
          )}
          {onToggleStatus && (
            <button
              onClick={handleToggleStatus}
              className={`text-xs px-2 py-1 ${
                policy.status === "active"
                  ? "text-yellow-600 hover:text-yellow-700 dark:text-yellow-400 dark:hover:text-yellow-300"
                  : "text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300"
              }`}
              title={
                policy.status === "active" ? "Pause policy" : "Activate policy"
              }
            >
              {policy.status === "active" ? "Pause" : "Activate"}
            </button>
          )}
          {onEdit && (
            <button
              onClick={handleEdit}
              className="text-xs px-2 py-1 text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              title="Edit policy"
            >
              Edit
            </button>
          )}
          {onDelete && (
            <button
              onClick={handleDelete}
              className="text-xs px-2 py-1 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
              title="Delete policy"
            >
              Delete
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default RetentionPolicyCard;
