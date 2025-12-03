import React, { useMemo, useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ROUTES } from "../../constants/routes";
import apiClient from "../../api/client";

// =============================================================================
// Types
// =============================================================================

/**
 * ABSURD task status values.
 */
export type TaskStatus =
  | "pending"
  | "claimed"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

/**
 * Pipeline stage identifier - matches backend task_name values.
 */
export type PipelineStage =
  | "convert-uvh5-to-ms"
  | "calibration-solve"
  | "calibration-apply"
  | "imaging"
  | "validation"
  | "crossmatch"
  | "photometry"
  | "catalog-setup"
  | "organize-files";

/**
 * Status counts for a single pipeline stage.
 */
export interface StageStatusCounts {
  pending: number;
  running: number;
  completed: number;
  failed: number;
}

/**
 * Pipeline status response from /absurd/status endpoint.
 */
export interface PipelineStatusResponse {
  stages: Record<PipelineStage, StageStatusCounts>;
  total: StageStatusCounts;
  worker_count: number;
  last_updated: string;
  is_healthy: boolean;
}

/**
 * Stage metadata for display.
 */
interface StageMetadata {
  id: PipelineStage;
  label: string;
  shortLabel: string;
  description: string;
  icon: string;
}

// =============================================================================
// Constants
// =============================================================================

/**
 * Pipeline stages in execution order with display metadata.
 */
const PIPELINE_STAGES: StageMetadata[] = [
  {
    id: "convert-uvh5-to-ms",
    label: "UVH5 -> MS",
    shortLabel: "Convert",
    description: "Convert UVH5 files to Measurement Sets",
    icon: "1",
  },
  {
    id: "calibration-solve",
    label: "Cal Solve",
    shortLabel: "CalSolve",
    description: "Solve for calibration solutions",
    icon: "2",
  },
  {
    id: "calibration-apply",
    label: "Cal Apply",
    shortLabel: "CalApply",
    description: "Apply calibration to target data",
    icon: "3",
  },
  {
    id: "imaging",
    label: "Imaging",
    shortLabel: "Image",
    description: "Create FITS images with WSClean/tclean",
    icon: "4",
  },
  {
    id: "validation",
    label: "Validation",
    shortLabel: "Valid",
    description: "Validate image quality metrics",
    icon: "5",
  },
  {
    id: "crossmatch",
    label: "Crossmatch",
    shortLabel: "XMatch",
    description: "Cross-match sources with catalogs",
    icon: "6",
  },
  {
    id: "photometry",
    label: "Photometry",
    shortLabel: "Phot",
    description: "Extract source flux measurements",
    icon: "7",
  },
  {
    id: "catalog-setup",
    label: "Catalog",
    shortLabel: "Catalog",
    description: "Register sources in catalog",
    icon: "8",
  },
  {
    id: "organize-files",
    label: "Organize",
    shortLabel: "Files",
    description: "Archive and organize output files",
    icon: "9",
  },
];

/**
 * Default empty status counts.
 */
const EMPTY_COUNTS: StageStatusCounts = {
  pending: 0,
  running: 0,
  completed: 0,
  failed: 0,
};

// =============================================================================
// API Hook
// =============================================================================

/**
 * Fetch pipeline status from ABSURD endpoint.
 */
async function fetchPipelineStatus(): Promise<PipelineStatusResponse> {
  const response = await apiClient.get<PipelineStatusResponse>("/absurd/status", {
    // Override base URL to hit ABSURD routes even when apiClient default is /api
    baseURL: "/absurd",
  });
  return response.data;
}

/**
 * Hook to fetch pipeline status with polling.
 */
export function usePipelineStatus(pollInterval = 30000) {
  return useQuery({
    queryKey: ["absurd", "status"],
    queryFn: fetchPipelineStatus,
    refetchInterval: pollInterval,
    staleTime: 10000,
    retry: 2,
    // Return mock data if ABSURD is not enabled yet
    placeholderData: {
      stages: Object.fromEntries(
        PIPELINE_STAGES.map((s) => [s.id, EMPTY_COUNTS])
      ) as Record<PipelineStage, StageStatusCounts>,
      total: EMPTY_COUNTS,
      worker_count: 0,
      last_updated: new Date().toISOString(),
      is_healthy: false,
    },
  });
}

// =============================================================================
// Sub-components
// =============================================================================

interface StatusIndicatorProps {
  counts: StageStatusCounts;
  size?: "sm" | "md";
}

/**
 * Compact status indicator dots showing task counts.
 */
