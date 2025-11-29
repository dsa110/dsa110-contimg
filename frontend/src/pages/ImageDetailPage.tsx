import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import ProvenanceStrip from "../components/provenance/ProvenanceStrip";
import ErrorDisplay from "../components/errors/ErrorDisplay";
import {
  Card,
  CoordinateDisplay,
  ImageThumbnail,
  LoadingSpinner,
  Modal,
  QAMetrics,
} from "../components/common";
import { AladinLiteViewer } from "../components/widgets";
import { FitsViewer } from "../components/fits";
import { RatingCard, RatingTag } from "../components/rating";
import { mapProvenanceFromImageDetail, ImageDetailResponse } from "../utils/provenanceMappers";
import { relativeTime } from "../utils/relativeTime";
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
  const [showSkyViewer, setShowSkyViewer] = useState(true);
  const [showFitsViewer, setShowFitsViewer] = useState(false);
  const encodedImageId = imageId ? encodeURIComponent(imageId) : "";
  const [showRatingCard, setShowRatingCard] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const handleDeleteImage = async () => {
    const baseUrl = import.meta.env.VITE_API_URL || "/api";
    try {
      await fetch(`${baseUrl}/images/${encodedImageId}`, { method: "DELETE" });
      window.location.href = "/images";
    } catch (e) {
      console.error("Failed to delete image:", e);
    }
  };

  // Rating tags for QA assessment
  const ratingTags: RatingTag[] = [
    { id: "artifact", name: "Artifact", color: "#EF4444", description: "Image contains artifacts" },
    { id: "good", name: "Good Quality", color: "#22C55E", description: "Image passes QA" },
    { id: "marginal", name: "Marginal", color: "#F59E0B", description: "Borderline quality" },
    { id: "rfi", name: "RFI", color: "#8B5CF6", description: "Radio frequency interference" },
  ];

  const handleRatingSubmit = async (rating: {
    itemId: string;
    confidence: "true" | "false" | "unsure";
    tagId: string;
    notes: string;
  }) => {
    const baseUrl = import.meta.env.VITE_API_URL || "/api";
    await fetch(`${baseUrl}/images/${rating.itemId}/rating`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(rating),
    });
    // Refresh image data
    refetch();
  };

  // Track in recent items when image loads
  React.useEffect(() => {
    if (image && imageId) {
      addRecentImage(imageId);
    }
  }, [image, imageId, addRecentImage]);

  if (isLoading) {
    return <LoadingSpinner label="Loading image details..." />;
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <ErrorDisplay error={error as unknown as ErrorResponse} onRetry={() => refetch()} />
      </div>
    );
  }

  if (!image) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <Card>
          <p className="text-gray-500 mb-4">Image not found.</p>
          <Link to="/images" className="link">
            Back to Images
          </Link>
        </Card>
      </div>
    );
  }

  // Cast to expected response type for mapper
  const imageData = image as ImageDetailResponse;
  const provenance = mapProvenanceFromImageDetail(imageData);
  const filename = image.path?.split("/").pop() || image.id;

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <Link to="/images" className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block">
          Back to Images
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">{filename}</h1>
        <ProvenanceStrip {...provenance} />
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column - Preview and actions (sticky on desktop) */}
        <div className="lg:col-span-1 sticky-sidebar">
          {/* Image preview */}
          <Card title="Preview">
            <div className="flex justify-center">
              <ImageThumbnail imageId={imageId || ""} size="lg" alt={filename} />
            </div>
          </Card>

          {/* Actions */}
          <Card title="Actions">
            <div className="flex flex-col gap-2">
              <a
                href={`${import.meta.env.VITE_API_URL || "/api"}/images/${encodedImageId}/fits`}
                target="_blank"
                rel="noreferrer"
                className="btn btn-primary text-center"
              >
                Download FITS
              </a>
              <button
                type="button"
                className={`btn ${showFitsViewer ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setShowFitsViewer(!showFitsViewer)}
              >
                {showFitsViewer ? "Hide" : "Show"} FITS Viewer
              </button>
              <button
                type="button"
                className={`btn ${showRatingCard ? "btn-primary" : "btn-secondary"}`}
                onClick={() => setShowRatingCard(!showRatingCard)}
              >
                {showRatingCard ? "Hide" : "Show"} Rating
              </button>
              {imageData.qa_grade && (
                <Link to={`/qa/image/${encodedImageId}`} className="btn btn-secondary text-center">
                  View QA Report
                </Link>
              )}
              <button
                type="button"
                className="btn bg-red-100 text-red-700 hover:bg-red-200"
                onClick={() => setShowDeleteModal(true)}
              >
                Delete Image
              </button>
            </div>
          </Card>

          {/* Delete Confirmation Modal */}
          <Modal
            isOpen={showDeleteModal}
            onClose={() => setShowDeleteModal(false)}
            title="Delete Image"
            size="sm"
            footer={
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setShowDeleteModal(false)}
                  className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteImage}
                  className="px-4 py-2 text-sm text-white bg-red-600 rounded hover:bg-red-700"
                >
                  Delete
                </button>
              </div>
            }
          >
            <p className="text-gray-600">
              Are you sure you want to delete <strong>{filename}</strong>? This action cannot be
              undone.
            </p>
          </Modal>
        </div>

        {/* Right column - Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Interactive FITS Viewer */}
          {showFitsViewer && (
            <Card title="FITS Viewer">
              <FitsViewer
                fitsUrl={`${import.meta.env.VITE_API_URL || "/api"}/images/${encodedImageId}/fits`}
                displayId={`fits-${encodedImageId}`}
                width={600}
                height={500}
                showControls
                initialCenter={
                  imageData.pointing_ra_deg != null && imageData.pointing_dec_deg != null
                    ? { ra: imageData.pointing_ra_deg, dec: imageData.pointing_dec_deg }
                    : undefined
                }
              />
            </Card>
          )}

          {/* Rating Card */}
          {showRatingCard && (
            <Card title="Image Rating">
              <RatingCard
                itemId={imageId || ""}
                itemName={filename}
                tags={ratingTags}
                previousRating={
                  imageData.qa_grade
                    ? {
                        id: `rating-${imageId}`,
                        confidence:
                          imageData.qa_grade === "good"
                            ? "true"
                            : imageData.qa_grade === "fail"
                            ? "false"
                            : "unsure",
                        tag:
                          ratingTags.find(
                            (t) =>
                              t.id ===
                              (imageData.qa_grade === "good"
                                ? "good"
                                : imageData.qa_grade === "fail"
                                ? "artifact"
                                : "marginal")
                          ) || ratingTags[0],
                        user: "system",
                        date: imageData.created_at || new Date().toISOString(),
                      }
                    : undefined
                }
                onSubmit={handleRatingSubmit}
              />
            </Card>
          )}

          {/* QA Metrics */}
          {(imageData.qa_grade || imageData.noise_jy || imageData.dynamic_range) && (
            <Card title="Quality Assessment">
              <QAMetrics
                grade={imageData.qa_grade as "good" | "warn" | "fail" | undefined}
                summary={imageData.qa_summary}
                noiseJy={imageData.noise_jy}
                dynamicRange={imageData.dynamic_range}
                beamMajorArcsec={imageData.beam_major_arcsec}
                beamMinorArcsec={imageData.beam_minor_arcsec}
                beamPaDeg={imageData.beam_pa_deg}
              />
            </Card>
          )}

          {/* Coordinates */}
          {imageData.pointing_ra_deg != null && imageData.pointing_dec_deg != null && (
            <Card
              title="Pointing"
              subtitle={
                <button
                  type="button"
                  onClick={() => setShowSkyViewer(!showSkyViewer)}
                  className="text-xs text-blue-600 hover:text-blue-800"
                >
                  {showSkyViewer ? "Hide Sky View" : "Show Sky View"}
                </button>
              }
            >
              <CoordinateDisplay
                raDeg={imageData.pointing_ra_deg}
                decDeg={imageData.pointing_dec_deg}
                showDecimal
                allowFormatToggle
              />
              {showSkyViewer && (
                <div className="mt-4">
                  <AladinLiteViewer
                    raDeg={imageData.pointing_ra_deg}
                    decDeg={imageData.pointing_dec_deg}
                    fov={0.5}
                    height={250}
                    className="rounded-lg overflow-hidden"
                  />
                </div>
              )}
            </Card>
          )}

          {/* Metadata */}
          <Card title="Metadata">
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wide">Image ID</dt>
                <dd className="font-mono text-sm text-gray-900 break-all">{image.id}</dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wide">Created</dt>
                <dd className="text-sm text-gray-900">
                  {image.created_at ? (
                    <>
                      {new Date(image.created_at).toLocaleString()}
                      <span className="text-gray-500 ml-1">({relativeTime(image.created_at)})</span>
                    </>
                  ) : (
                    <span className="text-gray-400">Unknown</span>
                  )}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs text-gray-500 uppercase tracking-wide">Path</dt>
                <dd className="font-mono text-sm text-gray-900 break-all">{image.path}</dd>
              </div>
              {image.ms_path && (
                <div className="sm:col-span-2">
                  <dt className="text-xs text-gray-500 uppercase tracking-wide">
                    Source Measurement Set
                  </dt>
                  <dd className="font-mono text-sm break-all">
                    <Link
                      to={`/ms/${encodeURIComponent(image.ms_path)}`}
                      className="text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {image.ms_path}
                    </Link>
                  </dd>
                </div>
              )}
              {image.cal_table && (
                <div className="sm:col-span-2">
                  <dt className="text-xs text-gray-500 uppercase tracking-wide">
                    Calibration Table
                  </dt>
                  <dd className="font-mono text-sm text-gray-900 break-all">{image.cal_table}</dd>
                </div>
              )}
              {image.run_id && (
                <div>
                  <dt className="text-xs text-gray-500 uppercase tracking-wide">Pipeline Run</dt>
                  <dd className="text-sm">
                    <Link
                      to={`/jobs/${image.run_id}`}
                      className="text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {image.run_id}
                    </Link>
                  </dd>
                </div>
              )}
            </dl>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default ImageDetailPage;
