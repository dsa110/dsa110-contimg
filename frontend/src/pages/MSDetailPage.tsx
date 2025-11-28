import React, { useEffect, useState } from "react";
import ProvenanceStrip from "../components/provenance/ProvenanceStrip";
import ErrorDisplay from "../components/errors/ErrorDisplay";
import { mapProvenanceFromMSDetail, MSDetailResponse } from "../utils/provenanceMappers";
import type { ErrorResponse } from "../types/errors";
import apiClient from "../api/client";

interface MSDetailPageProps {
  msPath: string;
}

/**
 * Detail page for a Measurement Set.
 * Displays MS metadata, calibrator matches, provenance, and related images.
 */
const MSDetailPage: React.FC<MSDetailPageProps> = ({ msPath }) => {
  const [ms, setMS] = useState<MSDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ErrorResponse | null>(null);

  useEffect(() => {
    const fetchMS = async () => {
      setLoading(true);
      setError(null);
      try {
        const encodedPath = encodeURIComponent(msPath);
        const response = await apiClient.get<MSDetailResponse>(`/ms/${encodedPath}/metadata`);
        setMS(response.data);
      } catch (err) {
        setError(err as ErrorResponse);
      } finally {
        setLoading(false);
      }
    };

    fetchMS();
  }, [msPath]);

  if (loading) {
    return (
      <div className="page-loading" style={{ padding: "20px", textAlign: "center" }}>
        Loading Measurement Set details...
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-error" style={{ padding: "20px" }}>
        <ErrorDisplay error={error} />
      </div>
    );
  }

  if (!ms) {
    return (
      <div className="page-empty" style={{ padding: "20px" }}>
        Measurement Set not found.
      </div>
    );
  }

  const provenance = mapProvenanceFromMSDetail(ms);

  return (
    <div className="ms-detail-page" style={{ padding: "20px" }}>
      <header style={{ marginBottom: "20px" }}>
        <h1 style={{ margin: "0 0 12px" }}>MS: {ms.path.split("/").pop()}</h1>
        <ProvenanceStrip {...provenance} />
      </header>

      <section className="ms-metadata" style={{ marginBottom: "20px" }}>
        <h2>Metadata</h2>
        <table style={{ borderCollapse: "collapse", width: "100%", maxWidth: "600px" }}>
          <tbody>
            <tr>
              <td style={{ padding: "8px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                Path
              </td>
              <td
                style={{ padding: "8px", borderBottom: "1px solid #eee", wordBreak: "break-all" }}
              >
                {ms.path}
              </td>
            </tr>
            {ms.pointing_ra_deg !== undefined && ms.pointing_ra_deg !== null && (
              <tr>
                <td style={{ padding: "8px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                  Pointing RA
                </td>
                <td style={{ padding: "8px", borderBottom: "1px solid #eee" }}>
                  {ms.pointing_ra_deg.toFixed(4)}°
                </td>
              </tr>
            )}
            {ms.pointing_dec_deg !== undefined && ms.pointing_dec_deg !== null && (
              <tr>
                <td style={{ padding: "8px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                  Pointing Dec
                </td>
                <td style={{ padding: "8px", borderBottom: "1px solid #eee" }}>
                  {ms.pointing_dec_deg.toFixed(4)}°
                </td>
              </tr>
            )}
            {ms.created_at && (
              <tr>
                <td style={{ padding: "8px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                  Created
                </td>
                <td style={{ padding: "8px", borderBottom: "1px solid #eee" }}>
                  {new Date(ms.created_at).toLocaleString()}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      {ms.calibrator_matches && ms.calibrator_matches.length > 0 && (
        <section className="ms-calibrators" style={{ marginBottom: "20px" }}>
          <h2>Calibrator Matches</h2>
          <table style={{ borderCollapse: "collapse", width: "100%", maxWidth: "600px" }}>
            <thead>
              <tr>
                <th style={{ padding: "8px", borderBottom: "2px solid #ccc", textAlign: "left" }}>
                  Type
                </th>
                <th style={{ padding: "8px", borderBottom: "2px solid #ccc", textAlign: "left" }}>
                  Calibration Table
                </th>
              </tr>
            </thead>
            <tbody>
              {ms.calibrator_matches.map((cal, index) => (
                <tr key={index}>
                  <td style={{ padding: "8px", borderBottom: "1px solid #eee" }}>{cal.type}</td>
                  <td
                    style={{
                      padding: "8px",
                      borderBottom: "1px solid #eee",
                      wordBreak: "break-all",
                    }}
                  >
                    {cal.cal_table}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="ms-actions" style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
        <button
          type="button"
          style={{
            padding: "10px 16px",
            backgroundColor: "#0066cc",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
          }}
          onClick={() => window.open(`/api/ms/${encodeURIComponent(msPath)}/download`, "_blank")}
        >
          Download MS
        </button>
        <button
          type="button"
          style={{
            padding: "10px 16px",
            backgroundColor: "#28a745",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
          }}
          onClick={() => window.open(`/viewer/carta?ms=${encodeURIComponent(msPath)}`, "_blank")}
        >
          Open in CARTA
        </button>
        {ms.qa_grade && (
          <a
            href={`/qa/ms/${encodeURIComponent(msPath)}`}
            style={{
              padding: "10px 16px",
              backgroundColor: "#6c757d",
              color: "white",
              textDecoration: "none",
              borderRadius: "4px",
            }}
          >
            View QA Report
          </a>
        )}
      </section>
    </div>
  );
};

export default MSDetailPage;
