import type {
  ProvenanceStripProps,
  ImageDetail,
  MSMetadata,
  SourceDetail,
  CalibratorMatch,
} from "../types";

// Re-export types for backward compatibility
export type { ImageDetail as ImageDetailResponse };
export type { MSMetadata as MSDetailResponse };
export type { SourceDetail as SourceDetailResponse };

/**
 * Maps an image detail API response to ProvenanceStripProps.
 * Handles missing fields gracefully by omitting them from the result.
 */
export function mapProvenanceFromImageDetail(image: ImageDetailResponse): ProvenanceStripProps {
  return {
    runId: image.run_id,
    msPath: image.ms_path,
    calTable: image.cal_table,
    calUrl: image.cal_table ? `/cal/${encodeURIComponent(image.cal_table)}` : undefined,
    pointingRaDeg: image.pointing_ra_deg,
    pointingDecDeg: image.pointing_dec_deg,
    qaGrade: image.qa_grade,
    qaSummary: image.qa_summary,
    logsUrl: image.run_id ? `/logs/${image.run_id}` : undefined,
    qaUrl: image.id ? `/qa/image/${image.id}` : undefined,
    msUrl: image.ms_path ? `/ms/${encodeURIComponent(image.ms_path)}` : undefined,
    imageUrl: `/images/${image.id}`,
    createdAt: image.created_at,
  };
}

/**
 * Maps an MS detail API response to ProvenanceStripProps.
 * Extracts the first calibrator table if available.
 */
export function mapProvenanceFromMSDetail(ms: MSDetailResponse): ProvenanceStripProps {
  const firstCal = ms.calibrator_matches?.[0]?.cal_table;

  return {
    runId: ms.run_id,
    msPath: ms.path,
    calTable: firstCal,
    calUrl: firstCal ? `/cal/${encodeURIComponent(firstCal)}` : undefined,
    pointingRaDeg: ms.pointing_ra_deg,
    pointingDecDeg: ms.pointing_dec_deg,
    qaGrade: ms.qa_grade,
    qaSummary: ms.qa_summary,
    logsUrl: ms.run_id ? `/logs/${ms.run_id}` : undefined,
    qaUrl: ms.path ? `/qa/ms/${encodeURIComponent(ms.path)}` : undefined,
    msUrl: `/ms/${encodeURIComponent(ms.path)}`,
    createdAt: ms.created_at,
  };
}

/**
 * Maps a source detail API response to ProvenanceStripProps.
 * Uses the latest contributing image for provenance data.
 */
export function mapProvenanceFromSourceDetail(
  source: SourceDetailResponse,
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
    msPath: image.ms_path,
    qaGrade: image.qa_grade,
    imageUrl: `/images/${image.image_id}`,
    msUrl: image.ms_path ? `/ms/${encodeURIComponent(image.ms_path)}` : undefined,
    createdAt: image.created_at,
  };
}
