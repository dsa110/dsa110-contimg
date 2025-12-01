import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "../api/client";
import type {
  ImageSummary,
  ImageDetail,
  SourceSummary,
  SourceDetail,
  MSMetadata,
  JobSummary,
  JobDetail,
  ProvenanceStripProps,
} from "../types";

// Re-export types for backward compatibility with existing imports
export type {
  ImageSummary,
  ImageDetail,
  SourceSummary,
  SourceDetail,
  MSMetadata,
  JobSummary,
  JobDetail,
};

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
  msRaster: (path: string) => ["ms", path, "raster"] as const,
  msAntennas: (path: string) => ["ms", path, "antennas"] as const,

  // Jobs
  jobs: ["jobs"] as const,
  job: (runId: string) => ["jobs", runId] as const,
  jobProvenance: (runId: string) => ["jobs", runId, "provenance"] as const,
};

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
      const response = await apiClient.get<ProvenanceStripProps>(
        `/images/${imageId}/provenance`
      );
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
      const response = await apiClient.get<SourceDetail>(
        `/sources/${sourceId}`
      );
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
      const response = await apiClient.get<MSMetadata>(
        `/ms/${encodedPath}/metadata`
      );
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
      const response = await apiClient.get<ProvenanceStripProps>(
        `/ms/${encodedPath}/provenance`
      );
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
      const response = await apiClient.get<ProvenanceStripProps>(
        `/jobs/${runId}/provenance`
      );
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
