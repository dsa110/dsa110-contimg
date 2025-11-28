import React, { useEffect, useState } from "react";
import ProvenanceStrip from "../components/provenance/ProvenanceStrip";
import ErrorDisplay from "../components/errors/ErrorDisplay";
import { mapProvenanceFromSourceDetail, SourceDetailResponse } from "../utils/provenanceMappers";
import type { ErrorResponse } from "../types/errors";
import type { ProvenanceStripProps } from "../types/provenance";
import apiClient from "../api/client";

interface SourceDetailPageProps {
  sourceId: string;
}

/**
 * Detail page for an astronomical source.
 * Displays source info, lightcurve, contributing images, and provenance.
 */
const SourceDetailPage: React.FC<SourceDetailPageProps> = ({ sourceId }) => {
  const [source, setSource] = useState<SourceDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ErrorResponse | null>(null);
  const [selectedImageId, setSelectedImageId] = useState<string | undefined>(undefined);

  useEffect(() => {
    const fetchSource = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiClient.get<SourceDetailResponse>(`/sources/${sourceId}`);
        setSource(response.data);
        // Default to first contributing image
        if (response.data.contributing_images?.length) {
          setSelectedImageId(response.data.contributing_images[0].image_id);
        }
      } catch (err) {
        setError(err as ErrorResponse);
      } finally {
        setLoading(false);
      }
    };

    fetchSource();
  }, [sourceId]);

  if (loading) {
    return (
      <div className="page-loading" style={{ padding: "20px", textAlign: "center" }}>
        Loading source details...
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

  if (!source) {
    return (
      <div className="page-empty" style={{ padding: "20px" }}>
        Source not found.
      </div>
    );
  }

  const provenance: ProvenanceStripProps | null = mapProvenanceFromSourceDetail(
    source,
    selectedImageId
  );

  return (
    <div className="source-detail-page" style={{ padding: "20px" }}>
      <header style={{ marginBottom: "20px" }}>
        <h1 style={{ margin: "0 0 12px" }}>Source: {source.name || source.id}</h1>
        {provenance && <ProvenanceStrip {...provenance} />}
      </header>

      <section className="source-coordinates" style={{ marginBottom: "20px" }}>
        <h2>Coordinates</h2>
        <table style={{ borderCollapse: "collapse", width: "100%", maxWidth: "400px" }}>
          <tbody>
            <tr>
              <td style={{ padding: "8px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                RA
              </td>
              <td style={{ padding: "8px", borderBottom: "1px solid #eee" }}>
                {source.ra_deg.toFixed(6)}°
              </td>
            </tr>
            <tr>
              <td style={{ padding: "8px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                Dec
              </td>
              <td style={{ padding: "8px", borderBottom: "1px solid #eee" }}>
                {source.dec_deg.toFixed(6)}°
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      {source.contributing_images && source.contributing_images.length > 0 && (
        <section className="source-images" style={{ marginBottom: "20px" }}>
          <h2>Contributing Images ({source.contributing_images.length})</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxWidth: "600px" }}>
            {source.contributing_images.map((img) => (
              <div
                key={img.image_id}
                style={{
                  padding: "12px",
                  border: selectedImageId === img.image_id ? "2px solid #0066cc" : "1px solid #ddd",
                  borderRadius: "4px",
                  cursor: "pointer",
                  backgroundColor: selectedImageId === img.image_id ? "#f0f7ff" : "white",
                }}
                onClick={() => setSelectedImageId(img.image_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    setSelectedImageId(img.image_id);
                  }
                }}
                role="button"
                tabIndex={0}
              >
                <div style={{ fontWeight: "bold" }}>
                  <a href={`/images/${img.image_id}`}>{img.path.split("/").pop()}</a>
                </div>
                {img.ms_path && (
                  <div style={{ fontSize: "0.9em", color: "#666" }}>
                    MS: {img.ms_path.split("/").pop()}
                  </div>
                )}
                <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
                  {img.qa_grade && (
                    <span
                      style={{
                        padding: "2px 6px",
                        borderRadius: "3px",
                        fontSize: "0.8em",
                        backgroundColor:
                          img.qa_grade === "good"
                            ? "#d4edda"
                            : img.qa_grade === "warn"
                              ? "#fff3cd"
                              : "#f8d7da",
                        color:
                          img.qa_grade === "good"
                            ? "#155724"
                            : img.qa_grade === "warn"
                              ? "#856404"
                              : "#721c24",
                      }}
                    >
                      {img.qa_grade.toUpperCase()}
                    </span>
                  )}
                  {img.created_at && (
                    <span style={{ fontSize: "0.8em", color: "#999" }}>
                      {new Date(img.created_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section
        className="source-actions"
        style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}
      >
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
          onClick={() => window.open(`/api/sources/${sourceId}/lightcurve`, "_blank")}
        >
          View Lightcurve
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
          onClick={() => window.open(`/api/sources/${sourceId}/postage_stamps`, "_blank")}
        >
          Download Postage Stamps
        </button>
        <button
          type="button"
          style={{
            padding: "10px 16px",
            backgroundColor: "#6c757d",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
          }}
          onClick={() => window.open(`/api/sources/${sourceId}/variability`, "_blank")}
        >
          Variability Analysis
        </button>
      </section>
    </div>
  );
};

export default SourceDetailPage;
