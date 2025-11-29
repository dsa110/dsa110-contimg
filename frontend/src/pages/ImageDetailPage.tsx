import React from "react";
import { useParams, Link } from "react-router-dom";
import ProvenanceStrip from "../components/provenance/ProvenanceStrip";
import ErrorDisplay from "../components/errors/ErrorDisplay";
import { mapProvenanceFromImageDetail, ImageDetailResponse } from "../utils/provenanceMappers";
import type { ErrorResponse } from "../types/errors";
import { useImage } from "../hooks/useQueries";
import { usePreferencesStore } from "../stores/appStore";

/**
 * Detail page for a single image.
 * Displays image metadata, provenance strip, and visualization options.
 */
const ImageDetailPage: React.FC = () => {
  const { imageId } = useParams<{ imageId: string }>();
  const { data: image, isLoading, error, refetch } = useImage(imageId);
  const addRecentImage = usePreferencesStore((state) => state.addRecentImage);

  // Track in recent items when image loads
  React.useEffect(() => {
    if (image && imageId) {
      addRecentImage(imageId);
    }
  }, [image, imageId, addRecentImage]);

  if (isLoading) {
    return (
      <div className="page-loading" style={{ padding: "20px", textAlign: "center" }}>
        Loading image details...
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-error" style={{ padding: "20px" }}>
        <ErrorDisplay error={error as unknown as ErrorResponse} onRetry={() => refetch()} />
      </div>
    );
  }

  if (!image) {
    return (
      <div className="page-empty" style={{ padding: "20px" }}>
        <p>Image not found.</p>
        <Link to="/images">← Back to Images</Link>
      </div>
    );
  }

  // Cast to expected response type for mapper
  const provenance = mapProvenanceFromImageDetail(image as ImageDetailResponse);

  return (
    <div className="image-detail-page" style={{ padding: "20px" }}>
      <header style={{ marginBottom: "20px" }}>
        <h1 style={{ margin: "0 0 12px" }}>Image: {image.path.split("/").pop()}</h1>
        <ProvenanceStrip {...provenance} />
      </header>

      <section className="image-metadata" style={{ marginBottom: "20px" }}>
        <h2>Metadata</h2>
        <table style={{ borderCollapse: "collapse", width: "100%", maxWidth: "600px" }}>
          <tbody>
            <tr>
              <td style={{ padding: "8px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                ID
              </td>
              <td style={{ padding: "8px", borderBottom: "1px solid #eee" }}>{image.id}</td>
            </tr>
            <tr>
              <td style={{ padding: "8px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                Path
              </td>
              <td
                style={{ padding: "8px", borderBottom: "1px solid #eee", wordBreak: "break-all" }}
              >
                {image.path}
              </td>
            </tr>
            {image.ms_path && (
              <tr>
                <td style={{ padding: "8px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                  Measurement Set
                </td>
                <td
                  style={{ padding: "8px", borderBottom: "1px solid #eee", wordBreak: "break-all" }}
                >
                  <a href={`/ms/${encodeURIComponent(image.ms_path)}`}>{image.ms_path}</a>
                </td>
              </tr>
            )}
            {image.cal_table && (
              <tr>
                <td style={{ padding: "8px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                  Calibration Table
                </td>
                <td
                  style={{ padding: "8px", borderBottom: "1px solid #eee", wordBreak: "break-all" }}
                >
                  {image.cal_table}
                </td>
              </tr>
            )}
            {image.created_at && (
              <tr>
                <td style={{ padding: "8px", borderBottom: "1px solid #eee", fontWeight: "bold" }}>
                  Created
                </td>
                <td style={{ padding: "8px", borderBottom: "1px solid #eee" }}>
                  {new Date(image.created_at).toLocaleString()}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <section className="image-actions" style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
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
          onClick={() => window.open(`/api/images/${imageId}/fits`, "_blank")}
        >
          Download FITS
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
          onClick={() => window.open(`/viewer/js9?image=${imageId}`, "_blank")}
        >
          Open in JS9
        </button>
        {image.qa_grade && (
          <a
            href={`/qa/image/${imageId}`}
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

export default ImageDetailPage;
