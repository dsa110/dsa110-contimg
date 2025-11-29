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
    return <div style={{ padding: "20px" }}>Loading jobs...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: "20px", color: "#dc3545" }}>Failed to load jobs: {error.message}</div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return { bg: "#d4edda", text: "#155724" };
      case "running":
        return { bg: "#cce5ff", text: "#004085" };
      case "failed":
        return { bg: "#f8d7da", text: "#721c24" };
      case "pending":
        return { bg: "#fff3cd", text: "#856404" };
      default:
        return { bg: "#e9ecef", text: "#495057" };
    }
  };

  return (
    <div className="jobs-list-page">
      <h1 style={{ marginTop: 0 }}>Pipeline Jobs</h1>

      {jobs && jobs.length > 0 ? (
        <table
          style={{
            width: "100%",
            backgroundColor: "white",
            borderCollapse: "collapse",
            boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
          }}
        >
          <thead>
            <tr style={{ backgroundColor: "#f8f9fa" }}>
              <th style={{ padding: "12px", textAlign: "left", borderBottom: "2px solid #dee2e6" }}>
                Run ID
              </th>
              <th style={{ padding: "12px", textAlign: "left", borderBottom: "2px solid #dee2e6" }}>
                Type
              </th>
              <th
                style={{ padding: "12px", textAlign: "center", borderBottom: "2px solid #dee2e6" }}
              >
                Status
              </th>
              <th style={{ padding: "12px", textAlign: "left", borderBottom: "2px solid #dee2e6" }}>
                Input MS
              </th>
              <th
                style={{ padding: "12px", textAlign: "right", borderBottom: "2px solid #dee2e6" }}
              >
                Started
              </th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => {
              const statusStyle = getStatusColor(job.status);
              return (
                <tr key={job.id} style={{ borderBottom: "1px solid #dee2e6" }}>
                  <td style={{ padding: "12px" }}>
                    <Link to={`/jobs/${job.id}`} style={{ color: "#0066cc" }}>
                      {job.id}
                    </Link>
                  </td>
                  <td style={{ padding: "12px" }}>{job.job_type || "imaging"}</td>
                  <td style={{ padding: "12px", textAlign: "center" }}>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "4px 12px",
                        borderRadius: "4px",
                        backgroundColor: statusStyle.bg,
                        color: statusStyle.text,
                        fontSize: "0.85rem",
                      }}
                    >
                      {job.status}
                    </span>
                  </td>
                  <td style={{ padding: "12px", fontSize: "0.9rem", color: "#666" }}>
                    {job.ms_path?.split("/").pop() || "—"}
                  </td>
                  <td style={{ padding: "12px", textAlign: "right", color: "#666" }}>
                    {job.created_at ? relativeTime(job.created_at) : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <p style={{ color: "#666" }}>No jobs found.</p>
      )}
    </div>
  );
};

export default JobsListPage;
