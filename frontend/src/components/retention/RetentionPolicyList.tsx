/**
 * RetentionPolicyList Component
 *
 * Displays a filterable list of retention policies with summary statistics.
 */

import React, { useState } from "react";
import { RetentionPolicyCard } from "./RetentionPolicyCard";
import {
  useRetentionFilter,
  useRetentionStats,
} from "../../hooks/useRetention";
import type {
  RetentionPolicy,
  RetentionDataType,
  RetentionPolicyStatus,
  RetentionPriority,
} from "../../types/retention";
import {
  DATA_TYPE_LABELS,
  PRIORITY_LABELS,
  STATUS_LABELS,
  formatBytes,
} from "../../types/retention";

interface RetentionPolicyListProps {
  /** Callback when a policy is selected */
  onSelectPolicy?: (policy: RetentionPolicy) => void;
  /** Currently selected policy ID */
  selectedPolicyId?: string | null;
  /** Callback to edit a policy */
  onEditPolicy?: (policy: RetentionPolicy) => void;
  /** Callback to delete a policy */
  onDeletePolicy?: (policy: RetentionPolicy) => void;
  /** Callback to toggle policy status */
  onToggleStatus?: (policy: RetentionPolicy) => void;
  /** Callback to run simulation */
  onSimulate?: (policy: RetentionPolicy) => void;
  /** Callback to execute policy */
  onExecute?: (policy: RetentionPolicy) => void;
  /** Callback to create a new policy */
  onCreatePolicy?: () => void;
  /** Whether simulation is running for a policy */
  simulatingPolicyId?: string | null;
  /** Whether execution is running for a policy */
  executingPolicyId?: string | null;
  /** Show summary stats */
  showStats?: boolean;
  /** Compact mode */
  compact?: boolean;
}

