import type { ProvenanceStripProps, ImageDetail, MSMetadata, SourceDetail } from "../types";
import { ROUTES } from "../constants/routes";

// Re-export types for backward compatibility
export type { ImageDetail as ImageDetailResponse };
export type { MSMetadata as MSDetailResponse };
export type { SourceDetail as SourceDetailResponse };

/**
 * Maps an image detail API response to ProvenanceStripProps.
 * Handles missing fields gracefully by omitting them from the result.
 */
export function mapProvenanceFromImageDetail(image: ImageDetail): ProvenanceStripProps {
  return {
    runId: image.run_id,
    msPath: image.ms_path ?? undefined,
    calTable: image.cal_table,
    calUrl: image.cal_table ? ROUTES.INTERNAL.CAL(image.cal_table) : undefined,
    pointingRaDeg: image.pointing_ra_deg,
    pointingDecDeg: image.pointing_dec_deg,
    qaGrade: image.qa_grade,
    qaSummary: image.qa_summary,
    logsUrl: image.run_id ? ROUTES.INTERNAL.LOGS(image.run_id) : undefined,
    qaUrl: image.id ? ROUTES.INTERNAL.QA_IMAGE(image.id) : undefined,
    msUrl: image.ms_path ? ROUTES.MS.DETAIL(image.ms_path) : undefined,
    imageUrl: ROUTES.IMAGES.DETAIL(image.id),
    createdAt: image.created_at ?? undefined,
  };
}

/**
 * Maps an MS detail API response to ProvenanceStripProps.
 * Extracts the first calibrator table if available.
 */
export function mapProvenanceFromMSDetail(ms: MSMetadata): ProvenanceStripProps {
  const firstCal = ms.calibrator_matches?.[0]?.cal_table;

  return {
    runId: ms.run_id,
    msPath: ms.path,
    calTable: firstCal,
    calUrl: firstCal ? ROUTES.INTERNAL.CAL(firstCal) : undefined,
    pointingRaDeg: ms.pointing_ra_deg,
    pointingDecDeg: ms.pointing_dec_deg,
    qaGrade: ms.qa_grade,
    qaSummary: ms.qa_summary,
    logsUrl: ms.run_id ? ROUTES.INTERNAL.LOGS(ms.run_id) : undefined,
    qaUrl: ms.path ? ROUTES.INTERNAL.QA_MS(ms.path) : undefined,
    msUrl: ROUTES.MS.DETAIL(ms.path),
    createdAt: ms.created_at,
  };
}

/**
 * Maps a source detail API response to ProvenanceStripProps.
 * Uses the latest contributing image for provenance data.
 */
export function mapProvenanceFromSourceDetail(
  source: SourceDetail,
  selectedImageId?: string
): ProvenanceStripProps | null {
  // Find the selected image or use the latest
  const images = source.contributing_images ?? [];
  const image = selectedImageId
    ? images.find((img) => img.image_id === selectedImageId)
    : images[0];

  if (!image) {
    return null; // No contributing images, hide provenance strip
  }

  return {
    msPath: image.ms_path ?? undefined,
    qaGrade: image.qa_grade,
    imageUrl: ROUTES.IMAGES.DETAIL(image.image_id),
    msUrl: image.ms_path ? ROUTES.MS.DETAIL(image.ms_path) : undefined,
    createdAt: image.created_at ?? undefined,
  };
}
