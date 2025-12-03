/**
 * BatchJobList - List of batch jobs with filtering
 */
import { useBatchStore } from "@/stores/batchStore";
import { BatchJobCard } from "./BatchJobCard";

export function BatchJobList() {
  const {
    getFilteredJobs,
    selectedJobId,
    selectJob,
    cancelJob,
    pauseJob,
    resumeJob,
    retryJob,
    getStats,
  } = useBatchStore();

  const jobs = getFilteredJobs();
  const stats = getStats();

  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
        <svg
          className="w-12 h-12 mb-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
          />
        </svg>
        <p className="text-sm">No batch jobs</p>
        <p className="text-xs mt-1">Select items and start a batch operation</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats summary */}
      <div className="flex items-center gap-4 text-sm">
        <span className="text-gray-600 dark:text-gray-400">
          {stats.total} total
        </span>
        {stats.running > 0 && (
          <span className="text-blue-600 dark:text-blue-400">
            {stats.running} running
          </span>
        )}
        {stats.queued > 0 && (
          <span className="text-gray-600 dark:text-gray-400">
            {stats.queued} queued
          </span>
        )}
      </div>

      {/* Job list */}
      <div className="space-y-3">
        {jobs.map((job) => (
          <BatchJobCard
            key={job.id}
            job={job}
            isSelected={selectedJobId === job.id}
            onSelect={selectJob}
            onCancel={cancelJob}
            onPause={pauseJob}
            onResume={resumeJob}
            onRetry={retryJob}
          />
        ))}
      </div>
    </div>
  );
}