export function RetentionPolicyList({
  onSelectPolicy,
  selectedPolicyId,
  onEditPolicy,
  onDeletePolicy,
  onToggleStatus,
  onSimulate,
  onExecute,
  onCreatePolicy,
  simulatingPolicyId,
  executingPolicyId,
  showStats = true,
  compact = false,
}: RetentionPolicyListProps) {
  const {
    filter,
    filteredPolicies,
    setStatusFilter,
    setDataTypeFilter,
    setPriorityFilter,
    setSearchFilter,
    clearFilter,
  } = useRetentionFilter();
  const stats = useRetentionStats();

  const [showFilters, setShowFilters] = useState(false);

  const dataTypes: RetentionDataType[] = [
    "measurement_set",
    "calibration",
    "image",
    "source_catalog",
    "job_log",
    "temporary",
  ];

  const statuses: RetentionPolicyStatus[] = [
    "active",
    "paused",
    "disabled",
    "expired",
  ];
  const priorities: RetentionPriority[] = ["critical", "high", "medium", "low"];

  const hasActiveFilters =
    (filter.status?.length ?? 0) > 0 ||
    (filter.dataType?.length ?? 0) > 0 ||
    (filter.priority?.length ?? 0) > 0 ||
    (filter.search?.length ?? 0) > 0;

  return (
    <div className="space-y-4">
      {/* Stats Summary */}
      {showStats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="stat-value">{stats.totalPolicies}</div>
            <div className="stat-label">Total Policies</div>
          </div>
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {stats.activePolicies}
            </div>
            <div className="stat-label">Active</div>
          </div>
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
              {stats.pausedPolicies}
            </div>
            <div className="stat-label">Paused</div>
          </div>
          <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {formatBytes(stats.spaceFreedLast30Days)}
            </div>
            <div className="stat-label">Freed (30 days)</div>
          </div>
        </div>
      )}

      {/* Search and Filter Bar */}
      <div className="flex flex-col md:flex-row gap-3">
        <div className="flex-1 relative">
          <input
            type="text"
            placeholder="Search policies..."
            value={filter.search || ""}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full px-4 py-2 pl-10 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <svg
            className="absolute left-3 top-2.5 w-5 h-5 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`px-4 py-2 border rounded-lg flex items-center gap-2 ${
            hasActiveFilters
              ? "border-blue-500 text-blue-600 dark:text-blue-400"
              : "border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300"
          }`}
        >
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
            />
          </svg>
          Filters
          {hasActiveFilters && (
            <span className="bg-blue-500 text-white text-xs px-1.5 py-0.5 rounded-full">
              {(filter.status?.length || 0) +
                (filter.dataType?.length || 0) +
                (filter.priority?.length || 0)}
            </span>
          )}
        </button>
        {onCreatePolicy && (
          <button
            onClick={onCreatePolicy}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
            New Policy
          </button>
        )}
      </div>

      {/* Expanded Filters */}
      {showFilters && (
        <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 space-y-4">
          {/* Status Filter */}
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
              Status
            </label>
            <div className="flex flex-wrap gap-2">
              {statuses.map((status) => (
                <button
                  key={status}
                  onClick={() => {
                    const current = filter.status || [];
                    setStatusFilter(
                      current.includes(status)
                        ? current.filter((s) => s !== status)
                        : [...current, status]
                    );
                  }}
                  className={`px-3 py-1 text-sm rounded-full border ${
                    filter.status?.includes(status)
                      ? "bg-blue-100 border-blue-500 text-blue-700 dark:bg-blue-900 dark:text-blue-200"
                      : "border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300"
                  }`}
                >
                  {STATUS_LABELS[status]}
                </button>
              ))}
            </div>
          </div>

          {/* Data Type Filter */}
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
              Data Type
            </label>
            <div className="flex flex-wrap gap-2">
              {dataTypes.map((type) => (
                <button
                  key={type}
                  onClick={() => {
                    const current = filter.dataType || [];
                    setDataTypeFilter(
                      current.includes(type)
                        ? current.filter((t) => t !== type)
                        : [...current, type]
                    );
                  }}
                  className={`px-3 py-1 text-sm rounded-full border ${
                    filter.dataType?.includes(type)
                      ? "bg-blue-100 border-blue-500 text-blue-700 dark:bg-blue-900 dark:text-blue-200"
                      : "border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300"
                  }`}
                >
                  {DATA_TYPE_LABELS[type]}
                </button>
              ))}
            </div>
          </div>

          {/* Priority Filter */}
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
              Priority
            </label>
            <div className="flex flex-wrap gap-2">
              {priorities.map((priority) => (
                <button
                  key={priority}
                  onClick={() => {
                    const current = filter.priority || [];
                    setPriorityFilter(
                      current.includes(priority)
                        ? current.filter((p) => p !== priority)
                        : [...current, priority]
                    );
                  }}
                  className={`px-3 py-1 text-sm rounded-full border ${
                    filter.priority?.includes(priority)
                      ? "bg-blue-100 border-blue-500 text-blue-700 dark:bg-blue-900 dark:text-blue-200"
                      : "border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300"
                  }`}
                >
                  {PRIORITY_LABELS[priority]}
                </button>
              ))}
            </div>
          </div>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <button
              onClick={clearFilter}
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
            >
              Clear all filters
            </button>
          )}
        </div>
      )}

      {/* Policy List */}
      {filteredPolicies.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <svg
            className="w-12 h-12 mx-auto mb-4 opacity-50"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <p className="text-lg font-medium">No retention policies found</p>
          <p className="text-sm mt-1">
            {hasActiveFilters
              ? "Try adjusting your filters"
              : "Create a new policy to get started"}
          </p>
          {onCreatePolicy && !hasActiveFilters && (
            <button
              onClick={onCreatePolicy}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Create Policy
            </button>
          )}
        </div>
      ) : (
        <div className={compact ? "space-y-2" : "space-y-4"}>
          {filteredPolicies.map((policy) => (
            <RetentionPolicyCard
              key={policy.id}
              policy={policy}
              isSelected={selectedPolicyId === policy.id}
              onSelect={onSelectPolicy}
              onEdit={onEditPolicy}
              onDelete={onDeletePolicy}
              onToggleStatus={onToggleStatus}
              onSimulate={onSimulate}
              onExecute={onExecute}
              isSimulating={simulatingPolicyId === policy.id}
              isExecuting={executingPolicyId === policy.id}
              compact={compact}
            />
          ))}
        </div>
      )}

      {/* Results count */}
      {filteredPolicies.length > 0 && (
        <div className="text-sm text-gray-500 dark:text-gray-400 text-center">
          Showing {filteredPolicies.length} of {stats.totalPolicies} policies
        </div>
      )}
    </div>
  );
}

export default RetentionPolicyList;
