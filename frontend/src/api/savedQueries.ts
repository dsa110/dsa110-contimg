/**
 * Saved Queries API
 *
 * Provides hooks for saving, loading, and sharing filter configurations.
 * Users can save their current filter state, name it, set visibility,
 * and generate shareable links.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";
import type { UrlFilterState } from "../hooks/useUrlFilterState";

// ============================================================================
// Types
// ============================================================================

/** Query visibility levels */
export type QueryVisibility = "private" | "shared" | "global";

/** Saved query context/scope */
export type QueryContext =
  | "sources"
  | "images"
  | "jobs"
  | "logs"
  | "calibrators"
  | "general";

/** Saved query record */
export interface SavedQuery {
  id: string;
  name: string;
  description?: string;
  visibility: QueryVisibility;
  context: QueryContext;
  /** Serialized filter state */
  filters: UrlFilterState;
  /** Owner user ID */
  owner_id: string;
  /** Owner username for display */
  owner_username: string;
  /** Number of times this query has been used */
  use_count: number;
  created_at: string;
  updated_at: string;
  /** Whether current user can edit this query */
  can_edit: boolean;
}

/** Create/update query request */
export interface SaveQueryRequest {
  name: string;
  description?: string;
  visibility: QueryVisibility;
  context: QueryContext;
  filters: UrlFilterState;
}

/** List queries filter options */
export interface SavedQueryFilters {
  visibility?: QueryVisibility;
  context?: QueryContext;
  owner?: "me" | "others" | "all";
  search?: string;
}

/** Pagination info */
export interface PaginationInfo {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

/** List response */
export interface SavedQueriesResponse {
  queries: SavedQuery[];
  pagination: PaginationInfo;
}

// ============================================================================
// Query Keys
// ============================================================================

export const savedQueryKeys = {
  all: ["savedQueries"] as const,
  lists: () => [...savedQueryKeys.all, "list"] as const,
  list: (filters?: SavedQueryFilters, page?: number) =>
    [...savedQueryKeys.lists(), { filters, page }] as const,
  details: () => [...savedQueryKeys.all, "detail"] as const,
  detail: (id: string) => [...savedQueryKeys.details(), id] as const,
};

// ============================================================================
// API Functions
// ============================================================================

async function fetchSavedQueries(
  filters?: SavedQueryFilters,
  page = 1,
  perPage = 20
): Promise<SavedQueriesResponse> {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("per_page", String(perPage));

  if (filters?.visibility) params.set("visibility", filters.visibility);
  if (filters?.context) params.set("context", filters.context);
  if (filters?.owner) params.set("owner", filters.owner);
  if (filters?.search) params.set("search", filters.search);

  const response = await apiClient.get<SavedQueriesResponse>(
    `/v1/saved-queries?${params.toString()}`
  );
  return response.data;
}

async function fetchSavedQuery(id: string): Promise<SavedQuery> {
  const response = await apiClient.get<SavedQuery>(`/v1/saved-queries/${id}`);
  return response.data;
}

async function createSavedQuery(data: SaveQueryRequest): Promise<SavedQuery> {
  const response = await apiClient.post<SavedQuery>("/v1/saved-queries", data);
  return response.data;
}

async function updateSavedQuery(
  id: string,
  data: Partial<SaveQueryRequest>
): Promise<SavedQuery> {
  const response = await apiClient.patch<SavedQuery>(
    `/v1/saved-queries/${id}`,
    data
  );
  return response.data;
}

async function deleteSavedQuery(id: string): Promise<void> {
  await apiClient.delete(`/v1/saved-queries/${id}`);
}

async function recordQueryUsage(id: string): Promise<void> {
  await apiClient.post(`/v1/saved-queries/${id}/use`);
}

// ============================================================================
// Hooks
// ============================================================================

/**
 * Hook to fetch list of saved queries with filtering and pagination.
 */
export function useSavedQueries(
  filters?: SavedQueryFilters,
  page = 1,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: savedQueryKeys.list(filters, page),
    queryFn: () => fetchSavedQueries(filters, page),
    staleTime: 30_000, // 30 seconds
    ...options,
  });
}

/**
 * Hook to fetch a single saved query by ID.
 */
export function useSavedQuery(id: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: savedQueryKeys.detail(id),
    queryFn: () => fetchSavedQuery(id),
    enabled: Boolean(id) && options?.enabled !== false,
    staleTime: 60_000, // 1 minute
  });
}

/**
 * Hook to create a new saved query.
 */
export function useCreateSavedQuery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createSavedQuery,
    onSuccess: () => {
      // Invalidate all lists to refetch
      queryClient.invalidateQueries({ queryKey: savedQueryKeys.lists() });
    },
  });
}

/**
 * Hook to update an existing saved query.
 */
