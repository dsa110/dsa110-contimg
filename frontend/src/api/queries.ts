/**
 * React Query hooks for API data fetching.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { apiClient } from './client';
import { createWebSocketClient, WebSocketClient } from './websocket';
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
} from './types';

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
    const unsubscribe = wsClient.on('status_update', (data: any) => {
      if (data.data?.pipeline_status) {
        queryClient.setQueryData(['pipeline', 'status'], data.data.pipeline_status);
      }
      if (data.data?.metrics) {
        queryClient.setQueryData(['system', 'metrics'], data.data.metrics);
      }
      if (data.data?.ese_candidates) {
        queryClient.setQueryData(['ese', 'candidates'], data.data.ese_candidates);
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
  if (typeof window === 'undefined') {
    return null;
  }

  if (!wsClientInstance) {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const wsUrl = `${apiUrl}/api/ws/status`;
    
    try {
      wsClientInstance = createWebSocketClient({
        url: wsUrl,
        reconnectInterval: 3000,
        maxReconnectAttempts: 10,
        useSSE: false, // Try WebSocket first, fallback handled in client
      });
      wsClientInstance.connect();
    } catch (error) {
      console.warn('Failed to create WebSocket client, using polling:', error);
      return null;
    }
  }

  return wsClientInstance;
}

export function usePipelineStatus(): UseQueryResult<PipelineStatus> {
  const wsClient = getWebSocketClient();
  
  return useRealtimeQuery(
    ['pipeline', 'status'],
    async () => {
      const response = await apiClient.get<PipelineStatus>('/api/status');
      return response.data;
    },
    wsClient,
    10000 // Fallback polling interval
  );
}

export function useSystemMetrics(): UseQueryResult<SystemMetrics> {
  const wsClient = getWebSocketClient();
  
  return useRealtimeQuery(
    ['system', 'metrics'],
    async () => {
      const response = await apiClient.get<SystemMetrics>('/api/metrics/system');
      return response.data;
    },
    wsClient,
    10000
  );
}

export function useESECandidates(): UseQueryResult<ESECandidatesResponse> {
  const wsClient = getWebSocketClient();
  
  return useRealtimeQuery(
    ['ese', 'candidates'],
    async () => {
      const response = await apiClient.get<ESECandidatesResponse>('/api/ese/candidates');
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
    queryKey: ['mosaics', request],
    queryFn: async () => {
      if (!request) {
        return { mosaics: [], total: 0 };
      }
      const response = await apiClient.post<MosaicQueryResponse>('/api/mosaics/query', request);
      return response.data;
    },
    enabled: !!request,
  });
}

export function useMosaic(mosaicId: number | null): UseQueryResult<Mosaic> {
  return useQuery({
    queryKey: ['mosaics', mosaicId],
    queryFn: async () => {
      if (!mosaicId) throw new Error('Mosaic ID required');
      const response = await apiClient.get<Mosaic>(`/api/mosaics/${mosaicId}`);
      return response.data;
    },
    enabled: !!mosaicId,
  });
}

export function useSourceSearch(
  request: SourceSearchRequest | null
): UseQueryResult<SourceSearchResponse> {
  return useQuery({
    queryKey: ['sources', request],
    queryFn: async () => {
      if (!request) {
        return { sources: [], total: 0 };
      }
      const response = await apiClient.post<SourceSearchResponse>('/api/sources/search', request);
      return response.data;
    },
    enabled: !!request,
  });
}

export function useAlertHistory(limit = 50): UseQueryResult<AlertHistory[]> {
  return useQuery({
    queryKey: ['alerts', 'history', limit],
    queryFn: async () => {
      const response = await apiClient.get<AlertHistory[]>(`/api/alerts/history?limit=${limit}`);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30s
  });
}

export function useCreateMosaic() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: MosaicQueryRequest) => {
      const response = await apiClient.post('/api/mosaics/create', request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mosaics'] });
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
    queryKey: ['ms', 'list', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      
      if (filters?.search) params.append('search', filters.search);
      if (filters?.has_calibrator !== undefined) params.append('has_calibrator', String(filters.has_calibrator));
      if (filters?.is_calibrated !== undefined) params.append('is_calibrated', String(filters.is_calibrated));
      if (filters?.is_imaged !== undefined) params.append('is_imaged', String(filters.is_imaged));
      if (filters?.calibrator_quality) params.append('calibrator_quality', filters.calibrator_quality);
      if (filters?.start_date) params.append('start_date', filters.start_date);
      if (filters?.end_date) params.append('end_date', filters.end_date);
      if (filters?.sort_by) params.append('sort_by', filters.sort_by);
      if (filters?.limit !== undefined) params.append('limit', String(filters.limit));
      if (filters?.offset !== undefined) params.append('offset', String(filters.offset));
      if (filters?.scan) params.append('scan', String(filters.scan));
      if (filters?.scan_dir) params.append('scan_dir', filters.scan_dir);
      
      const url = `/api/ms${params.toString() ? `?${params.toString()}` : ''}`;
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
      const response = await apiClient.post<{ success: boolean; count: number; scan_dir: string; discovered: string[] }>('/api/ms/discover', body);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ms'] });
    },
  });
}

export function useJobs(limit = 50, status?: string): UseQueryResult<JobList> {
  return useQuery({
    queryKey: ['jobs', limit, status],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('limit', limit.toString());
      if (status) params.append('status', status);
      const response = await apiClient.get<JobList>(`/api/jobs?${params}`);
      return response.data;
    },
    refetchInterval: 5000, // Poll every 5 seconds
  });
}

export function useJob(jobId: number | null): UseQueryResult<Job> {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: async () => {
      if (!jobId) throw new Error('Job ID required');
      const response = await apiClient.get<Job>(`/api/jobs/id/${jobId}`);
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
      const response = await apiClient.post<Job>('/api/jobs/calibrate', request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}

export function useCreateApplyJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: JobCreateRequest) => {
      const response = await apiClient.post<Job>('/api/jobs/apply', request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}

export function useCreateImageJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: JobCreateRequest) => {
      const response = await apiClient.post<Job>('/api/jobs/image', request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}

export function useUVH5Files(inputDir?: string): UseQueryResult<UVH5FileList> {
  return useQuery({
    queryKey: ['uvh5', 'list', inputDir],
    queryFn: async () => {
      const params = inputDir ? `?input_dir=${encodeURIComponent(inputDir)}` : '';
      const response = await apiClient.get<UVH5FileList>(`/api/uvh5${params}`);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30s
  });
}

export function useCreateConvertJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: ConversionJobCreateRequest) => {
      const response = await apiClient.post<Job>('/api/jobs/convert', request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['ms'] });
    },
  });
}

// Cal table queries
export function useCalTables(calDir?: string): UseQueryResult<CalTableList> {
  return useQuery({
    queryKey: ['caltables', 'list', calDir],
    queryFn: async () => {
      const params = calDir ? `?cal_dir=${encodeURIComponent(calDir)}` : '';
      const response = await apiClient.get<CalTableList>(`/api/caltables${params}`);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30s
  });
}

// MS metadata query
export function useMSMetadata(msPath: string | null): UseQueryResult<MSMetadata> {
  return useQuery({
    queryKey: ['ms', 'metadata', msPath],
    queryFn: async () => {
      if (!msPath) throw new Error('MS path required');
      // Remove leading slash and encode
      const encodedPath = msPath.startsWith('/') ? msPath.slice(1) : msPath;
      const response = await apiClient.get<MSMetadata>(`/api/ms/${encodedPath}/metadata`);
      return response.data;
    },
    enabled: !!msPath,
    staleTime: 60000, // Cache for 1 minute
  });
}

// Calibrator match hook
export function useCalibratorMatches(
  msPath: string | null,
  catalog: string = 'vla',
  radiusDeg: number = 1.5
): UseQueryResult<MSCalibratorMatchList> {
  return useQuery({
    queryKey: ['ms', 'calibrator-matches', msPath, catalog, radiusDeg],
    queryFn: async () => {
      if (!msPath) throw new Error('MS path required');
      // Remove leading slash and encode
      const encodedPath = msPath.startsWith('/') ? msPath.slice(1) : msPath;
      const response = await apiClient.get<MSCalibratorMatchList>(
        `/api/ms/${encodedPath}/calibrator-matches`,
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
    queryKey: ['ms', 'existing-caltables', msPath],
    queryFn: async () => {
      if (!msPath) throw new Error('MS path required');
      // Remove leading slash and encode
      const encodedPath = msPath.startsWith('/') ? msPath.slice(1) : msPath;
      const response = await apiClient.get<ExistingCalTables>(
        `/api/ms/${encodedPath}/existing-caltables`
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
      const encodedMsPath = msPath.startsWith('/') ? msPath.slice(1) : msPath;
      const response = await apiClient.post<CalTableCompatibility>(
        `/api/ms/${encodedMsPath}/validate-caltable`,
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
    queryKey: ['qa', 'calibration', msPath],
    queryFn: async () => {
      if (!msPath) throw new Error('MS path required');
      // Remove leading slash and encode
      const encodedPath = msPath.startsWith('/') ? msPath.slice(1) : msPath;
      const response = await apiClient.get<CalibrationQA>(
        `/api/qa/calibration/${encodedPath}`
      );
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
    queryKey: ['qa', 'bandpass-plots', msPath],
    queryFn: async () => {
      if (!msPath) throw new Error('MS path required');
      // Remove leading slash and URL-encode the path (handles colons and other special chars)
      const pathWithoutLeadingSlash = msPath.startsWith('/') ? msPath.slice(1) : msPath;
      const encodedPath = encodeURIComponent(pathWithoutLeadingSlash);
      const response = await apiClient.get<BandpassPlotsList>(
        `/api/qa/calibration/${encodedPath}/bandpass-plots`
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
    queryKey: ['qa', 'image', msPath],
    queryFn: async () => {
      if (!msPath) throw new Error('MS path required');
      // Remove leading slash and encode
      const encodedPath = msPath.startsWith('/') ? msPath.slice(1) : msPath;
      const response = await apiClient.get<ImageQA>(
        `/api/qa/image/${encodedPath}`
      );
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
    queryKey: ['qa', 'combined', msPath],
    queryFn: async () => {
      if (!msPath) throw new Error('MS path required');
      // Remove leading slash and encode
      const encodedPath = msPath.startsWith('/') ? msPath.slice(1) : msPath;
      const response = await apiClient.get<QAMetrics>(
        `/api/qa/${encodedPath}`
      );
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
      const response = await apiClient.post<Job>('/api/jobs/workflow', request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['ms'] });
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
    queryKey: ['batch', 'jobs', limit, status],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      params.append('limit', String(limit));
      
      const url = `/api/batch${params.toString() ? `?${params.toString()}` : ''}`;
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
    queryKey: ['batch', 'job', batchId],
    queryFn: async () => {
      if (!batchId) throw new Error('Batch ID required');
      const response = await apiClient.get<BatchJob>(`/api/batch/${batchId}`);
      return response.data;
    },
    enabled: !!batchId,
    refetchInterval: (query) => {
      // Poll frequently if batch is still running
      const data = query.state.data;
      if (data?.status === 'running' || data?.status === 'pending') {
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
      const response = await apiClient.post<BatchJob>('/api/batch/calibrate', request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch'] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
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
      const response = await apiClient.post<BatchJob>('/api/batch/apply', request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch'] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
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
      const response = await apiClient.post<BatchJob>('/api/batch/image', request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch'] });
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
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
      const response = await apiClient.post(`/api/batch/${batchId}/cancel`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch'] });
    },
  });
}

/**
 * Query hook for fetching images for SkyView.
 */
