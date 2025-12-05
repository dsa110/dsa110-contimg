/**
 * BatchJobCard - Displays a single batch job with progress
 */
import { formatDistanceToNow } from "date-fns";
import type { BatchJob } from "@/types/batch";
import {
  getOperationLabel,
  getStatusLabel,
  getStatusColorClass,
  canCancelJob,
  canPauseJob,
  canResumeJob,
  canRetryJob,
} from "@/types/batch";

interface BatchJobCardProps {
  job: BatchJob;
  onSelect: (jobId: string) => void;
  onCancel: (jobId: string) => void;
  onPause: (jobId: string) => void;
  onResume: (jobId: string) => void;
  onRetry: (jobId: string) => void;
  isSelected?: boolean;
}

export function BatchJobCard({
  job,
  onSelect,
  onCancel,
  onPause,
  onResume,
  onRetry,
  isSelected = false,
}: BatchJobCardProps) {
  const timeAgo = formatDistanceToNow(new Date(job.submittedAt), {
    addSuffix: true,
  });

  return (
    <div
      className={`p-4 border rounded-lg cursor-pointer transition-colors ${
        isSelected
          ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
          : "border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
      }`}
      onClick={() => onSelect(job.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          onSelect(job.id);
        }
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <h4 className="font-medium text-gray-900 dark:text-white">
            {job.name}
          </h4>
          <p className="text-hint">
            {getOperationLabel(job.operationType)} • {job.items.length} items
          </p>
        </div>
        <span
          className={`px-2 py-1 text-xs font-medium rounded ${getStatusColorClass(
            job.status
          )}`}
        >
          {getStatusLabel(job.status)}
        </span>
      </div>

      {/* Progress bar */}
      {(job.status === "running" || job.status === "paused") && (
        <div className="mb-3">
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="text-muted">Progress</span>
            <span className="text-gray-900 dark:text-white">
              {job.progress}%
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${
                job.status === "paused" ? "bg-yellow-500" : "bg-primary-600"
              }`}
              style={{ width: `${job.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="flex items-center gap-4 text-hint mb-3">
        <span>{timeAgo}</span>
        {job.completedCount > 0 && (
          <span className="text-green-600 dark:text-green-400">
            {job.completedCount} completed
          </span>
        )}
        {job.failedCount > 0 && (
          <span className="text-red-600 dark:text-red-400">
            {job.failedCount} failed
          </span>
        )}
      </div>

      {/* Error message */}
      {job.error && (
        <p className="text-sm text-red-600 dark:text-red-400 mb-3 truncate">
          {job.error}
        </p>
      )}

      {/* Actions */}
      <div
        className="flex items-center gap-2"
        onClick={(e) => e.stopPropagation()}
      >
        {canPauseJob(job) && (
          <button
            type="button"
            onClick={() => onPause(job.id)}
            className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            Pause
          </button>
        )}
        {canResumeJob(job) && (
          <button
            type="button"
            onClick={() => onResume(job.id)}
            className="px-3 py-1 text-sm text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded"
          >
            Resume
          </button>
        )}
        {canRetryJob(job) && (
          <button
            type="button"
            onClick={() => onRetry(job.id)}
            className="px-3 py-1 text-sm text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded"
          >
            Retry Failed
          </button>
        )}
        {canCancelJob(job) && (
          <button
            type="button"
            onClick={() => onCancel(job.id)}
            className="px-3 py-1 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
