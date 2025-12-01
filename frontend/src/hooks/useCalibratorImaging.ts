/**
 * React Query hooks for the Calibrator Imaging API.
 *
 * These hooks interact with the /api/v1/calibrator-imaging endpoints
 * to provide the full pipeline workflow: HDF5 → MS → Calibration → Imaging.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "../api/client";

// =============================================================================
// Types
// =============================================================================

export interface CalibratorInfo {
  id: number;
  name: string;
  ra_deg: number;
  dec_deg: number;
  flux_jy: number | null;
  status: string;
}

export interface TransitInfo {
  transit_time_iso: string;
  transit_time_mjd: number;
  has_data: boolean;
  num_subband_groups: number;
  observation_ids: string[];
}

export interface ObservationInfo {
  observation_id: string;
  start_time_iso: string;
  mid_time_iso: string;
  end_time_iso: string;
  num_subbands: number;
  file_paths: string[];
  delta_from_transit_min: number;
}

export interface MSGenerationRequest {
  calibrator_name: string;
  observation_id: string;
  output_name?: string;
}

export interface MSGenerationResponse {
  job_id: string;
  status: string;
  ms_path: string | null;
}

export interface CalibrationRequest {
  ms_path: string;
  calibrator_name: string;
}

export interface CalibrationResponse {
  job_id: string;
  status: string;
  cal_table_path: string | null;
}

export interface ImagingRequest {
  ms_path: string;
  imsize?: number;
  cell?: string;
  niter?: number;
  threshold?: string;
}

export interface ImagingResponse {
  job_id: string;
  status: string;
  image_path: string | null;
}

export interface JobInfo {
  job_id: string;
  job_type: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  result: Record<string, unknown> | null;
}

export interface PhotometryResult {
  source_name: string;
  ra_deg: number;
  dec_deg: number;
  peak_flux_jy: number;
  integrated_flux_jy: number;
  rms_jy: number;
  snr: number;
}

export interface HealthStatusDetail {
  path: string;
  exists: boolean;
  hdf5_file_count?: number;
  ms_file_count?: number;
}

export interface HealthStatus {
  status: "healthy" | "degraded";
  configuration?: {
    hdf5_db?: HealthStatusDetail;
    products_db?: HealthStatusDetail;
    calibrators_db?: HealthStatusDetail;
    incoming_dir?: HealthStatusDetail;
    output_ms_dir?: HealthStatusDetail;
    output_images_dir?: HealthStatusDetail;
  };
  // Legacy flat fields for backward compatibility
  hdf5_db_exists: boolean;
  calibrators_db_exists: boolean;
  incoming_dir_exists: boolean;
  output_ms_dir_exists: boolean;
  output_images_dir_exists: boolean;
}

// =============================================================================
// Query Keys
// =============================================================================

export const calibratorImagingKeys = {
  all: ["calibrator-imaging"] as const,
  calibrators: () => [...calibratorImagingKeys.all, "calibrators"] as const,
  transits: (calibratorName: string) =>
    [...calibratorImagingKeys.all, "transits", calibratorName] as const,
  observations: (calibratorName: string, transitTime: string) =>
    [
      ...calibratorImagingKeys.all,
      "observations",
      calibratorName,
      transitTime,
    ] as const,
  job: (jobId: string) => [...calibratorImagingKeys.all, "job", jobId] as const,
  photometry: (imagePath: string) =>
    [...calibratorImagingKeys.all, "photometry", imagePath] as const,
  health: () => [...calibratorImagingKeys.all, "health"] as const,
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch list of bandpass calibrators.
 */
export function useCalibratorList(status: string = "active") {
  return useQuery({
    queryKey: calibratorImagingKeys.calibrators(),
    queryFn: async () => {
      const response = await apiClient.get<CalibratorInfo[]>(
        "/calibrator-imaging/calibrators",
        { params: { status } }
      );
      return response.data;
    },
  });
}

/**
 * Fetch transit times for a calibrator with data availability info.
 */