function StatusIndicator({ counts, size = "md" }: StatusIndicatorProps) {
  const total =
    counts.pending + counts.running + counts.completed + counts.failed;
  if (total === 0) {
    return <span className="text-gray-400 text-xs">—</span>;
  }

  const dotSize = size === "sm" ? "w-2 h-2" : "w-2.5 h-2.5";

  return (
    <div className="flex items-center gap-1 text-xs">
      {counts.completed > 0 && (
        <span
          className="flex items-center gap-0.5"
          title={`${counts.completed} completed`}
        >
          <span className={`${dotSize} rounded-full bg-green-500`} />
          <span className="text-green-700 dark:text-green-400">
            {counts.completed}
          </span>
        </span>
      )}
      {counts.running > 0 && (
        <span
          className="flex items-center gap-0.5"
          title={`${counts.running} running`}
        >
          <span
            className={`${dotSize} rounded-full bg-blue-500 animate-pulse`}
          />
          <span className="text-blue-700 dark:text-blue-400">
            {counts.running}
          </span>
        </span>
      )}
      {counts.pending > 0 && (
        <span
          className="flex items-center gap-0.5"
          title={`${counts.pending} pending`}
        >
          <span className={`${dotSize} rounded-full bg-gray-400`} />
          <span className="text-gray-600 dark:text-gray-400">
            {counts.pending}
          </span>
        </span>
      )}
      {counts.failed > 0 && (
        <span
          className="flex items-center gap-0.5"
          title={`${counts.failed} failed`}
        >
          <span className={`${dotSize} rounded-full bg-red-500`} />
          <span className="text-red-700 dark:text-red-400">
            {counts.failed}
          </span>
        </span>
      )}
    </div>
  );
}

interface StageNodeProps {
  stage: StageMetadata;
  counts: StageStatusCounts;
  isFirst?: boolean;
  isLast?: boolean;
}

/**
 * Single pipeline stage node with status indicators.
 */
function StageNode({ stage, counts, isFirst, isLast }: StageNodeProps) {
  const total =
    counts.pending + counts.running + counts.completed + counts.failed;
  const hasActivity = total > 0;
  const hasFailures = counts.failed > 0;
  const isRunning = counts.running > 0;

  // Determine border color based on status
  let borderClass = "border-gray-200 dark:border-gray-700";
  if (hasFailures) {
    borderClass = "border-red-300 dark:border-red-500/50";
  } else if (isRunning) {
    borderClass = "border-blue-300 dark:border-blue-500/50";
  } else if (hasActivity) {
    borderClass = "border-green-200 dark:border-green-500/30";
  }

  return (
    <div className="flex items-center">
      {/* Connector line before */}
      {!isFirst && (
        <div className="w-4 h-0.5 bg-gray-300 dark:bg-gray-600 -mr-px" />
      )}

      {/* Stage box */}
      <Link
        to={`${ROUTES.JOBS.LIST}?stage=${stage.id}`}
        className={`
          relative flex flex-col items-center p-2 rounded-lg border-2 
          ${borderClass}
          bg-white dark:bg-gray-800
          hover:shadow-md hover:border-blue-400 dark:hover:border-blue-500
          transition-all duration-200 min-w-[70px]
          group
        `}
        title={stage.description}
      >
        {/* Icon */}
        <span className="text-lg mb-1">{stage.icon}</span>

        {/* Label */}
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300 text-center leading-tight">
          {stage.shortLabel}
        </span>

        {/* Status counts */}
        <div className="mt-1">
          <StatusIndicator counts={counts} size="sm" />
        </div>

        {/* Running pulse indicator */}
        {isRunning && (
          <span className="absolute -top-1 -right-1 w-3 h-3 bg-blue-500 rounded-full animate-ping opacity-75" />
        )}

        {/* Tooltip on hover */}
        <div
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 
                        bg-gray-900 text-white text-xs rounded shadow-lg 
                        opacity-0 group-hover:opacity-100 transition-opacity
                        whitespace-nowrap pointer-events-none z-10"
        >
          {stage.label}: {total} tasks
        </div>
      </Link>

      {/* Arrow after */}
      {!isLast && (
        <div className="flex items-center">
          <div className="w-3 h-0.5 bg-gray-300 dark:bg-gray-600" />
          <div
            className="w-0 h-0 border-t-4 border-b-4 border-l-4 
                          border-transparent border-l-gray-300 dark:border-l-gray-600"
          />
        </div>
      )}
    </div>
  );
}

interface SummaryBarProps {
  total: StageStatusCounts;
  workerCount: number;
  isHealthy: boolean;
}

/**
 * Summary bar showing totals and worker status.
 */
