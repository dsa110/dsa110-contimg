/**
 * useBatchOperations hook
 * Provides batch operation actions and helpers
 */
import { useCallback } from "react";
import { useBatchStore } from "@/stores/batchStore";
import { useNotifications } from "@/hooks/useNotifications";
import type {
  BatchOperationType,
  CreateBatchJobRequest,
  ReimageParams,
  RecalibrateParams,
  ExportParams,
  QARatingParams,
} from "@/types/batch";

/**
 * Main batch operations hook
 */
export function useBatchOperations() {
  const store = useBatchStore();
  const { notifyInfo, notifySuccess, notifyError } = useNotifications();

  /**
   * Create and submit a batch re-imaging job
   */
  const submitReimageJob = useCallback(
    (
      name: string,
      imageIds: string[],
      params: ReimageParams
    ) => {
      const job = store.createJob({
        operationType: "reimage",
        name,
        resourceIds: imageIds,
        resourceType: "image",
        parameters: { type: "reimage", params },
      });

      notifyInfo(
        "Batch job created",
        `Re-imaging job "${name}" with ${imageIds.length} images has been queued.`,
        { category: "pipeline", link: `/batch/${job.id}` }
      );

      return job;
    },
    [store, notifyInfo]
  );

  /**
   * Create and submit a batch re-calibration job
   */
  const submitRecalibrateJob = useCallback(
    (
      name: string,
      msIds: string[],
      params: RecalibrateParams
    ) => {
      const job = store.createJob({
        operationType: "recalibrate",
        name,
        resourceIds: msIds,
        resourceType: "ms",
        parameters: { type: "recalibrate", params },
      });

      notifyInfo(
        "Batch job created",
        `Re-calibration job "${name}" with ${msIds.length} measurement sets has been queued.`,
        { category: "calibration", link: `/batch/${job.id}` }
      );

      return job;
    },
    [store, notifyInfo]
  );

  /**
   * Create and submit a batch export job
   */
  const submitExportJob = useCallback(
    (
      name: string,
      resourceIds: string[],
      resourceType: "image" | "source",
      params: ExportParams
    ) => {
      const job = store.createJob({
        operationType: "export",
        name,
        resourceIds,
        resourceType,
        parameters: { type: "export", params },
      });

      notifyInfo(
        "Export job created",
        `Export job "${name}" with ${resourceIds.length} items has been queued.`,
        { category: "data", link: `/batch/${job.id}` }
      );

      return job;
    },
    [store, notifyInfo]
  );

  /**
   * Create and submit a batch QA rating job
   */
  const submitQARatingJob = useCallback(
    (
      name: string,
      resourceIds: string[],
      resourceType: "image" | "source",
      params: QARatingParams
    ) => {
      const job = store.createJob({
        operationType: "qa_rating",
        name,
        resourceIds,
        resourceType,
        parameters: { type: "qa_rating", params },
      });

      notifyInfo(
        "QA Rating job created",
        `Applying rating ${params.rating} to ${resourceIds.length} items.`,
        { category: "user", link: `/batch/${job.id}` }
      );

      return job;
    },
    [store, notifyInfo]
  );

  /**
   * Create and submit a batch crossmatch job
   */
  const submitCrossmatchJob = useCallback(
    (
      name: string,
      sourceIds: string[],
      catalogs: string[]
    ) => {
      const job = store.createJob({
        operationType: "crossmatch",
        name,
        resourceIds: sourceIds,
        resourceType: "source",
        parameters: { type: "crossmatch", params: { catalogs } },
      });

      notifyInfo(
        "Crossmatch job created",
        `Crossmatching ${sourceIds.length} sources against ${catalogs.join(", ")}.`,
        { category: "source", link: `/batch/${job.id}` }
      );

      return job;
    },
    [store, notifyInfo]
  );

  /**
   * Create and submit a batch delete job
   */
  const submitDeleteJob = useCallback(
    (
      name: string,
      resourceIds: string[],
      resourceType: "image" | "source" | "ms"
    ) => {
      const job = store.createJob({
        operationType: "delete",
        name,
        resourceIds,
        resourceType,
        parameters: { type: "delete", params: {} },
      });

      notifyInfo(
        "Delete job created",
        `Deleting ${resourceIds.length} ${resourceType}s.`,
        { category: "data", link: `/batch/${job.id}` }
      );

      return job;
    },
    [store, notifyInfo]
  );

  /**
   * Simulate job progress (for demo/development)
   * In production, this would be replaced by real API polling or WebSocket updates
   */
  const simulateJobProgress = useCallback(
    (jobId: string) => {
      const job = store.getJob(jobId);
      if (!job || job.status !== "pending") return;

      store.updateJobStatus(jobId, "running");

      let itemIndex = 0;
      const interval = setInterval(() => {
        const currentJob = store.getJob(jobId);
        if (!currentJob || currentJob.status === "cancelled" || currentJob.status === "paused") {
          clearInterval(interval);
          return;
        }

        if (itemIndex >= currentJob.items.length) {
          clearInterval(interval);

          const failedCount = currentJob.items.filter((i) => i.status === "failed").length;
          const finalStatus = failedCount > 0 ? "partial" : "completed";

          store.updateJobStatus(jobId, finalStatus);

          if (finalStatus === "completed") {
            notifySuccess(
              "Batch job completed",
              `Job "${currentJob.name}" completed successfully.`,
              { category: "pipeline" }
            );
          } else {
            notifyError(
              "Batch job completed with errors",
              `Job "${currentJob.name}" completed with ${failedCount} failures.`,
              { category: "pipeline" }
            );
          }
          return;
        }

        const item = currentJob.items[itemIndex];

        // Start processing
        store.updateItemStatus(jobId, item.id, "processing");

        // Simulate processing time
        setTimeout(() => {
          // 90% success rate for simulation
          const success = Math.random() > 0.1;
          store.updateItemStatus(
            jobId,
            item.id,
            success ? "completed" : "failed",
            success ? undefined : "Simulated failure"
          );

          const completedCount = currentJob.items.filter(
            (i) => i.status === "completed"
          ).length + (success ? 1 : 0);
          const failedCount = currentJob.items.filter(
            (i) => i.status === "failed"
          ).length + (success ? 0 : 1);
          const progress = Math.round(
            ((completedCount + failedCount) / currentJob.items.length) * 100
          );

          store.updateJobProgress(jobId, progress, completedCount, failedCount);
        }, 500);

        itemIndex++;
      }, 1000);

      return () => clearInterval(interval);
    },
    [store, notifySuccess, notifyError]
  );

  return {
    // State
    jobs: store.getFilteredJobs(),
    stats: store.getStats(),
    selectedJobId: store.selectedJobId,
    isPanelOpen: store.isPanelOpen,

    // Job submission
    submitReimageJob,
    submitRecalibrateJob,
    submitExportJob,
    submitQARatingJob,
    submitCrossmatchJob,
    submitDeleteJob,

    // Job management
    cancelJob: store.cancelJob,
    pauseJob: store.pauseJob,
    resumeJob: store.resumeJob,
    retryJob: store.retryJob,
    removeJob: store.removeJob,
    clearCompleted: store.clearCompleted,

    // UI
    selectJob: store.selectJob,
    togglePanel: store.togglePanel,
    setPanelOpen: store.setPanelOpen,
    setFilters: store.setFilters,

    // Development helper
    simulateJobProgress,
  };
}

/**
 * Hook to check if any items are selected for batch operations
 */
export function useSelectedItems<T extends { id: string }>(items: T[]) {
  const selectedIds = new Set<string>();

  const toggleSelection = (id: string) => {
    if (selectedIds.has(id)) {
      selectedIds.delete(id);
    } else {
      selectedIds.add(id);
    }
  };

  const selectAll = () => {
    items.forEach((item) => selectedIds.add(item.id));
  };

  const clearSelection = () => {
    selectedIds.clear();
  };

  const getSelectedItems = () => {
    return items.filter((item) => selectedIds.has(item.id));
  };

  return {
    selectedIds: Array.from(selectedIds),
    selectedCount: selectedIds.size,
    isSelected: (id: string) => selectedIds.has(id),
    toggleSelection,
    selectAll,
    clearSelection,
    getSelectedItems,
  };
}