export function useImages(filters?: ImageFilters): UseQueryResult<ImageList> {
  return useQuery({
    queryKey: ['images', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.limit) params.append('limit', filters.limit.toString());
      if (filters?.offset) params.append('offset', filters.offset.toString());
      if (filters?.ms_path) params.append('ms_path', filters.ms_path);
      if (filters?.image_type) params.append('image_type', filters.image_type);
      if (filters?.pbcor !== undefined) params.append('pbcor', filters.pbcor.toString());
      
      const response = await apiClient.get<ImageList>(`/api/images?${params.toString()}`);
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
    queryKey: ['streaming', 'status'],
    queryFn: async () => {
      const response = await apiClient.get<StreamingStatus>('/api/streaming/status');
      return response.data;
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  });
}

export function useStreamingHealth(): UseQueryResult<StreamingHealth> {
  return useQuery({
    queryKey: ['streaming', 'health'],
    queryFn: async () => {
      const response = await apiClient.get<StreamingHealth>('/api/streaming/health');
      return response.data;
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

export function useStreamingConfig(): UseQueryResult<StreamingConfig> {
  return useQuery({
    queryKey: ['streaming', 'config'],
    queryFn: async () => {
      const response = await apiClient.get<StreamingConfig>('/api/streaming/config');
      return response.data;
    },
  });
}

export function useStreamingMetrics(): UseQueryResult<StreamingMetrics> {
  return useQuery({
    queryKey: ['streaming', 'metrics'],
    queryFn: async () => {
      const response = await apiClient.get<StreamingMetrics>('/api/streaming/metrics');
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
    queryKey: ['pointing-monitor', 'status'],
    queryFn: async () => {
      const response = await apiClient.get<PointingMonitorStatus>('/api/pointing-monitor/status');
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
    queryKey: ['pointing-history', startMjd, endMjd],
    queryFn: async () => {
      const response = await apiClient.get<PointingHistoryList>(
        `/api/pointing_history?start_mjd=${startMjd}&end_mjd=${endMjd}`
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
      const response = await apiClient.post('/api/streaming/start', config || {});
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['streaming'] });
    },
  });
}

export function useStopStreaming() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post('/api/streaming/stop');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['streaming'] });
    },
  });
}

