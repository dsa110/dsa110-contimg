import React from "react";
import { Link } from "react-router-dom";
import { useJobs } from "../hooks/useQueries";
import { relativeTime } from "../utils/relativeTime";

/**
 * List page showing all pipeline jobs.
 */
const JobsListPage: React.FC = () => {
  const { data: jobs, isLoading, error } = useJobs();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-500">Loading jobs...</div>
      </div>
    );
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
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Pipeline Jobs</h1>

      {jobs && jobs.length > 0 ? (
        <div className="card overflow-hidden">
          <table className="table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th className="text-center">Status</th>
                <th className="text-right">Started</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {jobs.map((job) => (
                <tr key={job.run_id}>
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
