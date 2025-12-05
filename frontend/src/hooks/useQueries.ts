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

  // Interactive Imaging
  imagingSessions: ["imaging", "sessions"] as const,
  imagingSession: (id: string) => ["imaging", "sessions", id] as const,
  imagingDefaults: ["imaging", "defaults"] as const,
  imagingStatus: ["imaging", "status"] as const,
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
      const response = await apiClient.get<ImageDetail>(
        `/images/${imageId}`
      );
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

// =============================================================================
// Interactive Imaging hooks
// =============================================================================

/**
 * Types for interactive imaging
 */
export interface ImagingSession {
  id: string;
  port: number;
  url: string;
  ms_path: string;
  imagename: string;
  created_at: string;
  age_hours: number;
  is_alive: boolean;
  user_id?: string;
}

export interface ImagingSessionsResponse {
  sessions: ImagingSession[];
  total: number;
  available_ports: number;
}

export interface ImagingDefaults {
  imsize: number[];
  cell: string;
  specmode: string;
  deconvolver: string;
  weighting: string;
  robust: number;
  niter: number;
  threshold: string;
  nterms: number;
  datacolumn: string;
}

export interface InteractiveCleanRequest {
  ms_path: string;
  imagename: string;
  imsize?: number[];
  cell?: string;
  specmode?: string;
  deconvolver?: string;
  weighting?: string;
  robust?: number;
  niter?: number;
  threshold?: string;
}

export interface InteractiveCleanResponse {
  session_id: string;
  url: string;
  status: string;
  ms_path: string;
  imagename: string;
}

/**
 * Fetch list of active imaging sessions.
 */
export function useImagingSessions() {
  return useQuery({
    queryKey: queryKeys.imagingSessions,
    queryFn: async () => {
      const response = await apiClient.get<ImagingSessionsResponse>(
        "/imaging/sessions"
      );
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

/**
 * Fetch a single imaging session by ID.
 */
export function useImagingSession(sessionId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.imagingSession(sessionId ?? ""),
    queryFn: async () => {
      const response = await apiClient.get<ImagingSession>(
        `/imaging/sessions/${sessionId}`
      );
      return response.data;
    },
    enabled: !!sessionId,
  });
}

/**
 * Fetch DSA-110 default imaging parameters.
 */
export function useImagingDefaults() {
  return useQuery({
    queryKey: queryKeys.imagingDefaults,
    queryFn: async () => {
      const response = await apiClient.get<ImagingDefaults>(
        "/imaging/defaults"
      );
      return response.data;
    },
    staleTime: Infinity, // Defaults don't change
  });
}

/**
 * Start a new interactive clean session.
 */
export function useStartInteractiveClean() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: InteractiveCleanRequest) => {
      const response = await apiClient.post<InteractiveCleanResponse>(
        "/imaging/interactive",
        request
      );
      return response.data;
    },
    onSuccess: () => {
      // Invalidate sessions list to show new session
      queryClient.invalidateQueries({ queryKey: queryKeys.imagingSessions });
    },
  });
}

/**
 * Stop an imaging session.
 */
export function useStopSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (sessionId: string) => {
      const response = await apiClient.delete(
        `/imaging/sessions/${sessionId}`
      );
      return response.data;
    },
    onSuccess: () => {
      // Invalidate sessions list
      queryClient.invalidateQueries({ queryKey: queryKeys.imagingSessions });
    },
  });
}
