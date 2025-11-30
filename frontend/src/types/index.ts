/**
 * Centralized type exports.
 *
 * Import types from this barrel file:
 * import { ImageSummary, QAGrade } from '../types';
 */

// API types
export type {
  // Base types
  QAGrade,
  JobStatus,
  BaseEntity,
  WithTimestamps,
  WithProvenance,
  WithCoordinates,
  CalibratorMatch,
  // Image types
  ImageSummary,
  ImageDetail,
  // Source types
  SourceSummary,
  SourceDetail,
  ContributingImage,
  // MS types
  MSMetadata,
  // Job types
  JobSummary,
  JobDetail,
  // Deprecated aliases
  ImageDetailResponse,
  MSDetailResponse,
  SourceDetailResponse,
} from "./api";

// Error types
export type { ErrorResponse, ErrorSeverity, MappedError } from "./errors";

// Provenance types
export type { ProvenanceStripProps } from "./provenance";