export function useRestartStreaming() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (config?: StreamingConfig) => {
      const response = await apiClient.post('/api/streaming/restart', config || {});
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['streaming'] });
    },
  });
}

export function useUpdateStreamingConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (config: StreamingConfig) => {
      const response = await apiClient.post('/api/streaming/config', config);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['streaming'] });
    },
  });
}

// Data Registry Queries
export function useDataInstances(
  dataType?: string,
  status?: 'staging' | 'published'
): UseQueryResult<DataInstance[]> {
  return useQuery({
    queryKey: ['data', 'instances', dataType, status],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (dataType) params.append('data_type', dataType);
      if (status) params.append('status', status);
      const response = await apiClient.get<DataInstance[]>(`/api/data?${params.toString()}`);
      return response.data;
    },
  });
}

export function useDataInstance(dataId: string): UseQueryResult<DataInstanceDetail> {
  return useQuery({
    queryKey: ['data', 'instance', dataId],
    queryFn: async () => {
      const encodedId = encodeURIComponent(dataId);
      const response = await apiClient.get<DataInstanceDetail>(`/api/data/${encodedId}`);
      return response.data;
    },
    enabled: !!dataId,
  });
}

export function useAutoPublishStatus(dataId: string): UseQueryResult<AutoPublishStatus> {
  return useQuery({
    queryKey: ['data', 'auto-publish', dataId],
    queryFn: async () => {
      const encodedId = encodeURIComponent(dataId);
      const response = await apiClient.get<AutoPublishStatus>(`/api/data/${encodedId}/auto-publish/status`);
      return response.data;
    },
    enabled: !!dataId,
  });
}

