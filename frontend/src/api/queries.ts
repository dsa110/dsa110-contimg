/**
 * React Query hooks for API data fetching.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { apiClient } from "./client";
import { createWebSocketClient, WebSocketClient } from "./websocket";
import type {
  PipelineStatus,
  SystemMetrics,
  ESECandidatesResponse,
  MosaicQueryRequest,
  MosaicQueryResponse,
  SourceSearchRequest,
  SourceSearchResponse,
  AlertHistory,
  MSList,
  MSListFilters,
  MSMetadata,
  CalTableCompatibility,
  JobList,
  Job,
  JobCreateRequest,
  UVH5FileList,
  ConversionJobCreateRequest,
  CalTableList,
  MSCalibratorMatchList,
  ExistingCalTables,
  WorkflowJobCreateRequest,
  CalibrationQA,
  ImageQA,
  CatalogValidationResults,
  CatalogOverlayData,
  QAMetrics,
  BandpassPlotsList,
  BatchJob,
  BatchJobList,
  BatchJobCreateRequest,
  ImageList,
  ImageFilters,
  DataInstance,
  DataInstanceDetail,
  AutoPublishStatus,
  DataLineage,
  PointingHistoryList,
  Mosaic,
  DirectoryListing,
  FITSInfo,
  CasaTableInfo,
  NotebookGenerateRequest,
  NotebookGenerateResponse,
  QARunRequest,
  QAResultSummary,
  DLQItem,
  DLQStats,
  DLQRetryRequest,
  DLQResolveRequest,
  CircuitBreakerState,
  CircuitBreakerList,
  HealthSummary,
  PipelineExecutionResponse,
  StageStatusResponse,
  StageMetricsResponse,
  DependencyGraphResponse,
  PipelineMetricsSummary,
  EventStreamItem,
  EventStatistics,
  EventTypesResponse,
  CacheStatistics,
  CacheKeysResponse,
  CacheKeyDetail,
  CachePerformance,
} from "./types";

/**
 * Hook to use WebSocket for real-time updates with polling fallback
 */
function useRealtimeQuery<T>(
  queryKey: string[],
  queryFn: () => Promise<T>,
  wsClient: WebSocketClient | null,
  pollInterval: number = 10000
): UseQueryResult<T> {
  const queryClient = useQueryClient();
  const wsSubscribed = useRef(false);

  // Set up WebSocket subscription
  useEffect(() => {
    if (!wsClient || !wsClient.connected || wsSubscribed.current) {
      return;
    }

    wsSubscribed.current = true;
    const unsubscribe = wsClient.on("status_update", (data: any) => {
      if (data.data?.pipeline_status) {
        queryClient.setQueryData(["pipeline", "status"], data.data.pipeline_status);
      }
      if (data.data?.metrics) {
        queryClient.setQueryData(["system", "metrics"], data.data.metrics);
      }
      if (data.data?.ese_candidates) {
        queryClient.setQueryData(["ese", "candidates"], data.data.ese_candidates);
      }
    });

    return () => {
      unsubscribe();
      wsSubscribed.current = false;
    };
  }, [wsClient, queryClient]);

  // Use polling as fallback or if WebSocket unavailable
  const shouldPoll = !wsClient || !wsClient.connected;

  return useQuery({
    queryKey,
    queryFn,
    refetchInterval: shouldPoll ? pollInterval : false,
  });
}

// Create WebSocket client instance (singleton)
let wsClientInstance: WebSocketClient | null = null;

