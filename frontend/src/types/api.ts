/**
 * Centralized API type definitions.
 *
 * This file bridges frontend types with backend-generated OpenAPI types.
 * Where possible, types are re-exported from the generated schema.
 * Application-specific types extend or augment the generated types.
 *
 * Regenerate backend types with:
 *   npm run openapi:sync
 */

import type { ProvenanceStripProps } from "./provenance";
import type {
  QAGrade as GeneratedQAGrade,
  JobStatus as GeneratedJobStatus,
  CalibratorMatch as GeneratedCalibratorMatch,
  ContributingImage as GeneratedContributingImage,
} from "../api/generated";

// =============================================================================
// Shared Base Types (re-exported from generated where available)
// =============================================================================

/**
 * QA grade values used across the application.
 * Extended to include null for ungraded items.
 */
export type QAGrade = GeneratedQAGrade | null;

/**
 * Job/pipeline status values.
 * Re-exported from generated types.
 */
export type JobStatus = GeneratedJobStatus;

/**
 * Calibrator match entry from MS metadata.
 * Re-exported from generated types.
 */
export type CalibratorMatch = GeneratedCalibratorMatch;

/**
 * Contributing image entry for source detail.
 * Extended from generated types with additional frontend fields.
 */
export interface ContributingImage extends GeneratedContributingImage {
  flux_jy?: number; // Additional field used in frontend lightcurve display
}

/**
 * Base interface for entities with an ID.
 */
export interface BaseEntity {
  id: string;
}

/**
 * Mixin for entities with timestamps.
 */
export interface WithTimestamps {
  created_at?: string;
}

/**
 * Mixin for entities with provenance/pipeline tracking.
 */
export interface WithProvenance {
  run_id?: string;
  qa_grade?: QAGrade;
}

/**
 * Mixin for entities with sky coordinates.
 */
export interface WithCoordinates {
  pointing_ra_deg?: number | null;
  pointing_dec_deg?: number | null;
}

// =============================================================================
// Image Types
// =============================================================================

/**
 * Summary view of an image (used in list views).
 */
export interface ImageSummary
  extends BaseEntity,
    WithTimestamps,
    WithProvenance {
  path: string;
  qa_grade: QAGrade;
  created_at: string; // Required for images
  // Optional coordinates for sky coverage maps
  pointing_ra_deg?: number | null;
  pointing_dec_deg?: number | null;
}

/**
 * Detailed image response from API.
 * Used by ImageDetailPage and provenance mappers.
 */
export interface ImageDetail extends ImageSummary, WithCoordinates {
  ms_path?: string;
  cal_table?: string;
  qa_summary?: string;
  // QA metrics
  noise_jy?: number;
  dynamic_range?: number;
  beam_major_arcsec?: number;
  beam_minor_arcsec?: number;
  beam_pa_deg?: number;
  peak_flux_jy?: number;
  // Mosaic-specific fields
  n_images?: number;
  effective_noise_jy?: number;
  // Provenance data (when embedded)
  provenance?: ProvenanceStripProps;
}

// =============================================================================
// Source Types
// =============================================================================

/**
 * Summary view of a source (used in list views).
 */
export interface SourceSummary extends BaseEntity {
  name?: string;
  ra_deg: number;
  dec_deg: number;
  image_id?: string;
  num_images?: number; // Count of contributing images
  // Variability metrics
  eta?: number;
  v?: number;
  peak_flux_jy?: number;
}

/**
 * Detailed source response from API.
 */
export interface SourceDetail extends SourceSummary {
  flux_jy?: number;
  peak_flux?: number;
  integrated_flux?: number;
  contributing_images?: ContributingImage[];
  latest_image_id?: string;
  provenance?: ProvenanceStripProps;
}

// =============================================================================
// Measurement Set (MS) Types
// =============================================================================

/**
 * Measurement Set metadata response.
 */
export interface MSMetadata
  extends WithCoordinates,
    WithTimestamps,
    WithProvenance {
  path: string;
  cal_table?: string;
  scan_id?: string;
  num_channels?: number;
  integration_time_s?: number;
  qa_summary?: string;
  calibrator_matches?: CalibratorMatch[];
  provenance?: ProvenanceStripProps;
}

// =============================================================================
// Job Types
// =============================================================================

/**
 * Summary view of a job (used in list views).
 */
export interface JobSummary {
  run_id: string;
  status: JobStatus;
  started_at?: string;
  finished_at?: string;
}

/**
 * Detailed job response from API.
 */
export interface JobDetail extends JobSummary {
  logs_url?: string;
  config?: Record<string, unknown>;
  provenance?: ProvenanceStripProps;
}
