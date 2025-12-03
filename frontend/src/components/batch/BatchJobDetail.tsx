/**
 * BatchJobDetail - Detailed view of a single batch job
 */
import { formatDistanceToNow, format } from "date-fns";
import { useBatchStore } from "@/stores/batchStore";
import type { BatchItem } from "@/types/batch";
import {
  getOperationLabel,
  getStatusLabel,
  getStatusColorClass,
} from "@/types/batch";

interface BatchJobDetailProps {
  jobId: string;
}

function ItemStatusIcon({ status }: { status: BatchItem["status"] }) {
  switch (status) {
    case "completed":
      return (
        <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
            clipRule="evenodd"
          />
        </svg>
      );
    case "failed":
      return (
        <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
            clipRule="evenodd"
          />
        </svg>
      );
    case "processing":
      return (
        <svg className="w-4 h-4 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      );
    case "skipped":
      return (
        <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9a1 1 0 000 2h6a1 1 0 100-2H7z"
            clipRule="evenodd"
          />
        </svg>
      );
    default:
      return (
        <svg className="w-4 h-4 text-gray-300" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zm0-2a6 6 0 100-12 6 6 0 000 12z"
            clipRule="evenodd"
          />
        </svg>
      );
  }
}

export function BatchJobDetail({ jobId }: BatchJobDetailProps) {
  const job = useBatchStore((state) => state.getJob(jobId));

  if (!job) {
    return (
      <div className="text-center text-gray-500 dark:text-gray-400 py-8">
        Job not found
      </div>
    );
  }

  const submittedAt = new Date(job.submittedAt);

  return (
    <div className="space-y-6">
      {/* Job info */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
          {job.name}
        </h3>
        <div className="flex items-center gap-2 mb-4">
          <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusColorClass(job.status)}`}>
            {getStatusLabel(job.status)}
          </span>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {getOperationLabel(job.operationType)}
          </span>
        </div>

        {/* Progress */}
        {(job.status === "running" || job.status === "paused") && (
          <div className="mb-4">
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-600 dark:text-gray-400">Progress</span>
              <span className="text-gray-900 dark:text-white">
                {job.completedCount + job.failedCount} / {job.items.length}
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className="h-2 rounded-full bg-primary-600 transition-all"
                style={{ width: `${job.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Error */}
        {job.error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg mb-4">
            <p className="text-sm text-red-700 dark:text-red-400">{job.error}</p>
          </div>
        )}

        {/* Timestamps */}
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Submitted</dt>
            <dd className="text-gray-900 dark:text-white">
              {format(submittedAt, "MMM d, yyyy HH:mm")}
            </dd>
          </div>
          {job.startedAt && (
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Started</dt>
              <dd className="text-gray-900 dark:text-white">
                {formatDistanceToNow(new Date(job.startedAt), { addSuffix: true })}
              </dd>
            </div>
          )}
          {job.completedAt && (
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Completed</dt>
              <dd className="text-gray-900 dark:text-white">
                {format(new Date(job.completedAt), "MMM d, yyyy HH:mm")}
              </dd>
            </div>
          )}
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Submitted by</dt>
            <dd className="text-gray-900 dark:text-white">{job.submittedBy}</dd>
          </div>
        </dl>
      </div>

      {/* Items list */}
      <div>
        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
          Items ({job.items.length})
        </h4>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {job.items.map((item) => (
            <div
              key={item.id}
              className="flex items-center gap-3 p-2 bg-gray-50 dark:bg-gray-800 rounded"
            >
              <ItemStatusIcon status={item.status} />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-900 dark:text-white truncate">
                  {item.name}
                </p>
                {item.error && (
                  <p className="text-xs text-red-600 dark:text-red-400 truncate">
                    {item.error}
                  </p>
                )}
              </div>
              <span className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                {item.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
