/**
 * Batch operations store using Zustand
 * Manages batch job state, tracking, and actions
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  BatchJob,
  BatchJobStatus,
  BatchJobFilters,
  BatchJobStats,
  CreateBatchJobRequest,
  BatchItem,
} from "@/types/batch";

/**
 * Maximum number of completed jobs to keep in history
 */
const MAX_JOB_HISTORY = 50;

/**
 * Batch operations store state
 */
interface BatchState {
  /** Active and recent batch jobs */
  jobs: BatchJob[];
  /** Current filters */
  filters: BatchJobFilters;
  /** Selected job ID for detail view */
  selectedJobId: string | null;
  /** Whether the batch panel is open */
  isPanelOpen: boolean;
}

/**
 * Batch operations store actions
 */
interface BatchActions {
  /** Create a new batch job */
  createJob: (request: CreateBatchJobRequest) => BatchJob;
  /** Update a job's status */
  updateJobStatus: (jobId: string, status: BatchJobStatus, error?: string) => void;
  /** Update a job's progress */
  updateJobProgress: (
    jobId: string,
    progress: number,
    completedCount: number,
    failedCount: number
  ) => void;
  /** Update an item's status within a job */
  updateItemStatus: (
    jobId: string,
    itemId: string,
    status: BatchItem["status"],
    error?: string,
    result?: Record<string, unknown>
  ) => void;
  /** Cancel a job */
  cancelJob: (jobId: string) => void;
  /** Pause a job */
  pauseJob: (jobId: string) => void;
  /** Resume a paused job */
  resumeJob: (jobId: string) => void;
  /** Retry a failed job */
  retryJob: (jobId: string) => void;
  /** Remove a job from history */
  removeJob: (jobId: string) => void;
  /** Clear all completed jobs */
  clearCompleted: () => void;
  /** Set filters */
  setFilters: (filters: BatchJobFilters) => void;
  /** Select a job for detail view */
  selectJob: (jobId: string | null) => void;
  /** Toggle panel open/closed */
  togglePanel: () => void;
  /** Set panel open state */
  setPanelOpen: (open: boolean) => void;
  /** Get filtered jobs */
  getFilteredJobs: () => BatchJob[];
  /** Get job statistics */
  getStats: () => BatchJobStats;
  /** Get a specific job */
  getJob: (jobId: string) => BatchJob | undefined;
}

/**
 * Generate a unique job ID
 */
