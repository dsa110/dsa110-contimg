import React, { useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import { useJobs } from "../hooks/useQueries";
import { relativeTime } from "../utils/relativeTime";
import { LoadingSpinner, SortableTableHeader, useTableSort } from "../components/common";
import { useSelectionStore } from "../stores/appStore";

interface JobItem {
  run_id: string;
  status: string;
  started_at?: string;
}

/**
 * List page showing all pipeline jobs with sortable columns.
 */
const JobsListPage: React.FC = () => {
  const { data: jobs, isLoading, error } = useJobs();

  // Multi-select state
  const selectedJobs = useSelectionStore((s) => s.selectedJobs);
  const toggleJobSelection = useSelectionStore((s) => s.toggleJobSelection);
  const selectAllJobs = useSelectionStore((s) => s.selectAllJobs);
  const clearJobSelection = useSelectionStore((s) => s.clearJobSelection);

  const selectedIds = useMemo(() => Array.from(selectedJobs), [selectedJobs]);

  const handleBulkAction = useCallback(
    async (action: "rerun" | "cancel" | "export") => {
      if (selectedIds.length === 0) return;
      const baseUrl = import.meta.env.VITE_API_URL || "/api";
      if (action === "export") {
        window.open(`${baseUrl}/jobs/export?ids=${selectedIds.join(",")}`, "_blank");
      } else {
        await fetch(`${baseUrl}/jobs/bulk-${action}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ runIds: selectedIds }),
        });
      }
    },
    [selectedIds]
  );

  // Apply sorting using the hook
  const {
    sortColumn,
    sortDirection,
    handleSort,
    sortedData: sortedJobs,
  } = useTableSort<JobItem>(jobs as JobItem[] | undefined, "started_at", "desc");

  if (isLoading) {
    return <LoadingSpinner label="Loading jobs..." />;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
        Failed to load jobs: {error.message}
      </div>
    );
  }

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "completed":
        return "badge-success";
      case "running":
        return "badge-info";
      case "failed":
        return "badge-error";
      case "pending":
        return "badge-warning";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-gray-900">Pipeline Jobs</h1>
          {selectedIds.length > 0 && (
            <span className="text-sm text-gray-500">{selectedIds.length} selected</span>
          )}
        </div>
        {selectedIds.length > 0 && (
          <div className="flex gap-2">
            <button
              onClick={() => handleBulkAction("rerun")}
              className="px-3 py-1.5 rounded text-sm font-medium bg-blue-600 text-white hover:bg-blue-700"
            >
              Rerun Selected
            </button>
            <button
              onClick={() => handleBulkAction("cancel")}
              className="px-3 py-1.5 rounded text-sm font-medium bg-orange-600 text-white hover:bg-orange-700"
            >
              Cancel Selected
            </button>
            <button
              onClick={() => handleBulkAction("export")}
              className="px-3 py-1.5 rounded text-sm font-medium bg-green-600 text-white hover:bg-green-700"
            >
              Export Logs
            </button>
          </div>
        )}
      </div>

      {sortedJobs && sortedJobs.length > 0 ? (
        <div className="card overflow-hidden">
          <table className="table">
            <thead>
              <tr>
                <th className="w-10 px-3 py-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.length === sortedJobs.length && sortedJobs.length > 0}
                    ref={(el) => {
                      if (el)
                        el.indeterminate =
                          selectedIds.length > 0 && selectedIds.length < sortedJobs.length;
                    }}
                    onChange={() => {
                      if (selectedIds.length === sortedJobs.length) {
                        clearJobSelection();
                      } else {
                        selectAllJobs(sortedJobs.map((j) => j.run_id));
                      }
                    }}
                    className="h-4 w-4 text-blue-600 rounded"
                  />
                </th>
                <SortableTableHeader
                  columnKey="run_id"
                  sortColumn={sortColumn}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                >
                  Run ID
                </SortableTableHeader>
                <SortableTableHeader
                  columnKey="status"
                  sortColumn={sortColumn}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  className="text-center"
                >
                  Status
                </SortableTableHeader>
                <SortableTableHeader
                  columnKey="started_at"
                  sortColumn={sortColumn}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  className="text-right"
                >
                  Started
                </SortableTableHeader>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sortedJobs.map((job) => (
                <tr key={job.run_id} className={selectedJobs.has(job.run_id) ? "bg-blue-50" : ""}>
                  <td className="px-3">
                    <input
                      type="checkbox"
                      checked={selectedJobs.has(job.run_id)}
                      onChange={() => toggleJobSelection(job.run_id)}
                      className="h-4 w-4 text-blue-600 rounded"
                    />
                  </td>
                  <td>
                    <Link
                      to={`/jobs/${job.run_id}`}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      {job.run_id}
                    </Link>
                  </td>
                  <td className="text-center">
                    <span className={`badge ${getStatusBadgeClass(job.status)}`}>{job.status}</span>
                  </td>
                  <td className="text-right text-gray-500">
                    {job.started_at ? relativeTime(job.started_at) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-gray-500">No jobs found.</p>
      )}
    </div>
  );
};

export default JobsListPage;
