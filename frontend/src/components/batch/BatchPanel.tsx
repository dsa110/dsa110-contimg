/**
 * BatchPanel - Slide-out panel for batch operations
 */
import { useEffect, useRef } from "react";
import { useBatchStore, useRunningJobCount } from "@/stores/batchStore";
import { BatchJobList } from "./BatchJobList";
import { BatchJobDetail } from "./BatchJobDetail";

export function BatchPanel() {
  const {
    isPanelOpen,
    setPanelOpen,
    selectedJobId,
    selectJob,
    clearCompleted,
    getStats,
  } = useBatchStore();

  const panelRef = useRef<HTMLDivElement>(null);
  const stats = getStats();

  // Close on escape key
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (selectedJobId) {
          selectJob(null);
        } else {
          setPanelOpen(false);
        }
      }
    };

    if (isPanelOpen) {
      document.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isPanelOpen, selectedJobId, selectJob, setPanelOpen]);

  if (!isPanelOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 dark:bg-black/40 z-40"
        onClick={() => setPanelOpen(false)}
      />

      {/* Panel */}
      <div
        ref={panelRef}
        className="fixed right-0 top-0 h-full w-full max-w-lg bg-white dark:bg-gray-900 shadow-xl z-50 flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            {selectedJobId && (
              <button
                type="button"
                onClick={() => selectJob(null)}
                className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                aria-label="Back to list"
              >
                <svg
                  className="w-5 h-5 text-gray-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 19l-7-7 7-7"
                  />
                </svg>
              </button>
            )}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {selectedJobId ? "Job Details" : "Batch Operations"}
              </h2>
              {!selectedJobId && (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {stats.running} running, {stats.queued} queued
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {!selectedJobId && stats.total > stats.running + stats.queued && (
              <button
                type="button"
                onClick={clearCompleted}
                className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400"
              >
                Clear completed
              </button>
            )}
            <button
              type="button"
              onClick={() => setPanelOpen(false)}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
              aria-label="Close panel"
            >
              <svg
                className="w-5 h-5 text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {selectedJobId ? <BatchJobDetail jobId={selectedJobId} /> : <BatchJobList />}
        </div>
      </div>
    </>
  );
}

/**
 * BatchButton - Header button to open batch panel
 */
export function BatchButton({ className = "" }: { className?: string }) {
  const togglePanel = useBatchStore((state) => state.togglePanel);
  const runningCount = useRunningJobCount();

  return (
    <button
      type="button"
      onClick={togglePanel}
      className={`relative p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${className}`}
      aria-label={`Batch operations${runningCount > 0 ? ` (${runningCount} running)` : ""}`}
    >
      {/* Batch icon */}
      <svg
        className="w-6 h-6 text-gray-600 dark:text-gray-300"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
        />
      </svg>

      {/* Running indicator */}
      {runningCount > 0 && (
        <span className="absolute -top-1 -right-1 min-w-[20px] h-5 px-1 flex items-center justify-center text-xs font-bold text-white bg-primary-600 rounded-full">
          {runningCount}
        </span>
      )}
    </button>
  );
}