export function useDataLineage(dataId: string): UseQueryResult<DataLineage> {
  return useQuery({
    queryKey: ['data', 'lineage', dataId],
    queryFn: async () => {
      const encodedId = encodeURIComponent(dataId);
      const response = await apiClient.get<DataLineage>(`/api/data/${encodedId}/lineage`);
      return response.data;
    },
    enabled: !!dataId,
  });
}

// Catalog Validation Queries
export function useCatalogValidation(
  imageId: string | null,
  catalog: 'nvss' | 'vlass' = 'nvss',
  validationType: 'astrometry' | 'flux_scale' | 'source_counts' | 'all' = 'all'
): UseQueryResult<CatalogValidationResults> {
  return useQuery({
    queryKey: ['qa', 'catalog-validation', imageId, catalog, validationType],
    queryFn: async () => {
      if (!imageId) throw new Error('Image ID required');
      const encodedId = encodeURIComponent(imageId);
      const response = await apiClient.get<CatalogValidationResults>(
        `/api/qa/images/${encodedId}/catalog-validation?catalog=${catalog}&validation_type=${validationType}`
      );
      return response.data;
    },
    enabled: !!imageId,
    staleTime: 300000, // Cache for 5 minutes
  });
}

export function useCatalogOverlay(
  imageId: string | null,
  catalog: 'nvss' | 'vlass' = 'nvss',
  minFluxJy?: number
): UseQueryResult<CatalogOverlayData> {
  return useQuery({
    queryKey: ['qa', 'catalog-overlay', imageId, catalog, minFluxJy],
    queryFn: async () => {
      if (!imageId) throw new Error('Image ID required');
      const encodedId = encodeURIComponent(imageId);
      const params = new URLSearchParams({ catalog });
      if (minFluxJy !== undefined) params.append('min_flux_jy', minFluxJy.toString());
      const response = await apiClient.get<CatalogOverlayData>(
        `/api/qa/images/${encodedId}/catalog-overlay?${params.toString()}`
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
      catalog = 'nvss',
      validationTypes = ['astrometry', 'flux_scale', 'source_counts'],
    }: {
      imageId: string;
      catalog?: 'nvss' | 'vlass';
      validationTypes?: string[];
    }) => {
      const encodedId = encodeURIComponent(imageId);
      const response = await apiClient.post<CatalogValidationResults>(
        `/api/qa/images/${encodedId}/catalog-validation/run`,
        { catalog, validation_types: validationTypes }
      );
      return response.data;
    },
    onSuccess: (_data, variables) => {
      // Invalidate validation queries to refetch
      queryClient.invalidateQueries({
        queryKey: ['qa', 'catalog-validation', variables.imageId],
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
  catalog: string = 'all'
): UseQueryResult<CatalogOverlayResponse> {
  return useQuery({
    queryKey: ['catalog-overlay', ra, dec, radius, catalog],
    queryFn: async () => {
      if (ra === null || dec === null) throw new Error('RA and Dec required');
      const params = new URLSearchParams({
        ra: ra.toString(),
        dec: dec.toString(),
        radius: radius.toString(),
        catalog,
      });
      const response = await apiClient.get<CatalogOverlayResponse>(
        `/api/catalog/overlay?${params.toString()}`
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
  type: 'circle' | 'rectangle' | 'polygon';
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
    queryKey: ['regions', imagePath, regionType],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (imagePath) params.append('image_path', imagePath);
      if (regionType) params.append('region_type', regionType);
      const response = await apiClient.get<RegionListResponse>(
        `/api/regions?${params.toString()}`
      );
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
      const response = await apiClient.post<{ id: number; region: Region }>(
        '/api/regions',
        regionData
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['regions'] });
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
        `/api/regions/${regionId}`,
        regionData
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['regions'] });
    },
  });
}

export function useDeleteRegion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (regionId: number) => {
      const response = await apiClient.delete<{ id: number; deleted: boolean }>(
        `/api/regions/${regionId}`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['regions'] });
    },
  });
}

