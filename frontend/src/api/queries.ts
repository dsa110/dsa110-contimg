/**
 * React Query hooks for API data fetching.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';
import { apiClient } from './client';
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
  QAMetrics,
  BatchJob,
  BatchJobList,
  BatchJobCreateRequest,
  ImageList,
  ImageFilters,
} from './types';

export function usePipelineStatus(): UseQueryResult<PipelineStatus> {
  return useQuery({
    queryKey: ['pipeline', 'status'],
    queryFn: async () => {
      const response = await apiClient.get<PipelineStatus>('/api/status');
      return response.data;
    },
    refetchInterval: 10000, // Poll every 10 seconds
  });
}

export function useSystemMetrics(): UseQueryResult<SystemMetrics> {
  return useQuery({
    queryKey: ['system', 'metrics'],
    queryFn: async () => {
      const response = await apiClient.get<SystemMetrics>('/api/metrics/system');
      return response.data;
    },
    refetchInterval: 10000,
  });
}

export function useESECandidates(): UseQueryResult<ESECandidatesResponse> {
  return useQuery({
    queryKey: ['ese', 'candidates'],
    queryFn: async () => {
      const response = await apiClient.get<ESECandidatesResponse>('/api/ese/candidates');
      return response.data;
    },
    refetchInterval: 10000, // Live updates
  });
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
      const body: any = {};
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
 *   console.log('Overall quality:', calQA.overall_quality);
 *   console.log('Flag fraction:', calQA.flags_total);
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
 * Hook to fetch image QA metrics for an MS.
 * 
 * @param msPath - Path to the MS file
 * @returns Image QA metrics including RMS, dynamic range, beam parameters
 * 
 * @example
 * const { data: imgQA } = useImageQA('/path/to/ms');
 * if (imgQA) {
 *   console.log('RMS noise:', imgQA.rms_noise, 'Jy/beam');
 *   console.log('Dynamic range:', imgQA.dynamic_range);
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
 *   console.log('Cal quality:', qa.calibration_qa.overall_quality);
 * }
 * if (qa?.image_qa) {
 *   console.log('Image quality:', qa.image_qa.overall_quality);
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