function SummaryBar({ total, workerCount, isHealthy }: SummaryBarProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 text-sm">
      {/* Task counts */}
      <div className="flex flex-wrap items-center gap-4">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-gray-400" />
          <span className="text-gray-600 dark:text-gray-400">
            {total.pending} pending
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse" />
          <span className="text-blue-700 dark:text-blue-400">
            {total.running} running
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
          <span className="text-green-700 dark:text-green-400">
            {total.completed} completed
          </span>
        </span>
        {total.failed > 0 && (
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span className="text-red-700 dark:text-red-400">
              {total.failed} failed
            </span>
          </span>
        )}
      </div>

      {/* Worker status */}
      <div className="flex items-center gap-3">
        <span className="text-gray-500 dark:text-gray-400">
          {workerCount} worker{workerCount !== 1 ? "s" : ""}
        </span>
        <span
          className={`px-2 py-0.5 rounded text-xs font-medium ${
            isHealthy
              ? "bg-green-100 text-green-800 dark:bg-green-500/20 dark:text-green-400"
              : "bg-yellow-100 text-yellow-800 dark:bg-yellow-500/20 dark:text-yellow-400"
          }`}
        >
          {isHealthy ? "Healthy" : "Degraded"}
        </span>
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export interface PipelineStatusPanelProps {
  /** Polling interval in ms (default: 30000) */
  pollInterval?: number;
  /** Show compact version (fewer stages visible) */
  compact?: boolean;
  /** Custom CSS class */
  className?: string;
}

/**
 * Pipeline status visualization panel.
 *
 * Displays the ABSURD workflow stages with real-time task status counts.
 * Each stage shows pending/running/completed/failed counts and links
 * to the Jobs list filtered by that stage.
 *
 * @example
 * ```tsx
 * <PipelineStatusPanel pollInterval={15000} />
 * ```
 */
export function PipelineStatusPanel({
  pollInterval = 30000,
  compact = false,
  className = "",
}: PipelineStatusPanelProps) {
  const { data, isLoading, isError, dataUpdatedAt, refetch, isFetching } =
    usePipelineStatus(pollInterval);

  // Stages to display (compact mode shows fewer)
  const visibleStages = useMemo(() => {
    if (compact) {
      // Show only the 5 main stages in compact mode
      return PIPELINE_STAGES.filter((s) =>
        [
          "convert-uvh5-to-ms",
          "calibration-apply",
          "imaging",
          "validation",
          "organize-files",
        ].includes(s.id)
      );
    }
    return PIPELINE_STAGES;
  }, [compact]);

  // Track current time for relative time display
  const [now, setNow] = useState(Date.now());

  // Update current time periodically for relative time display
  React.useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(interval);
  }, []);

  // Format last updated time
  const lastUpdatedStr = useMemo(() => {
    if (!dataUpdatedAt) return "";
    const seconds = Math.floor((now - dataUpdatedAt) / 1000);
    if (seconds < 5) return "just now";
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ago`;
  }, [dataUpdatedAt]);

  if (isError) {
    return (
      <div className={`card p-4 ${className}`}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Pipeline Status
          </h3>
          <button
            onClick={() => refetch()}
            className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400"
          >
            Retry
          </button>
        </div>
        <div className="text-center py-8 text-gray-500">
          <p className="mb-2">Unable to load pipeline status</p>
          <p className="text-xs text-gray-400">
            ABSURD workflow manager may not be enabled yet
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`card p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Pipeline Status
        </h3>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          {isFetching && <span className="animate-pulse">Updating...</span>}
          {lastUpdatedStr && !isFetching && (
            <span>Updated {lastUpdatedStr}</span>
          )}
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            title="Refresh"
          >
            <svg
              className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      )}

      {/* Pipeline visualization */}
      {!isLoading && data && (
        <>
          {/* Stage nodes */}
          <div className="overflow-x-auto pb-2 mb-4">
            <div className="flex items-center justify-center min-w-max px-2">
              {visibleStages.map((stage, index) => (
                <StageNode
                  key={stage.id}
                  stage={stage}
                  counts={data.stages[stage.id] || EMPTY_COUNTS}
                  isFirst={index === 0}
                  isLast={index === visibleStages.length - 1}
                />
              ))}
            </div>
          </div>

          {/* Divider */}
          <hr className="border-gray-200 dark:border-gray-700 mb-3" />

          {/* Summary bar */}
          <SummaryBar
            total={data.total}
            workerCount={data.worker_count}
            isHealthy={data.is_healthy}
          />
        </>
      )}
    </div>
  );
}

export default PipelineStatusPanel;
