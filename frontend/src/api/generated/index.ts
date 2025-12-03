/**
 * Auto-generated API Types
 *
 * This module re-exports types generated from the backend OpenAPI schema.
 *
 * Usage:
 *   import type { components, paths, operations } from '../api/generated';
 *
 *   // Access schema types
 *   type ImageDetail = components['schemas']['ImageDetailResponse'];
 *   type SourceList = components['schemas']['SourceListResponse'];
 *
 *   // Access path types for request/response
 *   type ListImagesResponse = paths['/api/v1/images']['get']['responses']['200']['content']['application/json'];
 *
 * Regenerate with:
 *   npm run openapi:sync
 */

export type * from "./api.d.ts";

// Re-export commonly used schema types for convenience
import type { components } from "./api.d.ts";

// ============================================================================
// Image Types
// ============================================================================
export type ImageListResponse = components["schemas"]["ImageListResponse"];
export type ImageDetailResponse = components["schemas"]["ImageDetailResponse"];
export type ImageVersionInfo = components["schemas"]["ImageVersionInfo"];
export type ImageVersionChainResponse =
  components["schemas"]["ImageVersionChainResponse"];
export type ReimageRequest = components["schemas"]["ReimageRequest"];
export type ReimageResponse = components["schemas"]["ReimageResponse"];

// ============================================================================
// Source Types
// ============================================================================
export type SourceListResponse = components["schemas"]["SourceListResponse"];
export type SourceDetailResponse =
  components["schemas"]["SourceDetailResponse"];
export type ContributingImage = components["schemas"]["ContributingImage"];

// ============================================================================
// Measurement Set Types
// ============================================================================
export type MSDetailResponse = components["schemas"]["MSDetailResponse"];
export type CalibratorMatch = components["schemas"]["CalibratorMatch"];
export type AntennaInfo = components["schemas"]["AntennaInfo"];
export type AntennaLayoutResponse =
  components["schemas"]["AntennaLayoutResponse"];

// ============================================================================
// Job/Pipeline Types
// ============================================================================
export type JobListResponse = components["schemas"]["JobListResponse"];
export type JobStatus = components["schemas"]["JobStatus"];
export type JobInfo = components["schemas"]["JobInfo"];
export type ProvenanceResponse = components["schemas"]["ProvenanceResponse"];

// ============================================================================
// Interactive Imaging Types
// ============================================================================
export type InteractiveCleanRequest =
  components["schemas"]["InteractiveCleanRequest"];
export type InteractiveCleanResponse =
  components["schemas"]["InteractiveCleanResponse"];
export type ImagingDefaultsResponse =
  components["schemas"]["ImagingDefaultsResponse"];
export type SessionInfo = components["schemas"]["SessionInfo"];
export type SessionListResponse = components["schemas"]["SessionListResponse"];

// ============================================================================
// Calibrator Imaging Types
// ============================================================================
export type CalibratorInfo = components["schemas"]["CalibratorInfo"];
export type TransitInfo = components["schemas"]["TransitInfo"];
export type ObservationInfo = components["schemas"]["ObservationInfo"];
export type MSGenerationRequest = components["schemas"]["MSGenerationRequest"];
export type MSGenerationResponse =
  components["schemas"]["MSGenerationResponse"];
export type CalibrationRequest = components["schemas"]["CalibrationRequest"];
export type CalibrationResponse = components["schemas"]["CalibrationResponse"];
export type ImagingRequest = components["schemas"]["ImagingRequest"];
export type ImagingResponse = components["schemas"]["ImagingResponse"];
export type PhotometryResult = components["schemas"]["PhotometryResult"];

// ============================================================================
// Health Monitoring Types
// ============================================================================
export type SystemHealthReport = components["schemas"]["SystemHealthReport"];
export type ServiceHealthStatus = components["schemas"]["ServiceHealthStatus"];
export type HealthSummary = components["schemas"]["HealthSummary"];
export type ActiveValidityWindows =
  components["schemas"]["ActiveValidityWindows"];
export type PointingStatusResponse =
  components["schemas"]["PointingStatusResponse"];
export type TransitPrediction = components["schemas"]["TransitPrediction"];

// ============================================================================
// Queue/Workflow Types (ABSURD)
// ============================================================================
export type TaskResponse = components["schemas"]["TaskResponse"];
export type TaskListResponse = components["schemas"]["TaskListResponse"];
export type QueueStatsResponse = components["schemas"]["QueueStatsResponse"];
export type WorkflowTemplate = components["schemas"]["WorkflowTemplate"];
export type WorkflowTemplateStep =
  components["schemas"]["WorkflowTemplateStep"];
export type MetricsResponse = components["schemas"]["MetricsResponse"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type WorkerResponse = components["schemas"]["WorkerResponse"];
export type WorkerListResponse = components["schemas"]["WorkerListResponse"];
export type WorkerMetricsResponse =
  components["schemas"]["WorkerMetricsResponse"];

// ============================================================================
// Mask/Region Types
// ============================================================================
export type MaskResponse = components["schemas"]["MaskResponse"];
export type MaskListResponse = components["schemas"]["MaskListResponse"];
export type MaskCreateRequest = components["schemas"]["MaskCreateRequest"];
export type RegionResponse = components["schemas"]["RegionResponse"];
export type RegionListResponse = components["schemas"]["RegionListResponse"];
export type RegionCreateRequest = components["schemas"]["RegionCreateRequest"];

// ============================================================================
// Mosaic Types
// ============================================================================
export type MosaicRequest = components["schemas"]["MosaicRequest"];
export type MosaicResponse = components["schemas"]["MosaicResponse"];
export type MosaicStatusResponse =
  components["schemas"]["MosaicStatusResponse"];

// ============================================================================
// Error Types
// ============================================================================
export type HTTPValidationError = components["schemas"]["HTTPValidationError"];
export type ValidationError = components["schemas"]["ValidationError"];

// ============================================================================
// QA Grade Type (extracted from enums)
// ============================================================================
export type QAGrade = "good" | "warn" | "fail";