function getWebSocketClient(): WebSocketClient | null {
  if (typeof window === "undefined") {
    return null;
  }

  if (!wsClientInstance) {
    // Use VITE_API_URL if set, otherwise use relative /api for Vite proxy
    const apiUrl = import.meta.env.VITE_API_URL || "/api";
    // For WebSocket, convert http:// to ws:// or use relative path
    const wsUrl = apiUrl.startsWith("http")
      ? `${apiUrl.replace(/^http/, "ws")}/ws/status`
      : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}${apiUrl}/ws/status`;

    try {
      wsClientInstance = createWebSocketClient({
        url: wsUrl,
        reconnectInterval: 3000,
        maxReconnectAttempts: 10,
        useSSE: false, // Try WebSocket first, fallback handled in client
      });
      wsClientInstance.connect();
    } catch (error) {
      console.warn("Failed to create WebSocket client, using polling:", error);
      return null;
    }
  }

  return wsClientInstance;
}

export function usePipelineStatus(): UseQueryResult<PipelineStatus> {
  const wsClient = getWebSocketClient();

  return useRealtimeQuery(
    ["pipeline", "status"],
    async () => {
      const response = await apiClient.get<PipelineStatus>("/status");
      return response.data;
    },
    wsClient,
    10000 // Fallback polling interval
  );
}

export function useSystemMetrics(): UseQueryResult<SystemMetrics> {
  const wsClient = getWebSocketClient();

  return useRealtimeQuery(
    ["system", "metrics"],
    async () => {
      const response = await apiClient.get<SystemMetrics>("/metrics/system");
      return response.data;
    },
    wsClient,
    10000
  );
}

export function useESECandidates(): UseQueryResult<ESECandidatesResponse> {
  const wsClient = getWebSocketClient();

  return useRealtimeQuery(
    ["ese", "candidates"],
    async () => {
      const response = await apiClient.get<ESECandidatesResponse>("/ese/candidates");
      return response.data;
    },
    wsClient,
    10000
  );
}

export function useMosaicQuery(
  request: MosaicQueryRequest | null
): UseQueryResult<MosaicQueryResponse> {
  return useQuery({
    queryKey: ["mosaics", request],
    queryFn: async () => {
      if (!request) {
        return { mosaics: [], total: 0 };
      }
      const response = await apiClient.post<MosaicQueryResponse>("/mosaics/query", request);
      return response.data;
    },
    enabled: !!request,
  });
}

export function useMosaic(mosaicId: number | null): UseQueryResult<Mosaic> {
  return useQuery({
    queryKey: ["mosaics", mosaicId],
    queryFn: async () => {
      if (!mosaicId) throw new Error("Mosaic ID required");
      const response = await apiClient.get<Mosaic>(`/mosaics/${mosaicId}`);
      return response.data;
    },
    enabled: !!mosaicId,
  });
}

export function useSourceSearch(
  request: SourceSearchRequest | null
): UseQueryResult<SourceSearchResponse> {
  return useQuery({
    queryKey: ["sources", request],
    queryFn: async () => {
      if (!request) {
        return { sources: [], total: 0 };
      }
      const response = await apiClient.post<SourceSearchResponse>("/sources/search", request);
      return response.data;
    },
    enabled: !!request,
  });
}

export function useAlertHistory(limit = 50): UseQueryResult<AlertHistory[]> {
  return useQuery({
    queryKey: ["alerts", "history", limit],
    queryFn: async () => {
      const response = await apiClient.get<AlertHistory[]>(`/alerts/history?limit=${limit}`);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30s
  });
}

export function useCreateMosaic() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: MosaicQueryRequest) => {
      const response = await apiClient.post("/mosaics/create", request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mosaics"] });
    },
  });
}

// Control panel queries

/**
 * Hook to fetch MS list with optional filtering, sorting, and pagination.
 *
 * @param filters - Optional filters for search, status, quality, date range, etc.
 * @returns MS list with pagination metadata
 *
 * @example
 * // Get all MS
 * const { data } = useMSList();
 *
 * @example
 * // Search for MS with calibrator
 * const { data } = useMSList({ search: '3C286', has_calibrator: true });
 *
 * @example
 * // Get calibrated MS, sorted by time
 * const { data } = useMSList({ is_calibrated: true, sort_by: 'time_desc' });
 */
export function useMSList(filters?: MSListFilters): UseQueryResult<MSList> {
  return useQuery({
    queryKey: ["ms", "list", filters],
    queryFn: async () => {
      const params = new URLSearchParams();

      if (filters?.search) params.append("search", filters.search);
      if (filters?.has_calibrator !== undefined)
        params.append("has_calibrator", String(filters.has_calibrator));
      if (filters?.is_calibrated !== undefined)
        params.append("is_calibrated", String(filters.is_calibrated));
      if (filters?.is_imaged !== undefined) params.append("is_imaged", String(filters.is_imaged));
      if (filters?.calibrator_quality)
        params.append("calibrator_quality", filters.calibrator_quality);
      if (filters?.start_date) params.append("start_date", filters.start_date);
      if (filters?.end_date) params.append("end_date", filters.end_date);
      if (filters?.sort_by) params.append("sort_by", filters.sort_by);
      if (filters?.limit !== undefined) params.append("limit", String(filters.limit));
      if (filters?.offset !== undefined) params.append("offset", String(filters.offset));
      if (filters?.scan) params.append("scan", String(filters.scan));
      if (filters?.scan_dir) params.append("scan_dir", filters.scan_dir);

      const url = `/ms${params.toString() ? `?${params.toString()}` : ""}`;
      const response = await apiClient.get<MSList>(url);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30s
  });
}

export function useDiscoverMS() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params?: { scan_dir?: string; recursive?: boolean }) => {
      const body: Record<string, unknown> = {};
      if (params?.scan_dir) body.scan_dir = params.scan_dir;
      if (params?.recursive !== undefined) body.recursive = params.recursive;
      const response = await apiClient.post<{
        success: boolean;
        count: number;
        scan_dir: string;
        discovered: string[];
      }>("/ms/discover", body);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ms"] });
    },
  });
}

export function useJobs(limit = 50, status?: string): UseQueryResult<JobList> {
  return useQuery({
    queryKey: ["jobs", limit, status],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append("limit", limit.toString());
      if (status) params.append("status", status);
      const response = await apiClient.get<JobList>(`/jobs?${params}`);
      return response.data;
    },
    refetchInterval: 5000, // Poll every 5 seconds
  });
}

export function useJob(jobId: number | null): UseQueryResult<Job> {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: async () => {
      if (!jobId) throw new Error("Job ID required");
      const response = await apiClient.get<Job>(`/jobs/id/${jobId}`);
      return response.data;
    },
    enabled: !!jobId,
    refetchInterval: 2000, // Poll every 2 seconds
  });
}

export function useCreateCalibrateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: JobCreateRequest) => {
      const response = await apiClient.post<Job>("/jobs/calibrate", request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useCreateApplyJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: JobCreateRequest) => {
      const response = await apiClient.post<Job>("/jobs/apply", request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useCreateImageJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: JobCreateRequest) => {
      const response = await apiClient.post<Job>("/jobs/image", request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useUVH5Files(inputDir?: string): UseQueryResult<UVH5FileList> {
  return useQuery({
    queryKey: ["uvh5", "list", inputDir],
    queryFn: async () => {
      const params = inputDir ? `?input_dir=${encodeURIComponent(inputDir)}` : "";
      const response = await apiClient.get<UVH5FileList>(`/uvh5${params}`);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30s
  });
}

export function useCreateConvertJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: ConversionJobCreateRequest) => {
      const response = await apiClient.post<Job>("/jobs/convert", request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["ms"] });
    },
  });
}

// Cal table queries
export function useCalTables(calDir?: string): UseQueryResult<CalTableList> {
  return useQuery({
    queryKey: ["caltables", "list", calDir],
    queryFn: async () => {
      const params = calDir ? `?cal_dir=${encodeURIComponent(calDir)}` : "";
      const response = await apiClient.get<CalTableList>(`/caltables${params}`);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30s
  });
}

// MS metadata query
export function useMSMetadata(msPath: string | null): UseQueryResult<MSMetadata> {
  return useQuery({
    queryKey: ["ms", "metadata", msPath],
    queryFn: async () => {
      if (!msPath) throw new Error("MS path required");
      // Remove leading slash and encode
      const encodedPath = msPath.startsWith("/") ? msPath.slice(1) : msPath;
      const response = await apiClient.get<MSMetadata>(`/ms/${encodedPath}/metadata`);
      return response.data;
    },
    enabled: !!msPath,
    staleTime: 60000, // Cache for 1 minute
  });
}

// Calibrator match hook
export function useCalibratorMatches(
  msPath: string | null,
  catalog: string = "vla",
  radiusDeg: number = 1.5
): UseQueryResult<MSCalibratorMatchList> {
  return useQuery({
    queryKey: ["ms", "calibrator-matches", msPath, catalog, radiusDeg],
    queryFn: async () => {
      if (!msPath) throw new Error("MS path required");
      // Remove leading slash and encode
      const encodedPath = msPath.startsWith("/") ? msPath.slice(1) : msPath;
      const response = await apiClient.get<MSCalibratorMatchList>(
        `/ms/${encodedPath}/calibrator-matches`,
        { params: { catalog, radius_deg: radiusDeg } }
      );
      return response.data;
    },
    enabled: !!msPath,
    staleTime: 300000, // Cache for 5 minutes (calibrator matches don't change often)
  });
}

// Existing cal tables hook
export function useExistingCalTables(msPath: string | null): UseQueryResult<ExistingCalTables> {
  return useQuery({
    queryKey: ["ms", "existing-caltables", msPath],
    queryFn: async () => {
      if (!msPath) throw new Error("MS path required");
      // Remove leading slash and encode
      const encodedPath = msPath.startsWith("/") ? msPath.slice(1) : msPath;
      const response = await apiClient.get<ExistingCalTables>(
        `/ms/${encodedPath}/existing-caltables`
      );
      return response.data;
    },
    enabled: !!msPath,
    staleTime: 60000, // Cache for 1 minute (cal tables change when calibration runs)
  });
}

export function useValidateCalTable() {
  return useMutation({
    mutationFn: async ({ msPath, caltablePath }: { msPath: string; caltablePath: string }) => {
      const encodedMsPath = msPath.startsWith("/") ? msPath.slice(1) : msPath;
      const response = await apiClient.post<CalTableCompatibility>(
        `/ms/${encodedMsPath}/validate-caltable`,
        { caltable_path: caltablePath }
      );
      return response.data;
    },
  });
}

/**
 * Hook to fetch calibration QA metrics for an MS.
 *
 * @param msPath - Path to the MS file
 * @returns Calibration QA metrics including K/BP/G table statistics
 *
 * @example
 * const { data: calQA } = useCalibrationQA('/path/to/ms');
 * if (calQA) {
 *   logger.info('Overall quality:', calQA.overall_quality);
 *   logger.info('Flag fraction:', calQA.flags_total);
 * }
 */
export function useCalibrationQA(msPath: string | null): UseQueryResult<CalibrationQA> {
  return useQuery({
    queryKey: ["qa", "calibration", msPath],
    queryFn: async () => {
      if (!msPath) throw new Error("MS path required");
      // Remove leading slash and encode
      const encodedPath = msPath.startsWith("/") ? msPath.slice(1) : msPath;
      const response = await apiClient.get<CalibrationQA>(`/qa/calibration/${encodedPath}`);
      return response.data;
    },
    enabled: !!msPath,
    staleTime: 300000, // Cache for 5 minutes (QA doesn't change unless recalibrated)
    retry: false, // Don't retry on 404 (no QA yet)
  });
}

/**
 * Fetch list of available bandpass plots for an MS.
 *
 * @example
 * const { data: plots } = useBandpassPlots('/path/to/ms');
 */
export function useBandpassPlots(msPath: string | null): UseQueryResult<BandpassPlotsList> {
  return useQuery({
    queryKey: ["qa", "bandpass-plots", msPath],
    queryFn: async () => {
      if (!msPath) throw new Error("MS path required");
      // Remove leading slash and URL-encode the path (handles colons and other special chars)
      const pathWithoutLeadingSlash = msPath.startsWith("/") ? msPath.slice(1) : msPath;
      const encodedPath = encodeURIComponent(pathWithoutLeadingSlash);
      const response = await apiClient.get<BandpassPlotsList>(
        `/qa/calibration/${encodedPath}/bandpass-plots`
      );
      return response.data;
    },
    enabled: !!msPath,
    staleTime: 300000, // Cache for 5 minutes
    retry: false, // Don't retry on 404 (no plots yet)
  });
}

/**
 * Hook to fetch image QA metrics for an MS.
 *
 * @param msPath - Path to the MS file
 * @returns Image QA metrics including RMS, dynamic range, beam parameters
 *
 * @example
 * const { data: imgQA } = useImageQA('/path/to/ms');
 * if (imgQA) {
 *   logger.info('RMS noise:', imgQA.rms_noise, 'Jy/beam');
 *   logger.info('Dynamic range:', imgQA.dynamic_range);
 * }
 */
export function useImageQA(msPath: string | null): UseQueryResult<ImageQA> {
  return useQuery({
    queryKey: ["qa", "image", msPath],
    queryFn: async () => {
      if (!msPath) throw new Error("MS path required");
      // Remove leading slash and encode
      const encodedPath = msPath.startsWith("/") ? msPath.slice(1) : msPath;
      const response = await apiClient.get<ImageQA>(`/qa/image/${encodedPath}`);
      return response.data;
    },
    enabled: !!msPath,
    staleTime: 300000, // Cache for 5 minutes
    retry: false, // Don't retry on 404 (no QA yet)
  });
}

/**
 * Hook to fetch combined QA metrics (calibration + image) for an MS.
 *
 * @param msPath - Path to the MS file
 * @returns Combined QA metrics with both calibration and image data
 *
 * @example
 * const { data: qa } = useQAMetrics('/path/to/ms');
 * if (qa?.calibration_qa) {
 *   logger.info('Cal quality:', qa.calibration_qa.overall_quality);
 * }
 * if (qa?.image_qa) {
 *   logger.info('Image quality:', qa.image_qa.overall_quality);
 * }
 */
export function useQAMetrics(msPath: string | null): UseQueryResult<QAMetrics> {
  return useQuery({
    queryKey: ["qa", "combined", msPath],
    queryFn: async () => {
      if (!msPath) throw new Error("MS path required");
      // Remove leading slash and encode
      const encodedPath = msPath.startsWith("/") ? msPath.slice(1) : msPath;
      const response = await apiClient.get<QAMetrics>(`/qa/${encodedPath}`);
      return response.data;
    },
    enabled: !!msPath,
    staleTime: 300000, // Cache for 5 minutes
    retry: false, // Don't retry on 404 (no QA yet)
  });
}

// Workflow job mutation
export function useCreateWorkflowJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: WorkflowJobCreateRequest) => {
      const response = await apiClient.post<Job>("/jobs/workflow", request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["ms"] });
    },
  });
}

/**
 * Batch job hooks for processing multiple MS files.
 */

/**
 * Hook to fetch list of batch jobs.
 *
 * @param limit - Maximum number of batch jobs to return
 * @param status - Optional status filter (pending, running, done, failed, cancelled)
 * @returns List of batch jobs
 */
export function useBatchJobs(limit = 50, status?: string): UseQueryResult<BatchJobList> {
  return useQuery({
    queryKey: ["batch", "jobs", limit, status],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (status) params.append("status", status);
      params.append("limit", String(limit));

      const url = `/batch${params.toString() ? `?${params.toString()}` : ""}`;
      const response = await apiClient.get<BatchJobList>(url);
      return response.data;
    },
    refetchInterval: 5000, // Poll every 5 seconds for running batches
  });
}

/**
 * Hook to fetch a single batch job by ID.
 *
 * @param batchId - Batch job ID
 * @returns Batch job details with per-item status
 */
export function useBatchJob(batchId: number | null): UseQueryResult<BatchJob> {
  return useQuery({
    queryKey: ["batch", "job", batchId],
    queryFn: async () => {
      if (!batchId) throw new Error("Batch ID required");
      const response = await apiClient.get<BatchJob>(`/batch/${batchId}`);
      return response.data;
    },
    enabled: !!batchId,
    refetchInterval: (query) => {
      // Poll frequently if batch is still running
      const data = query.state.data;
      if (data?.status === "running" || data?.status === "pending") {
        return 2000; // Poll every 2 seconds
      }
      return false; // Don't poll completed batches
    },
  });
}

/**
 * Hook to create a batch calibration job.
 *
 * @returns Mutation hook for creating batch calibration jobs
 */
export function useCreateBatchCalibrateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: BatchJobCreateRequest) => {
      const response = await apiClient.post<BatchJob>("/batch/calibrate", request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["batch"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

/**
 * Hook to create a batch apply job.
 *
 * @returns Mutation hook for creating batch apply jobs
 */
export function useCreateBatchApplyJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: BatchJobCreateRequest) => {
      const response = await apiClient.post<BatchJob>("/batch/apply", request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["batch"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

/**
 * Hook to create a batch imaging job.
 *
 * @returns Mutation hook for creating batch imaging jobs
 */
export function useCreateBatchImageJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: BatchJobCreateRequest) => {
      const response = await apiClient.post<BatchJob>("/batch/image", request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["batch"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

/**
 * Hook to cancel a batch job.
 *
 * @returns Mutation hook for cancelling batch jobs
 */
export function useCancelBatchJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (batchId: number) => {
      const response = await apiClient.post(`/batch/${batchId}/cancel`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["batch"] });
    },
  });
}

/**
 * Query hook for fetching images for SkyView.
 */
export function useImages(filters?: ImageFilters): UseQueryResult<ImageList> {
  return useQuery({
    queryKey: ["images", filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.limit) params.append("limit", filters.limit.toString());
      if (filters?.offset) params.append("offset", filters.offset.toString());
      if (filters?.ms_path) params.append("ms_path", filters.ms_path);
      if (filters?.image_type) params.append("image_type", filters.image_type);
      if (filters?.pbcor !== undefined) params.append("pbcor", filters.pbcor.toString());
      // Advanced filters
      if (filters?.start_date) params.append("start_date", filters.start_date);
      if (filters?.end_date) params.append("end_date", filters.end_date);
      if (filters?.dec_min !== undefined) params.append("dec_min", filters.dec_min.toString());
      if (filters?.dec_max !== undefined) params.append("dec_max", filters.dec_max.toString());
      if (filters?.noise_max !== undefined)
        params.append("noise_max", filters.noise_max.toString());
      if (filters?.has_calibrator !== undefined)
        params.append("has_calibrator", filters.has_calibrator.toString());

      const response = await apiClient.get<ImageList>(`/images?${params.toString()}`);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

/**
 * Streaming Service Hooks
 */
export interface StreamingStatus {
  running: boolean;
  pid?: number;
  started_at?: string;
  uptime_seconds?: number;
  cpu_percent?: number;
  memory_mb?: number;
  last_heartbeat?: string;
  config?: Record<string, unknown>;
  error?: string;
}

export interface StreamingHealth {
  healthy: boolean;
  running: boolean;
  uptime_seconds?: number;
  cpu_percent?: number;
  memory_mb?: number;
  error?: string;
}

export interface StreamingConfig {
  input_dir: string;
  output_dir: string;
  queue_db?: string;
  registry_db?: string;
  scratch_dir?: string;
  expected_subbands: number;
  chunk_duration: number;
  log_level: string;
  use_subprocess: boolean;
  monitoring: boolean;
  monitor_interval: number;
  poll_interval: number;
  worker_poll_interval: number;
  max_workers: number;
  stage_to_tmpfs: boolean;
  tmpfs_path: string;
}

export interface StreamingMetrics {
  service_running: boolean;
  uptime_seconds?: number;
  cpu_percent?: number;
  memory_mb?: number;
  queue_stats?: Record<string, number>;
  processing_rate_per_hour?: number;
  queue_error?: string;
}

export function useStreamingStatus(): UseQueryResult<StreamingStatus> {
  return useQuery({
    queryKey: ["streaming", "status"],
    queryFn: async () => {
      const response = await apiClient.get<StreamingStatus>("/streaming/status");
      return response.data;
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  });
}

export function useStreamingHealth(): UseQueryResult<StreamingHealth> {
  return useQuery({
    queryKey: ["streaming", "health"],
    queryFn: async () => {
      const response = await apiClient.get<StreamingHealth>("/streaming/health");
      return response.data;
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

export function useStreamingConfig(): UseQueryResult<StreamingConfig> {
  return useQuery({
    queryKey: ["streaming", "config"],
    queryFn: async () => {
      const response = await apiClient.get<StreamingConfig>("/streaming/config");
      return response.data;
    },
  });
}

export function useStreamingMetrics(): UseQueryResult<StreamingMetrics> {
  return useQuery({
    queryKey: ["streaming", "metrics"],
    queryFn: async () => {
      const response = await apiClient.get<StreamingMetrics>("/streaming/metrics");
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

export interface PointingMonitorMetrics {
  files_processed: number;
  files_succeeded: number;
  files_failed: number;
  success_rate_percent: number;
  uptime_seconds: number;
  last_processed_time?: number;
  last_success_time?: number;
  last_error_time?: number;
  last_error_message?: string;
  recent_error_count: number;
}

export interface PointingMonitorStatus {
  running: boolean;
  healthy: boolean;
  stale?: boolean;
  issues: string[];
  watch_dir: string;
  products_db: string;
  metrics: PointingMonitorMetrics;
  timestamp: number;
  timestamp_iso: string;
  status_file_age_seconds?: number;
  error?: string;
  status_file?: string;
}

export function usePointingMonitorStatus(): UseQueryResult<PointingMonitorStatus> {
  return useQuery({
    queryKey: ["pointing-monitor", "status"],
    queryFn: async () => {
      const response = await apiClient.get<PointingMonitorStatus>("/pointing-monitor/status");
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

export function usePointingHistory(
  startMjd: number,
  endMjd: number
): UseQueryResult<PointingHistoryList> {
  return useQuery({
    queryKey: ["pointing-history", startMjd, endMjd],
    queryFn: async () => {
      const response = await apiClient.get<PointingHistoryList>(
        `/pointing_history?start_mjd=${startMjd}&end_mjd=${endMjd}`
      );
      return response.data;
    },
    refetchInterval: 60000, // Refresh every minute
    staleTime: 30000, // Consider stale after 30 seconds
  });
}

export function useStartStreaming() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (config?: StreamingConfig) => {
      const response = await apiClient.post("/streaming/start", config || {});
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["streaming"] });
    },
  });
}

export function useStopStreaming() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post("/streaming/stop");
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["streaming"] });
    },
  });
}

export function useRestartStreaming() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (config?: StreamingConfig) => {
      const response = await apiClient.post("/streaming/restart", config || {});
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["streaming"] });
    },
  });
}

export function useUpdateStreamingConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (config: StreamingConfig) => {
      const response = await apiClient.post("/streaming/config", config);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["streaming"] });
    },
  });
}

// Data Registry Queries
export function useDataInstances(
  dataType?: string,
  status?: "staging" | "published"
): UseQueryResult<DataInstance[]> {
  return useQuery({
    queryKey: ["data", "instances", dataType, status],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (dataType) params.append("data_type", dataType);
      if (status) params.append("status", status);
      const response = await apiClient.get<DataInstance[]>(`/data?${params.toString()}`);
      return response.data;
    },
  });
}

export function useDataInstance(dataId: string): UseQueryResult<DataInstanceDetail> {
  return useQuery({
    queryKey: ["data", "instance", dataId],
    queryFn: async () => {
      const encodedId = encodeURIComponent(dataId);
      const response = await apiClient.get<DataInstanceDetail>(`/data/${encodedId}`);
      return response.data;
    },
    enabled: !!dataId,
  });
}

export function useAutoPublishStatus(dataId: string): UseQueryResult<AutoPublishStatus> {
  return useQuery({
    queryKey: ["data", "auto-publish", dataId],
    queryFn: async () => {
      const encodedId = encodeURIComponent(dataId);
      const response = await apiClient.get<AutoPublishStatus>(
        `/data/${encodedId}/auto-publish/status`
      );
      return response.data;
    },
    enabled: !!dataId,
  });
}

export function useDataLineage(dataId: string): UseQueryResult<DataLineage> {
  return useQuery({
    queryKey: ["data", "lineage", dataId],
    queryFn: async () => {
      const encodedId = encodeURIComponent(dataId);
      const response = await apiClient.get<DataLineage>(`/data/${encodedId}/lineage`);
      return response.data;
    },
    enabled: !!dataId,
  });
}

// Catalog Validation Queries
export function useCatalogValidation(
  imageId: string | null,
  catalog: "nvss" | "vlass" = "nvss",
  validationType: "astrometry" | "flux_scale" | "source_counts" | "all" = "all"
): UseQueryResult<CatalogValidationResults> {
  return useQuery({
    queryKey: ["qa", "catalog-validation", imageId, catalog, validationType],
    queryFn: async () => {
      if (!imageId) throw new Error("Image ID required");
      const encodedId = encodeURIComponent(imageId);
      const response = await apiClient.get<CatalogValidationResults>(
        `/qa/images/${encodedId}/catalog-validation?catalog=${catalog}&validation_type=${validationType}`
      );
      return response.data;
    },
    enabled: !!imageId,
    staleTime: 300000, // Cache for 5 minutes
  });
}

export function useCatalogOverlay(
  imageId: string | null,
  catalog: "nvss" | "vlass" = "nvss",
  minFluxJy?: number
): UseQueryResult<CatalogOverlayData> {
  return useQuery({
    queryKey: ["qa", "catalog-overlay", imageId, catalog, minFluxJy],
    queryFn: async () => {
      if (!imageId) throw new Error("Image ID required");
      const encodedId = encodeURIComponent(imageId);
      const params = new URLSearchParams({ catalog });
      if (minFluxJy !== undefined) params.append("min_flux_jy", minFluxJy.toString());
      const response = await apiClient.get<CatalogOverlayData>(
        `/qa/images/${encodedId}/catalog-overlay?${params.toString()}`
      );
      return response.data;
    },
    enabled: !!imageId,
    staleTime: 300000, // Cache for 5 minutes
  });
}

export function useRunCatalogValidation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      imageId,
      catalog = "nvss",
      validationTypes = ["astrometry", "flux_scale", "source_counts"],
    }: {
      imageId: string;
      catalog?: "nvss" | "vlass";
      validationTypes?: string[];
    }) => {
      const encodedId = encodeURIComponent(imageId);
      const response = await apiClient.post<CatalogValidationResults>(
        `/qa/images/${encodedId}/catalog-validation/run`,
        { catalog, validation_types: validationTypes }
      );
      return response.data;
    },
    onSuccess: (_data, variables) => {
      // Invalidate validation queries to refetch
      queryClient.invalidateQueries({
        queryKey: ["qa", "catalog-validation", variables.imageId],
      });
    },
  });
}

/**
 * Query hook for catalog overlay using RA/Dec/radius (new endpoint)
 */
export interface CatalogOverlaySource {
  ra_deg: number;
  dec_deg: number;
  flux_mjy: number | null;
  source_id: string | null;
  catalog_type: string;
}

export interface CatalogOverlayResponse {
  sources: CatalogOverlaySource[];
  count: number;
  ra_center: number;
  dec_center: number;
  radius_deg: number;
}

export function useCatalogOverlayByCoords(
  ra: number | null,
  dec: number | null,
  radius: number = 1.5,
  catalog: string = "all"
): UseQueryResult<CatalogOverlayResponse> {
  return useQuery({
    queryKey: ["catalog-overlay", ra, dec, radius, catalog],
    queryFn: async () => {
      if (ra === null || dec === null) throw new Error("RA and Dec required");
      const params = new URLSearchParams({
        ra: ra.toString(),
        dec: dec.toString(),
        radius: radius.toString(),
        catalog,
      });
      const response = await apiClient.get<CatalogOverlayResponse>(
        `/catalog/overlay?${params.toString()}`
      );
      return response.data;
    },
    enabled: ra !== null && dec !== null,
    staleTime: 300000, // Cache for 5 minutes
  });
}

/**
 * Region management query hooks
 */
export interface Region {
  id: number;
  name: string;
  type: "circle" | "rectangle" | "polygon";
  coordinates: Record<string, any>;
  image_path: string;
  created_at: number;
  created_by?: string;
  updated_at?: number;
}

export interface RegionListResponse {
  regions: Region[];
  count: number;
}

export function useRegions(
  imagePath?: string | null,
  regionType?: string
): UseQueryResult<RegionListResponse> {
  return useQuery({
    queryKey: ["regions", imagePath, regionType],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (imagePath) params.append("image_path", imagePath);
      if (regionType) params.append("region_type", regionType);
      const response = await apiClient.get<RegionListResponse>(`/regions?${params.toString()}`);
      return response.data;
    },
    staleTime: 60000, // Cache for 1 minute
  });
}

export function useCreateRegion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (regionData: {
      name: string;
      type: string;
      coordinates: Record<string, any>;
      image_path: string;
      created_by?: string;
    }) => {
      const response = await apiClient.post<{ id: number; region: Region }>("/regions", regionData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["regions"] });
    },
  });
}

export function useUpdateRegion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      regionId,
      regionData,
    }: {
      regionId: number;
      regionData: Partial<Region>;
    }) => {
      const response = await apiClient.put<{ id: number; updated: boolean }>(
        `/regions/${regionId}`,
        regionData
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["regions"] });
    },
  });
}

export function useDeleteRegion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (regionId: number) => {
      const response = await apiClient.delete<{ id: number; deleted: boolean }>(
        `/regions/${regionId}`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["regions"] });
    },
  });
}

export function useRegionStatistics(regionId: number | null) {
  return useQuery({
    queryKey: ["region-statistics", regionId],
    queryFn: async () => {
      if (!regionId) throw new Error("Region ID required");
      const response = await apiClient.get<{
        region_id: number;
        statistics: Record<string, number>;
      }>(`/regions/${regionId}/statistics`);
      return response.data;
    },
    enabled: regionId !== null,
    staleTime: 60000, // Cache for 1 minute
  });
}

export interface ProfileExtractionRequest {
  imageId: number;
  profileType: "line" | "polyline" | "point";
  coordinates: number[][];
  coordinateSystem?: "wcs" | "pixel";
  width?: number;
  radius?: number;
  fitModel?: "gaussian" | "moffat";
}

export interface ProfileExtractionResponse {
  profile_type: string;
  distance: number[];
  flux: number[];
  error?: number[];
  coordinates: number[][];
  units: {
    distance: string;
    flux: string;
  };
  fit?: {
    model: string;
    parameters: Record<string, number>;
    statistics: {
      chi_squared: number;
      reduced_chi_squared: number;
      r_squared: number;
    };
    fitted_flux: number[];
    parameter_errors?: Record<string, number>;
  };
}

export function useProfileExtraction() {
  return useMutation({
    mutationFn: async (request: ProfileExtractionRequest) => {
      const params = new URLSearchParams({
        profile_type: request.profileType,
        coordinates: JSON.stringify(request.coordinates),
        coordinate_system: request.coordinateSystem || "wcs",
        width: (request.width || 1).toString(),
      });

      if (request.profileType === "point" && request.radius !== undefined) {
        params.append("radius", request.radius.toString());
      }

      if (request.fitModel) {
        params.append("fit_model", request.fitModel);
      }

      const response = await apiClient.get<ProfileExtractionResponse>(
        `/images/${request.imageId}/profile?${params.toString()}`
      );
      return response.data;
    },
  });
}

export interface ImageFittingRequest {
  imageId: number;
  model: "gaussian" | "moffat";
  regionId?: number;
  initialGuess?: Record<string, number>;
  fitBackground?: boolean;
}

export interface ImageFittingResponse {
  model: string;
  parameters: {
    amplitude: number;
    center: {
      x: number;
      y: number;
      ra?: number;
      dec?: number;
    };
    major_axis: number;
    minor_axis: number;
    pa: number;
    background: number;
    gamma?: number;
    alpha?: number;
  };
  statistics: {
    chi_squared: number;
    reduced_chi_squared: number;
    r_squared: number;
  };
  residuals: {
    mean: number;
    std: number;
    max: number;
  };
  center_wcs?: {
    ra: number;
    dec: number;
  };
}

export function useImageFitting() {
  return useMutation({
    mutationFn: async (request: ImageFittingRequest) => {
      const body: any = {
        model: request.model,
        fit_background: request.fitBackground !== false,
      };

      if (request.regionId !== undefined) {
        body.region_id = request.regionId;
      }

      if (request.initialGuess) {
        body.initial_guess = JSON.stringify(request.initialGuess);
      }

      const response = await apiClient.post<ImageFittingResponse>(
        `/images/${request.imageId}/fit`,
        body
      );
      return response.data;
    },
  });
}

// QA Visualization Queries
/**
 * Check if a path looks complete (not being actively typed).
 * Paths ending with certain characters suggest they're incomplete.
 */
function isPathComplete(path: string | null): boolean {
  if (!path || path.trim().length === 0) return false;

  const trimmed = path.trim();

  // Root path is always complete
  if (trimmed === "/") return true;

  // Remove trailing slash for analysis (but keep it for the path itself)
  const pathWithoutTrailingSlash = trimmed.replace(/\/+$/, "");
  if (pathWithoutTrailingSlash.length === 0) return true; // Just slashes

  // Paths ending with these characters suggest incomplete typing
  const incompleteEndings = ["-", "_"];
  // Check if the last segment ends with an incomplete character
  const segments = pathWithoutTrailingSlash.split("/").filter(Boolean);
  if (segments.length === 0) return true; // Root or just slashes

  const lastSegment = segments[segments.length - 1];
  // If last segment ends with incomplete characters, path is incomplete
  return !incompleteEndings.some((ending) => lastSegment.endsWith(ending));
}

export function useDirectoryListing(
  path: string | null,
  recursive = false,
  includePattern?: string,
  excludePattern?: string,
  showHidden = false
): UseQueryResult<DirectoryListing> {
  const pathComplete = isPathComplete(path);

  return useQuery({
    queryKey: [
      "visualization",
      "directory",
      path,
      recursive,
      includePattern,
      excludePattern,
      showHidden,
    ],
    queryFn: async () => {
      if (!path) throw new Error("Path required");
      const params = new URLSearchParams({
        path,
        recursive: recursive.toString(),
        show_hidden: showHidden.toString(),
      });
      if (includePattern) params.append("include_pattern", includePattern);
      if (excludePattern) params.append("exclude_pattern", excludePattern);
      const response = await apiClient.get<DirectoryListing>(
        `/visualization/browse?${params.toString()}`
      );
      return response.data;
    },
    enabled: !!path && pathComplete,
    // Don't show errors for incomplete paths
    retry: pathComplete,
  });
}

export function useDirectoryThumbnails(
  path: string | null,
  recursive = false,
  includePattern?: string,
  excludePattern?: string,
  ncol?: number,
  mincol = 0,
  maxcol = 8,
  titles = true,
  width?: number
): UseQueryResult<string> {
  const pathComplete = isPathComplete(path);

  return useQuery({
    queryKey: [
      "visualization",
      "directory",
      "thumbnails",
      path,
      recursive,
      includePattern,
      excludePattern,
      ncol,
      mincol,
      maxcol,
      titles,
      width,
    ],
    queryFn: async () => {
      if (!path) throw new Error("Path required");
      const params = new URLSearchParams({
        path,
        recursive: recursive.toString(),
        mincol: mincol.toString(),
        maxcol: maxcol.toString(),
        titles: titles.toString(),
      });
      if (includePattern) params.append("include_pattern", includePattern);
      if (excludePattern) params.append("exclude_pattern", excludePattern);
      if (ncol !== undefined) params.append("ncol", ncol.toString());
      if (width !== undefined) params.append("width", width.toString());
      const response = await apiClient.get<string>(
        `/visualization/directory/thumbnails?${params.toString()}`,
        {
          responseType: "text",
        }
      );
      return response.data;
    },
    enabled: !!path && pathComplete,
    retry: pathComplete,
  });
}

export function useFITSInfo(path: string | null): UseQueryResult<FITSInfo> {
  return useQuery({
    queryKey: ["visualization", "fits", "info", path],
    queryFn: async () => {
      if (!path) throw new Error("Path required");
      const response = await apiClient.get<FITSInfo>(
        `/visualization/fits/info?path=${encodeURIComponent(path)}`
      );
      return response.data;
    },
    enabled: !!path,
  });
}

export function useCasaTableInfo(path: string | null): UseQueryResult<CasaTableInfo> {
  return useQuery({
    queryKey: ["visualization", "casatable", "info", path],
    queryFn: async () => {
      if (!path) throw new Error("Path required");
      const response = await apiClient.get<CasaTableInfo>(
        `/visualization/casatable/info?path=${encodeURIComponent(path)}`
      );
      return response.data;
    },
    enabled: !!path,
  });
}

export function useGenerateNotebook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: NotebookGenerateRequest) => {
      const response = await apiClient.post<NotebookGenerateResponse>(
        "/visualization/notebook/generate",
        request
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["visualization", "notebook"] });
    },
  });
}

export function useRunQA() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: QARunRequest) => {
      const response = await apiClient.post<QAResultSummary>("/visualization/notebook/qa", request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["visualization", "qa"] });
    },
  });
}

// Source detail hooks
export function useSourceDetail(sourceId: string | null): UseQueryResult<any> {
  return useQuery({
    queryKey: ["source", sourceId],
    queryFn: async () => {
      const response = await apiClient.get(`/sources/${sourceId}`);
      return response.data;
    },
    enabled: !!sourceId,
  });
}

export function useSourceDetections(
  sourceId: string | null,
  page: number = 1,
  pageSize: number = 25
): UseQueryResult<any> {
  return useQuery({
    queryKey: ["source", sourceId, "detections", page, pageSize],
    queryFn: async () => {
      const response = await apiClient.get(`/sources/${sourceId}/detections`, {
        params: { page, page_size: pageSize },
      });
      return response.data;
    },
    enabled: !!sourceId,
  });
}

// Image detail hooks
export function useImageDetail(imageId: number | null): UseQueryResult<any> {
  return useQuery({
    queryKey: ["image", imageId],
    queryFn: async () => {
      const response = await apiClient.get(`/images/${imageId}`);
      return response.data;
    },
    enabled: !!imageId,
  });
}

export function useImageMeasurements(
  imageId: number | null,
  page: number = 1,
  pageSize: number = 25
): UseQueryResult<any> {
  return useQuery({
    queryKey: ["image", imageId, "measurements", page, pageSize],
    queryFn: async () => {
      const response = await apiClient.get(`/images/${imageId}/measurements`, {
        params: { page, page_size: pageSize },
      });
      return response.data;
    },
    enabled: !!imageId,
  });
}

// ============================================================================
// Operations API Queries (DLQ, Circuit Breakers, Health)
// ============================================================================

export function useDLQItems(
  component?: string,
  status?: string,
  limit: number = 100,
  offset: number = 0
): UseQueryResult<DLQItem[]> {
  return useQuery({
    queryKey: ["dlq", "items", component, status, limit, offset],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (component) params.append("component", component);
      if (status) params.append("status", status);
      params.append("limit", limit.toString());
      params.append("offset", offset.toString());
      const response = await apiClient.get<DLQItem[]>(`/operations/dlq/items?${params}`);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

export function useDLQStats(): UseQueryResult<DLQStats> {
  return useQuery({
    queryKey: ["dlq", "stats"],
    queryFn: async () => {
      const response = await apiClient.get<DLQStats>("/operations/dlq/stats");
      return response.data;
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

export function useDLQItem(itemId: number): UseQueryResult<DLQItem> {
  return useQuery({
    queryKey: ["dlq", "item", itemId],
    queryFn: async () => {
      const response = await apiClient.get<DLQItem>(`/operations/dlq/items/${itemId}`);
      return response.data;
    },
  });
}

export function useRetryDLQItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ itemId, note }: { itemId: number; note?: string }) => {
      const response = await apiClient.post(`/operations/dlq/items/${itemId}/retry`, { note });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dlq"] });
    },
  });
}

export function useResolveDLQItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ itemId, note }: { itemId: number; note?: string }) => {
      const response = await apiClient.post(`/operations/dlq/items/${itemId}/resolve`, { note });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dlq"] });
    },
  });
}

export function useFailDLQItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ itemId, note }: { itemId: number; note?: string }) => {
      const response = await apiClient.post(`/operations/dlq/items/${itemId}/fail`, { note });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dlq"] });
    },
  });
}

export function useCircuitBreakers(): UseQueryResult<CircuitBreakerList> {
  return useQuery({
    queryKey: ["circuit-breakers"],
    queryFn: async () => {
      const response = await apiClient.get<CircuitBreakerList>("/operations/circuit-breakers");
      return response.data;
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  });
}

export function useResetCircuitBreaker() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const response = await apiClient.post(`/operations/circuit-breakers/${name}/reset`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["circuit-breakers"] });
    },
  });
}

export function useHealthSummary(): UseQueryResult<HealthSummary> {
  return useQuery({
    queryKey: ["health", "summary"],
    queryFn: async () => {
      const response = await apiClient.get<HealthSummary>("/health/summary");
      return response.data;
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

// Pipeline Execution Hooks
export function usePipelineExecutions(
  status?: string,
  jobType?: string,
  limit: number = 100,
  offset: number = 0
): UseQueryResult<PipelineExecutionResponse[]> {
  return useQuery({
    queryKey: ["pipeline", "executions", status, jobType, limit, offset],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (status) params.append("status", status);
      if (jobType) params.append("job_type", jobType);
      params.append("limit", limit.toString());
      params.append("offset", offset.toString());
      const response = await apiClient.get<PipelineExecutionResponse[]>(
        `/pipeline/executions?${params.toString()}`
      );
      return response.data;
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  });
}

export function useActivePipelineExecutions(): UseQueryResult<PipelineExecutionResponse[]> {
  return useQuery({
    queryKey: ["pipeline", "executions", "active"],
    queryFn: async () => {
      const response = await apiClient.get<PipelineExecutionResponse[]>(
        "/pipeline/executions/active"
      );
      return response.data;
    },
    refetchInterval: 3000, // Refresh every 3 seconds for active executions
  });
}

export function usePipelineExecution(
  executionId: number
): UseQueryResult<PipelineExecutionResponse> {
  return useQuery({
    queryKey: ["pipeline", "executions", executionId],
    queryFn: async () => {
      const response = await apiClient.get<PipelineExecutionResponse>(
        `/pipeline/executions/${executionId}`
      );
      return response.data;
    },
    refetchInterval: 5000, // Refresh every 5 seconds
    enabled: executionId > 0,
  });
}

export function useExecutionStages(executionId: number): UseQueryResult<StageStatusResponse[]> {
  return useQuery({
    queryKey: ["pipeline", "executions", executionId, "stages"],
    queryFn: async () => {
      const response = await apiClient.get<StageStatusResponse[]>(
        `/pipeline/executions/${executionId}/stages`
      );
      return response.data;
    },
    refetchInterval: 5000,
    enabled: executionId > 0,
  });
}

// Stage Metrics Hooks
export function useStageMetrics(
  stageName?: string,
  limit: number = 100
): UseQueryResult<StageMetricsResponse[]> {
  return useQuery({
    queryKey: ["pipeline", "stages", "metrics", stageName, limit],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (stageName) params.append("stage_name", stageName);
      params.append("limit", limit.toString());
      const response = await apiClient.get<StageMetricsResponse[]>(
        `/pipeline/stages/metrics?${params.toString()}`
      );
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

export function useStageMetricsByName(stageName: string): UseQueryResult<StageMetricsResponse> {
  return useQuery({
    queryKey: ["pipeline", "stages", "metrics", stageName],
    queryFn: async () => {
      const response = await apiClient.get<StageMetricsResponse>(
        `/pipeline/stages/${stageName}/metrics`
      );
      return response.data;
    },
    refetchInterval: 30000,
    enabled: !!stageName,
  });
}

// Dependency Graph Hook
export function useDependencyGraph(): UseQueryResult<DependencyGraphResponse> {
  return useQuery({
    queryKey: ["pipeline", "dependency-graph"],
    queryFn: async () => {
      const response = await apiClient.get<DependencyGraphResponse>("/pipeline/dependency-graph");
      return response.data;
    },
    refetchInterval: 60000, // Refresh every minute (graph doesn't change often)
  });
}

// Pipeline Metrics Summary Hook
export function usePipelineMetricsSummary(): UseQueryResult<PipelineMetricsSummary> {
  return useQuery({
    queryKey: ["pipeline", "metrics", "summary"],
    queryFn: async () => {
      const response = await apiClient.get<PipelineMetricsSummary>("/pipeline/metrics/summary");
      return response.data;
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

// Event Bus Hooks (Phase 3)
export function useEventStream(
  eventType?: string,
  limit: number = 100,
  sinceMinutes?: number
): UseQueryResult<EventStreamItem[]> {
  return useQuery({
    queryKey: ["events", "stream", eventType, limit, sinceMinutes],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (eventType) params.append("event_type", eventType);
      params.append("limit", limit.toString());
      if (sinceMinutes !== undefined) params.append("since_minutes", sinceMinutes.toString());
      const response = await apiClient.get<EventStreamItem[]>(
        `/events/stream?${params.toString()}`
      );
      return response.data;
    },
    refetchInterval: 5000, // Refresh every 5 seconds for real-time updates
  });
}

export function useEventStatistics(): UseQueryResult<EventStatistics> {
  return useQuery({
    queryKey: ["events", "stats"],
    queryFn: async () => {
      const response = await apiClient.get<EventStatistics>("/events/stats");
      return response.data;
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

export function useEventTypes(): UseQueryResult<EventTypesResponse> {
  return useQuery({
    queryKey: ["events", "types"],
    queryFn: async () => {
      const response = await apiClient.get<EventTypesResponse>("/events/types");
      return response.data;
    },
    staleTime: 300000, // Cache for 5 minutes (event types don't change often)
  });
}

// Cache Hooks (Phase 3)
export function useCacheStatistics(): UseQueryResult<CacheStatistics> {
  return useQuery({
    queryKey: ["cache", "stats"],
    queryFn: async () => {
      const response = await apiClient.get<CacheStatistics>("/cache/stats");
      return response.data;
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

export function useCacheKeys(
  pattern?: string,
  limit: number = 100
): UseQueryResult<CacheKeysResponse> {
  return useQuery({
    queryKey: ["cache", "keys", pattern, limit],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (pattern) params.append("pattern", pattern);
      params.append("limit", limit.toString());
      const response = await apiClient.get<CacheKeysResponse>(`/cache/keys?${params.toString()}`);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

export function useCacheKey(key: string): UseQueryResult<CacheKeyDetail> {
  return useQuery({
    queryKey: ["cache", "keys", key],
    queryFn: async () => {
      const response = await apiClient.get<CacheKeyDetail>(
        `/cache/keys/${encodeURIComponent(key)}`
      );
      return response.data;
    },
    enabled: !!key,
    refetchInterval: 30000,
  });
}

export function useCachePerformance(): UseQueryResult<CachePerformance> {
  return useQuery({
    queryKey: ["cache", "performance"],
    queryFn: async () => {
      const response = await apiClient.get<CachePerformance>("/cache/performance");
      return response.data;
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}
