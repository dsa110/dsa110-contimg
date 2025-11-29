import React from "react";
import { Link } from "react-router-dom";
import { useSources } from "../hooks/useQueries";

/**
 * List page showing all detected sources.
 */
const SourcesListPage: React.FC = () => {
  const { data: sources, isLoading, error } = useSources();

  if (isLoading) {
    return <div style={{ padding: "20px" }}>Loading sources...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: "20px", color: "#dc3545" }}>
        Failed to load sources: {error.message}
      </div>
    );
  }

  return (
    <div className="sources-list-page">
      <h1 style={{ marginTop: 0 }}>Sources</h1>

      {sources && sources.length > 0 ? (
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
                ID
              </th>
              <th style={{ padding: "12px", textAlign: "left", borderBottom: "2px solid #dee2e6" }}>
                Name
              </th>
              <th
                style={{ padding: "12px", textAlign: "right", borderBottom: "2px solid #dee2e6" }}
              >
                RA (deg)
              </th>
              <th
                style={{ padding: "12px", textAlign: "right", borderBottom: "2px solid #dee2e6" }}
              >
                Dec (deg)
              </th>
              <th
                style={{ padding: "12px", textAlign: "center", borderBottom: "2px solid #dee2e6" }}
              >
                Images
              </th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.id} style={{ borderBottom: "1px solid #dee2e6" }}>
                <td style={{ padding: "12px" }}>
                  <Link to={`/sources/${source.id}`} style={{ color: "#0066cc" }}>
                    {source.id}
                  </Link>
                </td>
                <td style={{ padding: "12px" }}>{source.name || "—"}</td>
                <td style={{ padding: "12px", textAlign: "right" }}>{source.ra_deg?.toFixed(4)}</td>
                <td style={{ padding: "12px", textAlign: "right" }}>
                  {source.dec_deg?.toFixed(4)}
                </td>
                <td style={{ padding: "12px", textAlign: "center" }}>
                  {source.contributing_images?.length ?? 0}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p style={{ color: "#666" }}>No sources found.</p>
      )}
    </div>
  );
};

export default SourcesListPage;
