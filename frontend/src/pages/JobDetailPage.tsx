import React from "react";
import { useParams, Link } from "react-router-dom";
import { useJobProvenance } from "../hooks/useQueries";
import ProvenanceStrip from "../components/provenance/ProvenanceStrip";
import ErrorDisplay from "../components/errors/ErrorDisplay";
import { relativeTime } from "../utils/relativeTime";

/**
 * Job detail page showing provenance and job information.
 */
const JobDetailPage: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const { data: provenance, isLoading, error } = useJobProvenance(runId);

  if (isLoading) {
    return <div style={{ padding: "20px" }}>Loading job details...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: "20px" }}>
        <ErrorDisplay error={error} />
      </div>
    );
  }

  if (!provenance) {
    return <div style={{ padding: "20px" }}>Job not found.</div>;
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
        <ProvenanceStrip
          runId={provenance.run_id}
          msPath={provenance.ms_path}
          calTable={provenance.cal_table}
          pointingRaDeg={provenance.pointing_ra_deg}
          pointingDecDeg={provenance.pointing_dec_deg}
          qaGrade={provenance.qa_grade}
          qaSummary={provenance.qa_summary}
          logsUrl={provenance.logs_url}
          qaUrl={provenance.qa_url}
          msUrl={provenance.ms_url}
          imageUrl={provenance.image_url}
          createdAt={provenance.created_at}
        />
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
                {provenance.run_id}
              </td>
            </tr>
            {provenance.ms_path && (
              <tr>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                  Input MS
                </td>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  <Link to={`/ms/${encodeURIComponent(provenance.ms_path)}`}>
                    {provenance.ms_path}
                  </Link>
                </td>
              </tr>
            )}
            {provenance.cal_table && (
              <tr>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                  Cal Table
                </td>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  {provenance.cal_table}
                </td>
              </tr>
            )}
            {provenance.qa_grade && (
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
                        provenance.qa_grade === "good"
                          ? "#d4edda"
                          : provenance.qa_grade === "warn"
                            ? "#fff3cd"
                            : "#f8d7da",
                    }}
                  >
                    {provenance.qa_grade}
                  </span>
                  {provenance.qa_summary && (
                    <span style={{ marginLeft: "8px", color: "#666" }}>
                      {provenance.qa_summary}
                    </span>
                  )}
                </td>
              </tr>
            )}
            {provenance.created_at && (
              <tr>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                  Started
                </td>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  {new Date(provenance.created_at).toLocaleString()} (
                  {relativeTime(provenance.created_at)})
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <section className="job-actions" style={{ display: "flex", gap: "12px" }}>
        {provenance.logs_url && (
          <a
            href={provenance.logs_url}
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
        {provenance.image_url && (
          <Link
            to={provenance.image_url}
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