export function useUpdateSavedQuery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: Partial<SaveQueryRequest>;
    }) => updateSavedQuery(id, data),
    onSuccess: (updatedQuery) => {
      // Update the specific query in cache
      queryClient.setQueryData(
        savedQueryKeys.detail(updatedQuery.id),
        updatedQuery
      );
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: savedQueryKeys.lists() });
    },
  });
}

/**
 * Hook to delete a saved query.
 */
export function useDeleteSavedQuery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteSavedQuery,
    onSuccess: (_, deletedId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: savedQueryKeys.detail(deletedId) });
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: savedQueryKeys.lists() });
    },
  });
}

/**
 * Hook to record usage of a saved query (increments use_count).
 */
export function useRecordQueryUsage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: recordQueryUsage,
    onSuccess: (_, id) => {
      // Invalidate the specific query to refetch use_count
      queryClient.invalidateQueries({ queryKey: savedQueryKeys.detail(id) });
    },
  });
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Serialize filter state to URL search params string.
 * Used for generating shareable links.
 */
export function serializeFilters(filters: UrlFilterState): string {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });

  return params.toString();
}

/**
 * Parse URL search params string into filter state.
 */
export function parseFilters(searchString: string): UrlFilterState {
  const params = new URLSearchParams(searchString);
  const filters: UrlFilterState = {};

  // Parse numeric fields
  const numericFields = [
    "ra",
    "dec",
    "radius",
    "minFlux",
    "maxFlux",
    "minImages",
  ] as const;
  numericFields.forEach((field) => {
    const value = params.get(field);
    if (value !== null) {
      const num = Number(value);
      if (!isNaN(num)) {
        filters[field] = num;
      }
    }
  });

  // Parse string fields
  const stringFields = ["name", "tab"] as const;
  stringFields.forEach((field) => {
    const value = params.get(field);
    if (value !== null) {
      filters[field] = value;
    }
  });

  // Parse boolean fields
  const booleanFields = ["variable"] as const;
  booleanFields.forEach((field) => {
    const value = params.get(field);
    if (value !== null) {
      filters[field] = value === "true";
    }
  });

  return filters;
}

/**
 * Generate a shareable URL for a saved query.
 */
export function generateShareableUrl(
  query: SavedQuery,
  baseUrl: string = window.location.origin
): string {
  const filterParams = serializeFilters(query.filters);
  const contextPath = getContextPath(query.context);
  return `${baseUrl}${contextPath}?${filterParams}&savedQuery=${query.id}`;
}

/**
 * Get the base path for a query context.
 */
function getContextPath(context: QueryContext): string {
  switch (context) {
    case "sources":
      return "/sources";
    case "images":
      return "/images";
    case "jobs":
      return "/jobs";
    case "logs":
      return "/logs";
    case "calibrators":
      return "/calibrators";
    default:
      return "/";
  }
}

/**
 * Check if two filter states are equivalent.
 */
export function filtersEqual(a: UrlFilterState, b: UrlFilterState): boolean {
  const keysA = Object.keys(a).filter(
    (k) => a[k as keyof UrlFilterState] !== undefined
  );
  const keysB = Object.keys(b).filter(
    (k) => b[k as keyof UrlFilterState] !== undefined
  );

  if (keysA.length !== keysB.length) return false;

  return keysA.every((key) => {
    const k = key as keyof UrlFilterState;
    return a[k] === b[k];
  });
}

/**
 * Get a human-readable summary of filters.
 */
export function getFilterSummary(filters: UrlFilterState): string {
  const parts: string[] = [];

  if (filters.ra !== undefined && filters.dec !== undefined) {
    const radius = filters.radius ?? 1;
    parts.push(
      `Cone: (${filters.ra.toFixed(2)}°, ${filters.dec.toFixed(
        2
      )}°) r=${radius}°`
    );
  }

  if (filters.minFlux !== undefined || filters.maxFlux !== undefined) {
    const min = filters.minFlux?.toFixed(3) ?? "0";
    const max = filters.maxFlux?.toFixed(3) ?? "∞";
    parts.push(`Flux: ${min}-${max} Jy`);
  }

  if (filters.minImages !== undefined) {
    parts.push(`≥${filters.minImages} images`);
  }

  if (filters.name) {
    parts.push(`Name: "${filters.name}"`);
  }

  if (filters.variable) {
    parts.push("Variable only");
  }

  return parts.length > 0 ? parts.join(" • ") : "No filters";
}

// ============================================================================
// Visibility helpers
// ============================================================================

export function getVisibilityLabel(visibility: QueryVisibility): string {
  switch (visibility) {
    case "private":
      return "Private";
    case "shared":
      return "Shared with team";
    case "global":
      return "Public";
    default:
      return visibility;
  }
}

export function getVisibilityIcon(visibility: QueryVisibility): string {
  switch (visibility) {
    case "private":
      return "🔒";
    case "shared":
      return "👥";
    case "global":
      return "🌐";
    default:
      return "❓";
  }
}