export function useRegionStatistics(regionId: number | null) {
  return useQuery({
    queryKey: ['region-statistics', regionId],
    queryFn: async () => {
      if (!regionId) throw new Error('Region ID required');
      const response = await apiClient.get<{
        region_id: number;
        statistics: Record<string, number>;
      }>(`/api/regions/${regionId}/statistics`);
      return response.data;
    },
    enabled: regionId !== null,
    staleTime: 60000, // Cache for 1 minute
  });
}

export interface ProfileExtractionRequest {
  imageId: number;
  profileType: 'line' | 'polyline' | 'point';
  coordinates: number[][];
  coordinateSystem?: 'wcs' | 'pixel';
  width?: number;
  radius?: number;
  fitModel?: 'gaussian' | 'moffat';
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
        coordinate_system: request.coordinateSystem || 'wcs',
        width: (request.width || 1).toString(),
      });

      if (request.profileType === 'point' && request.radius !== undefined) {
        params.append('radius', request.radius.toString());
      }

      if (request.fitModel) {
        params.append('fit_model', request.fitModel);
      }

      const response = await apiClient.get<ProfileExtractionResponse>(
        `/api/images/${request.imageId}/profile?${params.toString()}`
      );
      return response.data;
    },
  });
}

export interface ImageFittingRequest {
  imageId: number;
  model: 'gaussian' | 'moffat';
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
        `/api/images/${request.imageId}/fit`,
        body
      );
      return response.data;
    },
  });
}