export function useCalibratorTransits(
  calibratorName: string | null,
  daysBack: number = 7,
  daysForward: number = 2
) {
  return useQuery({
    queryKey: calibratorImagingKeys.transits(calibratorName ?? ""),
    queryFn: async () => {
      const response = await apiClient.get<TransitInfo[]>(
        `/calibrator-imaging/calibrators/${encodeURIComponent(
          calibratorName!
        )}/transits`,
        {
          params: {
            days_back: daysBack,
            days_forward: daysForward,
          },
        }
      );
      return response.data;
    },
    enabled: !!calibratorName,
  });
}

/**
 * Fetch available observations around a specific transit time.
 */
export function useCalibratorObservations(
  calibratorName: string | null,
  transitTimeIso: string | null,
  windowMinutes: number = 60
) {
  return useQuery({
    queryKey: calibratorImagingKeys.observations(
      calibratorName ?? "",
      transitTimeIso ?? ""
    ),
    queryFn: async () => {
      const response = await apiClient.get<ObservationInfo[]>(
        `/calibrator-imaging/calibrators/${encodeURIComponent(
          calibratorName!
        )}/observations`,
        {
          params: {
            transit_time_iso: transitTimeIso,
            window_minutes: windowMinutes,
          },
        }
      );
      return response.data;
    },
    enabled: !!calibratorName && !!transitTimeIso,
  });
}

/**
 * Start MS generation from HDF5 files.
 */
export function useGenerateMS() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: MSGenerationRequest) => {
      const response = await apiClient.post<MSGenerationResponse>(
        "/calibrator-imaging/generate-ms",
        request
      );
      return response.data;
    },
    onSuccess: (data) => {
      // Invalidate job query to start polling
      queryClient.invalidateQueries({
        queryKey: calibratorImagingKeys.job(data.job_id),
      });
    },
  });
}

/**
 * Start calibration of an MS.
 */
export function useCalibrateMS() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: CalibrationRequest) => {
      const response = await apiClient.post<CalibrationResponse>(
        "/calibrator-imaging/calibrate",
        request
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: calibratorImagingKeys.job(data.job_id),
      });
    },
  });
}

/**
 * Start imaging of a calibrated MS.
 */
export function useCreateImage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: ImagingRequest) => {
      const response = await apiClient.post<ImagingResponse>(
        "/calibrator-imaging/image",
        request
      );
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: calibratorImagingKeys.job(data.job_id),
      });
    },
  });
}

/**
 * Poll job status.
 */
export function useCalibratorJob(jobId: string | null) {
  return useQuery({
    queryKey: calibratorImagingKeys.job(jobId ?? ""),
    queryFn: async () => {
      const response = await apiClient.get<JobInfo>(
        `/calibrator-imaging/job/${jobId}`
      );
      return response.data;
    },
    enabled: !!jobId,
    // Poll while job is pending or running
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "pending" || status === "running") {
        return 2000; // Poll every 2 seconds
      }
      return false; // Stop polling when complete/failed
    },
  });
}

/**
 * Fetch photometry results for an image.
 */
export function usePhotometry(
  imagePath: string | null,
  sourceName: string | null
) {
  return useQuery({
    queryKey: calibratorImagingKeys.photometry(imagePath ?? ""),
    queryFn: async () => {
      const response = await apiClient.get<PhotometryResult>(
        `/calibrator-imaging/photometry/${encodeURIComponent(imagePath!)}`,
        {
          params: { source_name: sourceName },
        }
      );
      return response.data;
    },
    enabled: !!imagePath,
  });
}

/**
 * Check health status of the calibrator imaging API.
 */
export function useCalibratorImagingHealth() {
  return useQuery({
    queryKey: calibratorImagingKeys.health(),
    queryFn: async () => {
      const response = await apiClient.get<HealthStatus>(
        "/calibrator-imaging/health"
      );
      return response.data;
    },
    staleTime: 30000, // Cache for 30 seconds
  });
}
