/**
 * ConversionPage - HDF5 to Measurement Set Conversion Dashboard
 *
 * Provides an interface to:
 * 1. View conversion queue statistics
 * 2. Browse pending HDF5 groups
 * 3. Trigger on-demand conversions
 * 4. Monitor conversion progress
 *
 * Route: /conversion
 */

import React, { useState, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import { Card, LoadingSpinner } from "../components/common";
import {
  useConversionStats,
  usePendingGroups,
  useGroupStatus,
  useConvertGroup,
  useBulkConvert,
  type PendingGroup,
} from "../hooks/useConversion";
import { relativeTime } from "../utils/relativeTime";

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
    collecting: "bg-blue-100 text-blue-800",
    converting: "bg-purple-100 text-purple-800",
    processing: "bg-purple-100 text-purple-800",
    completed: "bg-green-100 text-green-800",
    converted: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    error: "bg-red-100 text-red-800",
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
  icon,
}: {
  label: string;
  value: number | string;
  variant?: "default" | "warning" | "error" | "success" | "info";
  icon?: React.ReactNode;
}) {
  const variantColors = {
    default: "bg-white border-gray-200",
    warning: "bg-yellow-50 border-yellow-200",
    error: "bg-red-50 border-red-200",
    success: "bg-green-50 border-green-200",
    info: "bg-blue-50 border-blue-200",
  };

  return (
    <div className={`rounded-lg border p-4 ${variantColors[variant]}`}>
      <div className="flex items-center gap-2">
        {icon}
        <div className="text-sm text-gray-500">{label}</div>
      </div>
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
 * Queue statistics section.
 */
function StatsSection() {
  const { data: stats, isLoading, error } = useConversionStats();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-red-600">
          Unable to fetch conversion statistics.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <StatCard
        label="Pending"
        value={stats.total_pending}
        variant={stats.total_pending > 10 ? "warning" : "default"}
        icon={
          <svg className="w-4 h-4 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        }
      />
      <StatCard
        label="Converting"
        value={stats.total_converting}
        variant={stats.total_converting > 0 ? "info" : "default"}
        icon={
          <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        }
      />
      <StatCard
        label="Converted Today"
        value={stats.total_converted_today}
        variant="success"
        icon={
          <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        }
      />
      <StatCard
        label="Failed Today"
        value={stats.total_failed_today}
        variant={stats.total_failed_today > 0 ? "error" : "default"}
        icon={
          <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        }
      />
    </div>
  );
}

/**
 * Single group row with convert button.
 */
function GroupRow({
  group,
  isSelected,
  onToggleSelect,
  onConvert,
  isConverting,
}: {
  group: PendingGroup;
  isSelected: boolean;
  onToggleSelect: () => void;
  onConvert: () => void;
  isConverting: boolean;
}) {
  const subbandDisplay = group.expected_subbands
    ? `${group.actual_subbands}/${group.expected_subbands}`
    : `${group.actual_subbands}`;

  const isComplete = group.is_complete;
  const canConvert = group.state === "pending" || group.state === "collecting";

  return (
    <tr className={isSelected ? "bg-blue-50" : ""}>
      <td className="px-3 py-3">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggleSelect}
          className="h-4 w-4 text-blue-600 rounded"
          disabled={!canConvert}
        />
      </td>
      <td className="px-4 py-3">
        <div className="font-medium text-gray-900">{group.group_id}</div>
        {group.calibrators && (
          <div className="text-xs text-gray-500">
            Calibrator: {group.calibrators}
          </div>
        )}
      </td>
      <td className="px-4 py-3 text-center">
        <StatusBadge status={group.state} />
      </td>
      <td className="px-4 py-3 text-center">
        <span
          className={`font-medium ${
            isComplete ? "text-green-600" : "text-yellow-600"
          }`}
        >
          {subbandDisplay} SB
        </span>
        {isComplete && (
          <span className="ml-1 text-green-500" title="Complete">
            ✓
          </span>
        )}
      </td>
      <td className="px-4 py-3 text-right text-sm text-gray-500">
        {relativeTime(group.received_at)}
      </td>
      <td className="px-4 py-3 text-center">
        <button
          onClick={onConvert}
          disabled={!canConvert || isConverting}
          className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
            canConvert && !isConverting
              ? "bg-blue-600 text-white hover:bg-blue-700"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
          title={canConvert ? "Start conversion" : "Already processing"}
        >
          {isConverting ? (
            <span className="flex items-center gap-1">
              <LoadingSpinner size="sm" />
              Converting...
            </span>
          ) : (
            "Convert"
          )}
        </button>
      </td>
    </tr>
  );
}

/**
 * Pending groups table section.
 */
function PendingGroupsSection() {
  const [selectedGroups, setSelectedGroups] = useState<Set<string>>(new Set());
  const [convertingGroups, setConvertingGroups] = useState<Set<string>>(new Set());
  const [showCompleteOnly, setShowCompleteOnly] = useState(false);
  const [sinceHours, setSinceHours] = useState(168); // 7 days

  const {
    data: pendingData,
    isLoading,
    error,
    refetch,
  } = usePendingGroups(100, showCompleteOnly, false, sinceHours);

  const convertGroup = useConvertGroup();
  const bulkConvert = useBulkConvert();

  const groups = pendingData?.groups ?? [];
  const convertableGroups = useMemo(
    () => groups.filter((g) => g.state === "pending" || g.state === "collecting"),
    [groups]
  );

  const handleToggleSelect = useCallback((groupId: string) => {
    setSelectedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    if (selectedGroups.size === convertableGroups.length) {
      setSelectedGroups(new Set());
    } else {
      setSelectedGroups(new Set(convertableGroups.map((g) => g.group_id)));
    }
  }, [selectedGroups.size, convertableGroups]);

  const handleConvert = useCallback(
    async (groupId: string) => {
      setConvertingGroups((prev) => new Set(prev).add(groupId));
      try {
        await convertGroup.mutateAsync({ group_id: groupId });
      } finally {
        setConvertingGroups((prev) => {
          const next = new Set(prev);
          next.delete(groupId);
          return next;
        });
      }
    },
    [convertGroup]
  );

  const handleBulkConvert = useCallback(async () => {
    const groupIds = Array.from(selectedGroups);
    if (groupIds.length === 0) return;

    setConvertingGroups(new Set(groupIds));
    try {
      await bulkConvert.mutateAsync(groupIds);
      setSelectedGroups(new Set());
    } finally {
      setConvertingGroups(new Set());
    }
  }, [selectedGroups, bulkConvert]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <Skeleton className="h-8 w-48 mb-4" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-sm text-red-600">
          Unable to fetch pending groups. The conversion API may not be running.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold">
            Pending HDF5 Groups
            <span className="ml-2 text-sm font-normal text-gray-500">
              ({pendingData?.total ?? 0} total, {pendingData?.complete_count ?? 0} complete)
            </span>
          </h2>
          {selectedGroups.size > 0 && (
            <span className="text-sm text-blue-600">
              {selectedGroups.size} selected
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {/* Time range filter */}
          <select
            value={sinceHours}
            onChange={(e) => setSinceHours(Number(e.target.value))}
            className="text-sm border border-gray-300 rounded px-2 py-1"
          >
            <option value={24}>Last 24 hours</option>
            <option value={72}>Last 3 days</option>
            <option value={168}>Last 7 days</option>
            <option value={720}>Last 30 days</option>
          </select>
          {/* Complete only toggle */}
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={showCompleteOnly}
              onChange={(e) => setShowCompleteOnly(e.target.checked)}
              className="h-4 w-4 text-blue-600 rounded"
            />
            Complete only
          </label>
          {/* Bulk convert button */}
          {selectedGroups.size > 0 && (
            <button
              onClick={handleBulkConvert}
              disabled={bulkConvert.isPending}
              className="px-4 py-1.5 rounded text-sm font-medium bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
            >
              {bulkConvert.isPending ? (
                <span className="flex items-center gap-1">
                  <LoadingSpinner size="sm" />
                  Converting...
                </span>
              ) : (
                `Convert ${selectedGroups.size} Selected`
              )}
            </button>
          )}
          {/* Refresh button */}
          <button
            onClick={() => refetch()}
            className="p-1.5 text-gray-500 hover:text-gray-700 rounded hover:bg-gray-100"
            title="Refresh"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      {/* Table */}
      {groups.length > 0 ? (
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="w-10 px-3 py-3">
                <input
                  type="checkbox"
                  checked={
                    selectedGroups.size === convertableGroups.length &&
                    convertableGroups.length > 0
                  }
                  ref={(el) => {
                    if (el)
                      el.indeterminate =
                        selectedGroups.size > 0 &&
                        selectedGroups.size < convertableGroups.length;
                  }}
                  onChange={handleSelectAll}
                  className="h-4 w-4 text-blue-600 rounded"
                />
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Group ID
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                State
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Subbands
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Received
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {groups.map((group) => (
              <GroupRow
                key={group.group_id}
                group={group}
                isSelected={selectedGroups.has(group.group_id)}
                onToggleSelect={() => handleToggleSelect(group.group_id)}
                onConvert={() => handleConvert(group.group_id)}
                isConverting={convertingGroups.has(group.group_id)}
              />
            ))}
          </tbody>
        </table>
      ) : (
        <div className="px-4 py-8 text-center text-gray-500">
          <svg
            className="w-12 h-12 mx-auto mb-3 text-gray-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
            />
          </svg>
          <p>No pending HDF5 groups found</p>
          <p className="text-sm text-gray-400 mt-1">
            New data will appear here automatically
          </p>
        </div>
      )}
    </div>
  );
}

/**
 * Active conversions section showing in-progress jobs.
 */
function ActiveConversionsSection() {
  const { data: stats } = useConversionStats();

  if (!stats || stats.total_converting === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow p-4 mb-6">
      <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
        <svg className="w-5 h-5 text-purple-500 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Active Conversions
        <span className="text-sm font-normal text-gray-500">
          ({stats.total_converting} in progress)
        </span>
      </h2>
      <p className="text-sm text-gray-600">
        Conversion jobs are running in the background. Refresh the pending groups list to see updated statuses.
      </p>
    </div>
  );
}

// =============================================================================
// Main Page Component
// =============================================================================

const ConversionPage: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          HDF5 → MS Conversion
        </h1>
        <p className="text-gray-600 mt-1">
          Convert raw HDF5 subband files to Measurement Sets for imaging
        </p>
      </div>

      {/* Stats Cards */}
      <StatsSection />

      {/* Active Conversions */}
      <ActiveConversionsSection />

      {/* Pending Groups Table */}
      <PendingGroupsSection />

      {/* Help Section */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-800 mb-2">
          How it works
        </h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>
            • <strong>Pending:</strong> HDF5 files are waiting to be converted
          </li>
          <li>
            • <strong>Complete groups</strong> (16/16 subbands) are ready for immediate conversion
          </li>
          <li>
            • <strong>Partial groups</strong> may still be receiving data
          </li>
          <li>
            • Click <strong>Convert</strong> to start a conversion job, or select multiple and use <strong>Convert Selected</strong>
          </li>
          <li>
            • Converted MS files appear in the{" "}
            <Link to="/jobs" className="underline hover:text-blue-800">
              Jobs
            </Link>{" "}
            list and can be used for{" "}
            <Link to="/calibrator-imaging" className="underline hover:text-blue-800">
              Imaging
            </Link>
          </li>
        </ul>
      </div>
    </div>
  );
};

export default ConversionPage;
