/**
 * React Query hooks for Pipeline Control operations.
 *
 * Provides hooks for:
 * - Listing registered pipelines
 * - Running full pipelines
 * - Running individual stages
 * - Getting execution status
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { config } from "../config";
import { pipelineKeys } from "../lib/queryKeys";
import { absurdQueryKeys } from "./useAbsurdQueries";

// API base URL for pipeline endpoints
const API_BASE = config.api.baseUrl;

// =============================================================================
// Types
// =============================================================================

export interface PipelineInfo {
  name: string;
  description: string;
  schedule: string | null;
  is_scheduled: boolean;
}

export interface PipelineListResponse {
  pipelines: PipelineInfo[];
  total: number;
}

export interface StageInfo {
  name: string;
  description: string;
}

export interface StageListResponse {
  stages: StageInfo[];
  total: number;
}

export interface RunPipelineResponse {
  execution_id: string;
  pipeline_name: string;
  status: string;
  message: string;
}

export interface FullPipelineRequest {
  start_time: string;
  end_time: string;
  input_dir?: string;
  output_dir?: string;
  run_calibration?: boolean;
  run_imaging?: boolean;
  imaging_params?: Record<string, unknown>;
}

export interface FullPipelineResponse {
  status: string;
  task_ids: Record<string, string>;
  time_range: {
    start: string;
    end: string;
  };
  message: string;
}

export interface StageTaskRequest {
  stage: string;
  params: Record<string, unknown>;
  priority?: number;
}

export interface StageTaskResponse {
  task_id: string;
  stage: string;
  status: string;
}

export interface ExecutionJob {
  job_id: string;
  job_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

export interface ExecutionStatus {
  execution_id: string;
  pipeline_name: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  jobs: ExecutionJob[];
}

export interface ExecutionListResponse {
  executions: ExecutionStatus[];
  total: number;
}

// =============================================================================
// API Functions
// =============================================================================

async function fetchRegisteredPipelines(): Promise<PipelineListResponse> {
  const response = await fetch(`${API_BASE}/pipeline/registered`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch pipelines: ${response.statusText}`);
  }
  return response.json();
}

async function fetchAvailableStages(): Promise<StageListResponse> {
  const response = await fetch(`${API_BASE}/pipeline/stages`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch stages: ${response.statusText}`);
  }
  return response.json();
}

async function runPipeline(
  pipelineName: string,
  params: Record<string, unknown> = {}
): Promise<RunPipelineResponse> {
  const response = await fetch(`${API_BASE}/pipeline/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      pipeline_name: pipelineName,
      params,
    }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      error.detail || `Failed to run pipeline: ${response.statusText}`
    );
  }
  return response.json();
}

async function runFullPipeline(
  request: FullPipelineRequest
): Promise<FullPipelineResponse> {
  const response = await fetch(`${API_BASE}/pipeline/full`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      error.detail || `Failed to run full pipeline: ${response.statusText}`
    );
  }
  return response.json();
}

async function runStage(request: StageTaskRequest): Promise<StageTaskResponse> {
  const response = await fetch(`${API_BASE}/pipeline/stage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      error.detail || `Failed to run stage: ${response.statusText}`
    );
  }
  return response.json();
}

async function calibrateMS(
  msPath: string,
  applyOnly: boolean = true
): Promise<StageTaskResponse> {
  const params = new URLSearchParams({
    ms_path: msPath,
    apply_only: String(applyOnly),
  });
  const response = await fetch(`${API_BASE}/pipeline/calibrate?${params}`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      error.detail || `Failed to calibrate: ${response.statusText}`
    );
  }
  return response.json();
}

async function imageMS(
  msPath: string,
  options: {
    imsize?: number;
    cell?: string;
    niter?: number;
    threshold?: string;
    weighting?: string;
    robust?: number;
  } = {}
): Promise<StageTaskResponse> {
  const params = new URLSearchParams({
    ms_path: msPath,
    ...(options.imsize && { imsize: String(options.imsize) }),
    ...(options.cell && { cell: options.cell }),
    ...(options.niter && { niter: String(options.niter) }),
    ...(options.threshold && { threshold: options.threshold }),
    ...(options.weighting && { weighting: options.weighting }),
    ...(options.robust !== undefined && { robust: String(options.robust) }),
  });
  const response = await fetch(`${API_BASE}/pipeline/image?${params}`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to image: ${response.statusText}`);
  }
  return response.json();
}

async function fetchExecutions(
  limit: number = 50,
  statusFilter?: string
): Promise<ExecutionListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (statusFilter) {
    params.append("status_filter", statusFilter);
  }
  const response = await fetch(`${API_BASE}/pipeline/executions?${params}`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch executions: ${response.statusText}`);
  }
  return response.json();
}

async function fetchExecution(executionId: string): Promise<ExecutionStatus> {
  const response = await fetch(
    `${API_BASE}/pipeline/executions/${executionId}`,
    {
      credentials: "include",
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to fetch execution: ${response.statusText}`);
  }
  return response.json();
}

// =============================================================================
// React Query Hooks
// =============================================================================

/**
 * Hook to fetch registered pipelines.
 */
export function useRegisteredPipelines() {
  return useQuery({
    queryKey: pipelineKeys.registered(),
    queryFn: fetchRegisteredPipelines,
    staleTime: 60000, // 1 minute
  });
}

/**
 * Hook to fetch available stages.
 */
export function useAvailableStages() {
  return useQuery({
    queryKey: pipelineKeys.stages(),
    queryFn: fetchAvailableStages,
    staleTime: 300000, // 5 minutes (stages don't change often)
  });
}

/**
 * Hook to run a registered pipeline.
 */
export function useRunPipeline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      pipelineName,
      params = {},
    }: {
      pipelineName: string;
      params?: Record<string, unknown>;
    }) => runPipeline(pipelineName, params),
    onSuccess: () => {
      // Invalidate executions list
      queryClient.invalidateQueries({ queryKey: pipelineKeys.executions() });
      // Invalidate ABSURD tasks
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.tasks });
    },
  });
}

/**
 * Hook to run a full pipeline (conversion → calibration → imaging).
 */
export function useRunFullPipeline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: runFullPipeline,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.executions() });
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.tasks });
    },
  });
}

/**
 * Hook to run an individual stage.
 */
export function useRunStage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: runStage,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.tasks });
    },
  });
}

/**
 * Hook to calibrate a specific MS.
 */
export function useCalibrateMS() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      msPath,
      applyOnly = true,
    }: {
      msPath: string;
      applyOnly?: boolean;
    }) => calibrateMS(msPath, applyOnly),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.tasks });
    },
  });
}

/**
 * Hook to image a specific MS.
 */
export function useImageMS() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      msPath,
      options = {},
    }: {
      msPath: string;
      options?: {
        imsize?: number;
        cell?: string;
        niter?: number;
        threshold?: string;
        weighting?: string;
        robust?: number;
      };
    }) => imageMS(msPath, options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: absurdQueryKeys.tasks });
    },
  });
}

/**
 * Hook to fetch pipeline executions.
 */
export function useExecutions(limit: number = 50, statusFilter?: string) {
  return useQuery({
    queryKey: pipelineKeys.executionList({ limit, statusFilter }),
    queryFn: () => fetchExecutions(limit, statusFilter),
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

/**
 * Hook to fetch a specific execution.
 */
export function useExecution(executionId: string | null) {
  return useQuery({
    queryKey: pipelineKeys.execution(executionId!),
    queryFn: () => fetchExecution(executionId!),
    enabled: !!executionId,
    refetchInterval: 5000, // Refresh every 5 seconds while viewing
  });
}
