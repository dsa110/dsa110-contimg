import React from "react";
import { useParams, Link } from "react-router-dom";
import { useJobProvenance } from "../hooks/useQueries";
import ProvenanceStrip from "../components/provenance/ProvenanceStrip";
import ErrorDisplay from "../components/errors/ErrorDisplay";
import type { ErrorResponse } from "../types/errors";
import { relativeTime } from "../utils/relativeTime";
import { usePreferencesStore } from "../stores/appStore";

/**
 * Job detail page showing provenance and job information.
 */
const JobDetailPage: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const { data: provenance, isLoading, error, refetch } = useJobProvenance(runId);
  const addRecentJob = usePreferencesStore((state) => state.addRecentJob);

  // Track in recent items when job loads
  React.useEffect(() => {
    if (provenance && runId) {
      addRecentJob(runId);
    }
  }, [provenance, runId, addRecentJob]);

  if (isLoading) {
    return <div style={{ padding: "20px" }}>Loading job details...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: "20px" }}>
        <ErrorDisplay error={error as unknown as ErrorResponse} onRetry={() => refetch()} />
      </div>
    );
  }

  if (!provenance) {
    return (
      <div style={{ padding: "20px" }}>
        <p>Job not found.</p>
        <Link to="/jobs">← Back to Jobs</Link>
      </div>
    );
  }

  return (
    <div className="job-detail-page">
      <nav style={{ marginBottom: "16px" }}>
        <Link to="/jobs" style={{ color: "#0066cc" }}>
          ← Back to Jobs
        </Link>
      </nav>

      <header style={{ marginBottom: "24px" }}>
        <h1 style={{ margin: "0 0 12px" }}>Job: {runId}</h1>
        <ProvenanceStrip {...provenance} />
      </header>

      <section className="job-details" style={{ marginBottom: "24px" }}>
        <h2>Details</h2>
        <table
          style={{
            backgroundColor: "white",
            borderCollapse: "collapse",
            width: "100%",
            maxWidth: "600px",
            boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
          }}
        >
          <tbody>
            <tr>
              <td
                style={{
                  padding: "12px",
                  borderBottom: "1px solid #eee",
                  fontWeight: "bold",
                  width: "150px",
                }}
              >
                Run ID
              </td>
              <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                {provenance.runId || runId}
              </td>
            </tr>
            {provenance.msPath && (
              <tr>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                  Input MS
                </td>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  <Link to={`/ms/${encodeURIComponent(provenance.msPath)}`}>
                    {provenance.msPath}
                  </Link>
                </td>
              </tr>
            )}
            {provenance.calTable && (
              <tr>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                  Cal Table
                </td>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  {provenance.calUrl ? (
                    <a href={provenance.calUrl}>{provenance.calTable}</a>
                  ) : (
                    provenance.calTable
                  )}
                </td>
              </tr>
            )}
            {provenance.qaGrade && (
              <tr>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                  QA Grade
                </td>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  <span
                    style={{
                      padding: "4px 8px",
                      borderRadius: "4px",
                      backgroundColor:
                        provenance.qaGrade === "good"
                          ? "#d4edda"
                          : provenance.qaGrade === "warn"
                          ? "#fff3cd"
                          : "#f8d7da",
                    }}
                  >
                    {provenance.qaGrade}
                  </span>
                  {provenance.qaSummary && (
                    <span style={{ marginLeft: "8px", color: "#666" }}>{provenance.qaSummary}</span>
                  )}
                </td>
              </tr>
            )}
            {provenance.createdAt && (
              <tr>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                  Started
                </td>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  {new Date(provenance.createdAt).toLocaleString()} (
                  {relativeTime(provenance.createdAt)})
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <section className="job-actions" style={{ display: "flex", gap: "12px" }}>
        {provenance.logsUrl && (
          <a
            href={provenance.logsUrl}
            target="_blank"
            rel="noreferrer"
            style={{
              padding: "10px 16px",
              backgroundColor: "#6c757d",
              color: "white",
              textDecoration: "none",
              borderRadius: "4px",
            }}
          >
            View Logs
          </a>
        )}
        {provenance.imageUrl && (
          <Link
            to={provenance.imageUrl}
            style={{
              padding: "10px 16px",
              backgroundColor: "#0066cc",
              color: "white",
              textDecoration: "none",
              borderRadius: "4px",
            }}
          >
            View Output Image
          </Link>
        )}
      </section>
    </div>
  );
};

export default JobDetailPage;
