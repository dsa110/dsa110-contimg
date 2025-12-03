import React, { useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import ProvenanceStrip from "../components/provenance/ProvenanceStrip";
import ErrorDisplay from "../components/errors/ErrorDisplay";
import { WidgetErrorBoundary } from "../components/errors";
import {
  Card,
  CoordinateDisplay,
  ImageThumbnail,
  Modal,
  PageSkeleton,
  QAMetrics,
} from "../components/common";
import { AladinLiteViewer, GifPlayer } from "../components/widgets";
import { FitsViewer, MaskToolbar, RegionToolbar } from "../components/fits";
import type { Region, RegionFormat } from "../components/fits";
import { RatingCard, RatingTag } from "../components/rating";
import { mapProvenanceFromImageDetail } from "../utils/provenanceMappers";
import { relativeTime } from "../utils/relativeTime";
import { logger } from "../utils/logger";
import type { ErrorResponse, ImageDetail } from "../types";
import { useImageDetail } from "../hooks/useImageDetail";
import { ROUTES } from "../constants/routes";
import { config } from "../config";
import { saveImageRegions } from "../api/images";
import { useNotifications } from "../hooks/useNotifications";

/**
 * Detail page for a single image.
 * Displays image metadata, provenance strip, and visualization options.
 */
const ImageDetailPage: React.FC = () => {
  const { imageId } = useParams<{ imageId: string }>();

  // Use centralized hook for image detail logic
  const {
    image,
    isLoading,
    error,
    refetch,
    deleteState,
    openDeleteModal,
    closeDeleteModal,
    confirmDelete,
    submitRating,
    encodedImageId,
    filename,
  } = useImageDetail(imageId);

  const [showSkyViewer, setShowSkyViewer] = useState(true);
  const [showFitsViewer, setShowFitsViewer] = useState(false);
  const [showGifPlayer, setShowGifPlayer] = useState(false);
  const [showRatingCard, setShowRatingCard] = useState(false);
  const [showMaskTools, setShowMaskTools] = useState(false);
  const [showRegionTools, setShowRegionTools] = useState(false);
  const { notifySuccess, notifyError } = useNotifications();

  // Handlers for region/mask tools
  const handleRegionSave = useCallback(
    async (regions: Region[], format: RegionFormat) => {
      if (!imageId) {
        return;
      }
      try {
        await saveImageRegions(imageId, { format, regions });
        notifySuccess(
          "Regions saved",
          `${regions.length} region${regions.length === 1 ? "" : "s"} stored for ${filename}`
        );
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to save image regions";
        notifyError("Failed to save regions", message);
        logger.error("Failed to save image regions", err);
      }
    },
    [filename, imageId, notifyError, notifySuccess]
  );

  const handleMaskSaved = useCallback((maskPath: string) => {
    logger.info("Mask saved", { path: maskPath });
    // Optionally show a toast notification
  }, []);

  // Rating tags for QA assessment
  const ratingTags: RatingTag[] = [
    {
      id: "artifact",
      name: "Artifact",
      color: "#EF4444",
      description: "Image contains artifacts",
    },
    {
      id: "good",
      name: "Good Quality",
      color: "#22C55E",
      description: "Image passes QA",
    },
    {
      id: "marginal",
      name: "Marginal",
      color: "#F59E0B",
      description: "Borderline quality",
    },
    {
      id: "rfi",
      name: "RFI",
      color: "#8B5CF6",
      description: "Radio frequency interference",
    },
  ];

  // Recent items tracking is now handled by useImageDetail hook

  if (isLoading) {
    return <PageSkeleton variant="detail" showHeader showSidebar />;
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <ErrorDisplay
          error={error as unknown as ErrorResponse}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  if (!image) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <Card>
          <p className="text-gray-500 mb-4">Image not found.</p>
          <Link to={ROUTES.IMAGES.LIST} className="link">
            Back to Images
          </Link>
        </Card>
      </div>
    );
  }

  // Cast to expected response type for mapper
  const imageData = image as ImageDetail;
  const provenance = mapProvenanceFromImageDetail(imageData);

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <Link
          to={ROUTES.IMAGES.LIST}
          className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block"
        >
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
              <ImageThumbnail
                imageId={imageId || ""}
                size="lg"
                alt={filename}
              />
            </div>
          </Card>

          {/* Actions */}
          <Card title="Actions">
            <div className="flex flex-col gap-2">
              <a
                href={`${config.api.baseUrl}/images/${encodedImageId}/fits`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary text-center"
              >
                Download FITS
              </a>
              <button
                type="button"
                className={`btn ${
                  showFitsViewer ? "btn-primary" : "btn-secondary"
                }`}
                onClick={() => setShowFitsViewer(!showFitsViewer)}
              >
                {showFitsViewer ? "Hide" : "Show"} FITS Viewer
              </button>
              <button
                type="button"
                className={`btn ${
                  showGifPlayer ? "btn-primary" : "btn-secondary"
                }`}
                onClick={() => setShowGifPlayer(!showGifPlayer)}
              >
                {showGifPlayer ? "Hide" : "Show"} Animation
              </button>
              <button
                type="button"
                className={`btn ${
                  showRatingCard ? "btn-primary" : "btn-secondary"
                }`}
                onClick={() => setShowRatingCard(!showRatingCard)}
              >
                {showRatingCard ? "Hide" : "Show"} Rating
              </button>

              {/* Separator for analysis tools */}
              <div className="border-t border-gray-200 my-2" />
              <p className="text-xs text-gray-500 uppercase tracking-wide">
                Analysis Tools
              </p>

              <button
                type="button"
                className={`btn ${
                  showMaskTools ? "btn-primary" : "btn-secondary"
                }`}
                onClick={() => {
                  setShowMaskTools(!showMaskTools);
                  if (!showFitsViewer && !showMaskTools)
                    setShowFitsViewer(true);
                }}
              >
                {showMaskTools ? "Hide" : "Show"} Mask Tools
              </button>
              <button
                type="button"
                className={`btn ${
                  showRegionTools ? "btn-primary" : "btn-secondary"
                }`}
                onClick={() => {
                  setShowRegionTools(!showRegionTools);
                  if (!showFitsViewer && !showRegionTools)
                    setShowFitsViewer(true);
                }}
              >
                {showRegionTools ? "Hide" : "Show"} Region Tools
              </button>

              <div className="border-t border-gray-200 my-2" />

              {imageData.qa_grade && (
                <Link
                  to={`/qa/image/${encodedImageId}`}
                  className="btn btn-secondary text-center"
                >
                  View QA Report
                </Link>
              )}
              <button
                type="button"
                className="btn bg-red-100 text-red-700 hover:bg-red-200"
                onClick={openDeleteModal}
              >
                Delete Image
              </button>
            </div>
          </Card>

          {/* Delete Confirmation Modal */}
          <Modal
            isOpen={deleteState.showModal}
            onClose={closeDeleteModal}
            title="Delete Image"
            size="sm"
            footer={
              <div className="flex justify-end gap-2">
                <button
                  onClick={closeDeleteModal}
                  disabled={deleteState.isDeleting}
                  className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDelete}
                  disabled={deleteState.isDeleting}
                  className="px-4 py-2 text-sm text-white bg-red-600 rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {deleteState.isDeleting ? "Deleting..." : "Delete"}
                </button>
              </div>
            }
          >
            <p className="text-gray-600">
              Are you sure you want to delete <strong>{filename}</strong>? This
              action cannot be undone.
            </p>
            {deleteState.error && (
              <p className="mt-3 text-sm text-red-600 bg-red-50 p-2 rounded">
                Error: {deleteState.error}
              </p>
            )}
          </Modal>
        </div>

        {/* Right column - Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Interactive FITS Viewer */}
          {showFitsViewer && (
            <Card title="FITS Viewer">
              <WidgetErrorBoundary widgetName="FITS Viewer" minHeight={500}>
                <FitsViewer
                  fitsUrl={`${config.api.baseUrl}/images/${encodedImageId}/fits`}
                  displayId={`fits-${encodedImageId}`}
                  width={600}
                  height={500}
                  showControls
                  initialCenter={
                    imageData.pointing_ra_deg != null &&
                    imageData.pointing_dec_deg != null
                      ? {
                          ra: imageData.pointing_ra_deg,
                          dec: imageData.pointing_dec_deg,
                        }
                      : undefined
                  }
                />
              </WidgetErrorBoundary>

              {/* Mask Tools - shown below FITS viewer when enabled */}
              {showMaskTools && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Clean Mask Tools
                  </h4>
                  <p className="text-xs text-gray-500 mb-3">
                    Draw mask regions to use during re-imaging. Masks are saved
                    in DS9 format.
                  </p>
                  <MaskToolbar
                    displayId={`fits-${encodedImageId}`}
                    imageId={imageId || ""}
                    onMaskSaved={handleMaskSaved}
                  />
                </div>
              )}

              {/* Region Tools - shown below FITS viewer when enabled */}
              {showRegionTools && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Region Tools
                  </h4>
                  <p className="text-xs text-gray-500 mb-3">
                    Draw and export regions in DS9, CRTF, or JSON format.
                  </p>
                  <RegionToolbar
                    displayId={`fits-${encodedImageId}`}
                    onSave={handleRegionSave}
                  />
                </div>
              )}
            </Card>
          )}

          {/* Animated FITS Cutout Visualization */}
          {showGifPlayer && (
            <Card title="Animated Cutout" subtitle="Time-lapse visualization">
              <WidgetErrorBoundary
                widgetName="Animation Player"
                minHeight={400}
              >
                <GifPlayer
                  src={`${config.api.baseUrl}/images/${encodedImageId}/animation`}
                  width="100%"
                  height={400}
                  autoPlay={false}
                  loop={true}
                  speed={1}
                  showFrameCounter={true}
                  showTimeline={true}
                  onFrameChange={(frameIndex, totalFrames) => {
                    logger.debug(
                      `Animation frame: ${frameIndex + 1}/${totalFrames}`
                    );
                  }}
                  className="rounded-lg overflow-hidden"
                />
              </WidgetErrorBoundary>
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
                onSubmit={(rating) =>
                  submitRating({
                    confidence: rating.confidence,
                    tagId: rating.tagId,
                    notes: rating.notes,
                  })
                }
              />
            </Card>
          )}

          {/* QA Metrics */}
          {(imageData.qa_grade ||
            imageData.noise_jy ||
            imageData.dynamic_range) && (
            <Card title="Quality Assessment">
              <QAMetrics
                grade={
                  imageData.qa_grade as "good" | "warn" | "fail" | undefined
                }
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
          {imageData.pointing_ra_deg != null &&
            imageData.pointing_dec_deg != null && (
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
                    <WidgetErrorBoundary
                      widgetName="Sky Viewer"
                      minHeight={250}
                    >
                      <AladinLiteViewer
                        raDeg={imageData.pointing_ra_deg}
                        decDeg={imageData.pointing_dec_deg}
                        fov={0.5}
                        height={250}
                        className="rounded-lg overflow-hidden"
                      />
                    </WidgetErrorBoundary>
                  </div>
                )}
              </Card>
            )}

          {/* Metadata */}
          <Card title="Metadata">
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wide">
                  Image ID
                </dt>
                <dd className="font-mono text-sm text-gray-900 break-all">
                  {image.id}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wide">
                  Created
                </dt>
                <dd className="text-sm text-gray-900">
                  {image.created_at ? (
                    <>
                      {new Date(image.created_at).toLocaleString()}
                      <span className="text-gray-500 ml-1">
                        ({relativeTime(image.created_at)})
                      </span>
                    </>
                  ) : (
                    <span className="text-gray-400">Unknown</span>
                  )}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs text-gray-500 uppercase tracking-wide">
                  Path
                </dt>
                <dd className="font-mono text-sm text-gray-900 break-all">
                  {image.path}
                </dd>
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
                  <dd className="font-mono text-sm text-gray-900 break-all">
                    {image.cal_table}
                  </dd>
                </div>
              )}
              {image.run_id && (
                <div>
                  <dt className="text-xs text-gray-500 uppercase tracking-wide">
                    Pipeline Run
                  </dt>
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
