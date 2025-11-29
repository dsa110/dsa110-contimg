import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "../api/client";
import type { ProvenanceStripProps } from "../types/provenance";

// =============================================================================
// Query Keys - centralized for cache invalidation
// =============================================================================

export const queryKeys = {
  // Images
  images: ["images"] as const,
  image: (id: string) => ["images", id] as const,
  imageProvenance: (id: string) => ["images", id, "provenance"] as const,

  // Sources
  sources: ["sources"] as const,
  source: (id: string) => ["sources", id] as const,

  // MS (Measurement Sets)
  ms: (path: string) => ["ms", path] as const,
  msProvenance: (path: string) => ["ms", path, "provenance"] as const,

  // Jobs
  jobs: ["jobs"] as const,
  job: (runId: string) => ["jobs", runId] as const,
  jobProvenance: (runId: string) => ["jobs", runId, "provenance"] as const,
};

// =============================================================================
// Types for API responses
// =============================================================================

export interface ImageSummary {
  id: string;
  path: string;
  qa_grade: "good" | "warn" | "fail" | null;
  created_at: string;
  run_id?: string;
}

export interface ImageDetail extends ImageSummary {
  ms_path?: string;
  cal_table?: string;
  provenance?: ProvenanceStripProps;
}

export interface SourceSummary {
  id: string;
  name: string;
  ra_deg: number;
  dec_deg: number;
  image_id?: string;
  num_images?: number; // count of contributing images
}

export interface SourceDetail extends SourceSummary {
  flux_jy?: number;
  peak_flux?: number;
  integrated_flux?: number;
  provenance?: ProvenanceStripProps;
}

export interface MSMetadata {
  path: string;
  cal_table?: string;
  scan_id?: string;
  num_channels?: number;
  integration_time_s?: number;
  pointing_ra_deg?: number;
  pointing_dec_deg?: number;
  created_at?: string;
  qa_grade?: "good" | "warn" | "fail" | null;
  calibrator_matches?: Array<{ type: string; cal_table: string }>;
  provenance?: ProvenanceStripProps;
}

export interface JobSummary {
  run_id: string;
  status: "pending" | "running" | "completed" | "failed";
  started_at?: string;
  finished_at?: string;
}

export interface JobDetail extends JobSummary {
  logs_url?: string;
  config?: Record<string, unknown>;
  provenance?: ProvenanceStripProps;
}

// =============================================================================
// Images hooks
// =============================================================================

/**
 * Fetch list of all images.
 */
export function useImages() {
  return useQuery({
    queryKey: queryKeys.images,
    queryFn: async () => {
      const response = await apiClient.get<ImageSummary[]>("/images");
      return response.data;
    },
  });
}

/**
 * Fetch a single image by ID.
 */
export function useImage(imageId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.image(imageId ?? ""),
    queryFn: async () => {
      const response = await apiClient.get<ImageDetail>(`/images/${imageId}`);
      return response.data;
    },
    enabled: !!imageId,
  });
}

/**
 * Fetch provenance data for an image.
 */
export function useImageProvenance(imageId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.imageProvenance(imageId ?? ""),
    queryFn: async () => {
      const response = await apiClient.get<ProvenanceStripProps>(`/images/${imageId}/provenance`);
      return response.data;
    },
    enabled: !!imageId,
  });
}

// =============================================================================
// Sources hooks
// =============================================================================

/**
 * Fetch list of all sources.
 */
export function useSources() {
  return useQuery({
    queryKey: queryKeys.sources,
    queryFn: async () => {
      const response = await apiClient.get<SourceSummary[]>("/sources");
      return response.data;
    },
  });
}

/**
 * Fetch a single source by ID.
 */
export function useSource(sourceId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.source(sourceId ?? ""),
    queryFn: async () => {
      const response = await apiClient.get<SourceDetail>(`/sources/${sourceId}`);
      return response.data;
    },
    enabled: !!sourceId,
  });
}

// =============================================================================
// MS (Measurement Set) hooks
// =============================================================================

/**
 * Fetch MS metadata by path.
 * Path should be URL-encoded if it contains special characters.
 */
export function useMS(path: string | undefined) {
  return useQuery({
    queryKey: queryKeys.ms(path ?? ""),
    queryFn: async () => {
      const encodedPath = encodeURIComponent(path ?? "");
      const response = await apiClient.get<MSMetadata>(`/ms/${encodedPath}/metadata`);
      return response.data;
    },
    enabled: !!path,
  });
}

/**
 * Fetch provenance data for an MS.
 */
export function useMSProvenance(path: string | undefined) {
  return useQuery({
    queryKey: queryKeys.msProvenance(path ?? ""),
    queryFn: async () => {
      const encodedPath = encodeURIComponent(path ?? "");
      const response = await apiClient.get<ProvenanceStripProps>(`/ms/${encodedPath}/provenance`);
      return response.data;
    },
    enabled: !!path,
  });
}

// =============================================================================
// Jobs hooks
// =============================================================================

/**
 * Fetch list of all jobs.
 */
export function useJobs() {
  return useQuery({
    queryKey: queryKeys.jobs,
    queryFn: async () => {
      const response = await apiClient.get<JobSummary[]>("/jobs");
      return response.data;
    },
  });
}

/**
 * Fetch a single job by run ID.
 */
export function useJob(runId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.job(runId ?? ""),
    queryFn: async () => {
      const response = await apiClient.get<JobDetail>(`/jobs/${runId}`);
      return response.data;
    },
    enabled: !!runId,
  });
}

/**
 * Fetch provenance data for a job.
 */
export function useJobProvenance(runId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.jobProvenance(runId ?? ""),
    queryFn: async () => {
      const response = await apiClient.get<ProvenanceStripProps>(`/jobs/${runId}/provenance`);
      return response.data;
    },
    enabled: !!runId,
  });
}

// =============================================================================
// Mutations (placeholders for future CRUD operations)
// =============================================================================

/**
 * Example mutation hook for re-running a job.
 * Invalidates the jobs list and specific job on success.
 */
export function useRerunJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (runId: string) => {
      const response = await apiClient.post(`/jobs/${runId}/rerun`);
      return response.data;
    },
    onSuccess: (_data, runId) => {
      // Invalidate related queries to refetch fresh data
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs });
      queryClient.invalidateQueries({ queryKey: queryKeys.job(runId) });
    },
  });
}
