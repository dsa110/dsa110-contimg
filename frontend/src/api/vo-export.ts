/**
 * Virtual Observatory (VO) Export API
 *
 * Provides hooks for exporting data in VO-compatible formats:
 * - VOTable export
 * - FITS export with WCS
 * - Cone search integration
 * - TAP service queries
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

// ============================================================================
// Types
// ============================================================================

/** Supported VO export formats */
export type VOFormat = "votable" | "fits" | "csv" | "json";

/** Export status */
export type ExportStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | "expired";

/** Data types available for export */
export type ExportDataType = "sources" | "images" | "catalogs" | "spectra";

/** Export scope/filter */
export interface ExportFilter {
  /** Data type to export */
  data_type: ExportDataType;
  /** Cone search parameters */
  cone_search?: {
    ra: number;
    dec: number;
    radius_arcmin: number;
  };
  /** Time range filter */
  time_range?: {
    start: string;
    end: string;
  };
  /** Magnitude/flux limits */
  magnitude_range?: {
    min?: number;
    max?: number;
  };
  /** Quality flag filter */
  quality_flags?: string[];
  /** Maximum number of records */
  limit?: number;
  /** Column selection */
  columns?: string[];
}

/** Export job record */
export interface ExportJob {
  id: string;
  name: string;
  format: VOFormat;
  data_type: ExportDataType;
  filter: ExportFilter;
  status: ExportStatus;
  record_count: number;
  file_size_bytes: number;
  file_size_formatted: string;
  created_at: string;
  completed_at?: string;
  expires_at?: string;
  download_url?: string;
  error_message?: string;
  created_by: string;
}

/** Export request */
export interface CreateExportRequest {
  name?: string;
  format: VOFormat;
  filter: ExportFilter;
}

/** Available columns for export */
export interface ExportColumn {
  name: string;
  ucd: string;
  unit?: string;
  description: string;
  data_type: string;
  required: boolean;
}

/** Export preview/estimate */
export interface ExportPreview {
  estimated_records: number;
  estimated_size_bytes: number;
  estimated_time_seconds: number;
  available_columns: ExportColumn[];
  warnings: string[];
}

/** TAP query result */
export interface TAPResult {
  query_id: string;
  status: "queued" | "executing" | "completed" | "error" | "aborted";
  result_count?: number;
  result_url?: string;
  error_message?: string;
}

/** Cone search result summary */
export interface ConeSearchResult {
  total_matches: number;
  search_ra: number;
  search_dec: number;
  search_radius: number;
  sources: Array<{
    id: string;
    name: string;
    ra: number;
    dec: number;
    separation_arcsec: number;
  }>;
}

// ============================================================================
// Query Keys
// ============================================================================

export const voExportKeys = {
  all: ["vo-exports"] as const,
  lists: () => [...voExportKeys.all, "list"] as const,
  list: (filters: Record<string, unknown>) =>
    [...voExportKeys.lists(), filters] as const,
  details: () => [...voExportKeys.all, "detail"] as const,
  detail: (id: string) => [...voExportKeys.details(), id] as const,
  preview: (filter: ExportFilter) =>
    [...voExportKeys.all, "preview", filter] as const,
  columns: (dataType: ExportDataType) =>
    [...voExportKeys.all, "columns", dataType] as const,
  coneSearch: (ra: number, dec: number, radius: number) =>
    [...voExportKeys.all, "cone-search", ra, dec, radius] as const,
};

// ============================================================================
// Hooks
// ============================================================================

/**
 * Fetch list of export jobs
 */
export function useExportJobs(options?: {
  status?: ExportStatus;
  format?: VOFormat;
  limit?: number;
}) {
  return useQuery({
    queryKey: voExportKeys.list(options ?? {}),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (options?.status) params.append("status", options.status);
      if (options?.format) params.append("format", options.format);
      if (options?.limit) params.append("limit", options.limit.toString());

      const response = await apiClient.get<{ exports: ExportJob[] }>(
        `/api/v1/vo/exports?${params}`
      );
      return response.data.exports;
    },
    staleTime: 30_000,
  });
}

/**
 * Fetch single export job details
 */
export function useExportJob(id: string) {
  return useQuery({
    queryKey: voExportKeys.detail(id),
    queryFn: async () => {
      const response = await apiClient.get<ExportJob>(
        `/api/v1/vo/exports/${id}`
      );
      return response.data;
    },
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && (data.status === "pending" || data.status === "processing")) {
        return 3000;
      }
      return false;
    },
  });
}

/**
 * Get available columns for a data type
 */
export function useExportColumns(dataType: ExportDataType) {
  return useQuery({
    queryKey: voExportKeys.columns(dataType),
    queryFn: async () => {
      const response = await apiClient.get<{ columns: ExportColumn[] }>(
        `/api/v1/vo/columns/${dataType}`
      );
      return response.data.columns;
    },
    staleTime: 300_000, // 5 minutes
  });
}

/**
 * Preview export (estimate size/count)
 */
export function useExportPreview() {
  return useMutation({
    mutationFn: async (filter: ExportFilter) => {
      const response = await apiClient.post<ExportPreview>(
        "/v1/vo/exports/preview",
        filter
      );
      return response.data;
    },
  });
}

/**
 * Create a new export job
 */
export function useCreateExport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: CreateExportRequest) => {
      const response = await apiClient.post<ExportJob>(
        "/v1/vo/exports",
        request
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: voExportKeys.lists() });
    },
  });
}

/**
 * Delete/cancel an export job
 */
export function useDeleteExport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/vo/exports/${id}`);
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: voExportKeys.lists() });
    },
  });
}

/**
 * Perform cone search
 */
export function useConeSearch() {
  return useMutation({
    mutationFn: async (params: {
      ra: number;
      dec: number;
      radius_arcmin: number;
      limit?: number;
    }) => {
      const response = await apiClient.post<ConeSearchResult>(
        "/v1/vo/cone-search",
        params
      );
      return response.data;
    },
  });
}

/**
 * Submit TAP query
 */
export function useTAPQuery() {
  return useMutation({
    mutationFn: async (query: string) => {
      const response = await apiClient.post<TAPResult>("/v1/vo/tap/query", {
        query,
      });
      return response.data;
    },
  });
}

/**
 * Get TAP query status
 */
export function useTAPQueryStatus(queryId: string) {
  return useQuery({
    queryKey: [...voExportKeys.all, "tap", queryId],
    queryFn: async () => {
      const response = await apiClient.get<TAPResult>(
        `/v1/vo/tap/query/${queryId}`
      );
      return response.data;
    },
    enabled: !!queryId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && (data.status === "queued" || data.status === "executing")) {
        return 2000;
      }
      return false;
    },
  });
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Format VO format for display
 */
export function formatVOFormat(format: VOFormat): string {
  const labels: Record<VOFormat, string> = {
    votable: "VOTable",
    fits: "FITS",
    csv: "CSV",
    json: "JSON",
  };
  return labels[format];
}

/**
 * Get format file extension
 */
export function getFormatExtension(format: VOFormat): string {
  const extensions: Record<VOFormat, string> = {
    votable: ".xml",
    fits: ".fits",
    csv: ".csv",
    json: ".json",
  };
  return extensions[format];
}

/**
 * Format data type for display
 */
export function formatDataType(type: ExportDataType): string {
  const labels: Record<ExportDataType, string> = {
    sources: "Sources",
    images: "Images",
    catalogs: "Catalogs",
    spectra: "Spectra",
  };
  return labels[type];
}

/**
 * Format file size
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}