function generateJobId(): string {
  return `batch_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Generate a unique item ID
 */
function generateItemId(): string {
  return `item_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Filter jobs based on filters
 */
function filterJobs(jobs: BatchJob[], filters: BatchJobFilters): BatchJob[] {
  return jobs.filter((job) => {
    if (
      filters.status &&
      filters.status.length > 0 &&
      !filters.status.includes(job.status)
    ) {
      return false;
    }

    if (
      filters.operationType &&
      filters.operationType.length > 0 &&
      !filters.operationType.includes(job.operationType)
    ) {
      return false;
    }

    if (filters.dateRange) {
      const submitted = new Date(job.submittedAt).getTime();
      const start = new Date(filters.dateRange.start).getTime();
      const end = new Date(filters.dateRange.end).getTime();
      if (submitted < start || submitted > end) {
        return false;
      }
    }

    if (filters.submittedBy && job.submittedBy !== filters.submittedBy) {
      return false;
    }

    return true;
  });
}

/**
 * Calculate job statistics
 */
function calculateStats(jobs: BatchJob[]): BatchJobStats {
  const byStatus: Record<BatchJobStatus, number> = {
    pending: 0,
    running: 0,
    paused: 0,
    completed: 0,
    failed: 0,
    cancelled: 0,
    partial: 0,
  };

  const byType: Record<string, number> = {
    reimage: 0,
    recalibrate: 0,
    export: 0,
    archive: 0,
    delete: 0,
    qa_rating: 0,
    crossmatch: 0,
  };

  let totalCompletionTime = 0;
  let completedJobCount = 0;

  for (const job of jobs) {
    byStatus[job.status]++;
    byType[job.operationType]++;

    if (job.status === "completed" && job.startedAt && job.completedAt) {
      const start = new Date(job.startedAt).getTime();
      const end = new Date(job.completedAt).getTime();
      totalCompletionTime += end - start;
      completedJobCount++;
    }
  }

  return {
    total: jobs.length,
    byStatus,
    byType: byType as Record<string, number>,
    running: byStatus.running,
    queued: byStatus.pending,
    avgCompletionTime:
      completedJobCount > 0 ? totalCompletionTime / completedJobCount : 0,
  };
}

/**
 * Batch operations store
 */
export const useBatchStore = create<BatchState & BatchActions>()(
  persist(
    (set, get) => ({
      // Initial state
      jobs: [],
      filters: {},
      selectedJobId: null,
      isPanelOpen: false,

      // Actions
      createJob: (request) => {
        const job: BatchJob = {
          id: generateJobId(),
          operationType: request.operationType,
          name: request.name,
          status: "pending",
          priority: request.priority ?? "normal",
          parameters: request.parameters,
          items: request.resourceIds.map((resourceId) => ({
            id: generateItemId(),
            resourceType: request.resourceType,
            resourceId,
            name: resourceId, // Could be enhanced to fetch actual names
            status: "pending",
          })),
          submittedBy: "current-user", // Would come from auth
          submittedAt: new Date().toISOString(),
          progress: 0,
          completedCount: 0,
          failedCount: 0,
        };

        set((state) => ({
          jobs: [job, ...state.jobs].slice(0, MAX_JOB_HISTORY),
        }));

        return job;
      },

      updateJobStatus: (jobId, status, error) => {
        set((state) => ({
          jobs: state.jobs.map((job) => {
            if (job.id !== jobId) return job;

            const updates: Partial<BatchJob> = { status };

            if (status === "running" && !job.startedAt) {
              updates.startedAt = new Date().toISOString();
            }

            if (
              status === "completed" ||
              status === "failed" ||
              status === "cancelled" ||
              status === "partial"
            ) {
              updates.completedAt = new Date().toISOString();
            }

            if (error) {
              updates.error = error;
            }

            return { ...job, ...updates };
          }),
        }));
      },

      updateJobProgress: (jobId, progress, completedCount, failedCount) => {
        set((state) => ({
          jobs: state.jobs.map((job) =>
            job.id === jobId
              ? { ...job, progress, completedCount, failedCount }
              : job
          ),
        }));
      },

      updateItemStatus: (jobId, itemId, status, error, result) => {
        set((state) => ({
          jobs: state.jobs.map((job) => {
            if (job.id !== jobId) return job;

            const now = new Date().toISOString();
            const items = job.items.map((item) => {
              if (item.id !== itemId) return item;

              const updates: Partial<BatchItem> = { status };

              if (status === "processing" && !item.startedAt) {
                updates.startedAt = now;
              }

              if (status === "completed" || status === "failed") {
                updates.completedAt = now;
              }

              if (error) {
                updates.error = error;
              }

              if (result) {
                updates.result = result;
              }

              return { ...item, ...updates };
            });

            return { ...job, items };
          }),
        }));
      },

      cancelJob: (jobId) => {
        get().updateJobStatus(jobId, "cancelled");
      },

      pauseJob: (jobId) => {
        get().updateJobStatus(jobId, "paused");
      },

      resumeJob: (jobId) => {
        get().updateJobStatus(jobId, "running");
      },

      retryJob: (jobId) => {
        set((state) => ({
          jobs: state.jobs.map((job) => {
            if (job.id !== jobId) return job;

            // Reset failed items to pending
            const items = job.items.map((item) =>
              item.status === "failed"
                ? { ...item, status: "pending" as const, error: undefined }
                : item
            );

            return {
              ...job,
              status: "pending" as const,
              items,
              error: undefined,
              completedAt: undefined,
            };
          }),
        }));
      },

      removeJob: (jobId) => {
        set((state) => ({
          jobs: state.jobs.filter((job) => job.id !== jobId),
          selectedJobId:
            state.selectedJobId === jobId ? null : state.selectedJobId,
        }));
      },

      clearCompleted: () => {
        set((state) => ({
          jobs: state.jobs.filter(
            (job) =>
              job.status !== "completed" &&
              job.status !== "cancelled" &&
              job.status !== "partial"
          ),
        }));
      },

      setFilters: (filters) => {
        set({ filters });
      },

      selectJob: (jobId) => {
        set({ selectedJobId: jobId });
      },

      togglePanel: () => {
        set((state) => ({ isPanelOpen: !state.isPanelOpen }));
      },

      setPanelOpen: (open) => {
        set({ isPanelOpen: open });
      },

      getFilteredJobs: () => {
        const { jobs, filters } = get();
        return filterJobs(jobs, filters);
      },

      getStats: () => {
        const { jobs } = get();
        return calculateStats(jobs);
      },

      getJob: (jobId) => {
        return get().jobs.find((job) => job.id === jobId);
      },
    }),
    {
      name: "dsa110-batch-jobs",
      partialize: (state) => ({
        // Only persist recent jobs
        jobs: state.jobs.slice(0, 20),
      }),
    }
  )
);

/**
 * Helper hook to get running job count
 */
export function useRunningJobCount(): number {
  return useBatchStore(
    (state) => state.jobs.filter((j) => j.status === "running").length
  );
}

/**
 * Helper hook to get pending job count
 */
export function usePendingJobCount(): number {
  return useBatchStore(
    (state) => state.jobs.filter((j) => j.status === "pending").length
  );
}
