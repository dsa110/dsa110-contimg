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
  JobList,
  Job,
  JobCreateRequest,
  UVH5FileList,
  ConversionJobCreateRequest,
  CalTableList,
  MSMetadata,
  MSCalibratorMatchList,
  ExistingCalTables,
  WorkflowJobCreateRequest,
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
      
      const url = `/api/ms${params.toString() ? `?${params.toString()}` : ''}`;
      const response = await apiClient.get<MSList>(url);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30s
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
