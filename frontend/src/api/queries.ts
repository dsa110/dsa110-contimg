/**
 * Shared Queries API - Saved and shared database queries
 *
 * Provides hooks for managing saved queries that can be shared across team members.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

// ============================================================================
// Types
// ============================================================================

export type QueryTarget = "source" | "image" | "job" | "observation" | "ms";
export type QueryVisibility = "private" | "team" | "public";

export interface SavedQuery {
  id: string;
  name: string;
  description: string;
  query_string: string;
  target_type: QueryTarget;
  visibility: QueryVisibility;
  owner_id: string;
  owner_name: string;
  is_favorite: boolean;
  run_count: number;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
  tags: string[];
  parameters: QueryParameter[];
}

export interface QueryParameter {
  name: string;
  type: "string" | "number" | "date" | "boolean";
  default_value?: string;
  description?: string;
  required: boolean;
}

export interface QueryResult {
  columns: string[];
  rows: Array<Record<string, unknown>>;
  row_count: number;
  execution_time_ms: number;
  truncated: boolean;
}

export interface CreateQueryRequest {
  name: string;
  description?: string;
  query_string: string;
  target_type: QueryTarget;
  visibility: QueryVisibility;
  tags?: string[];
  parameters?: QueryParameter[];
}

export interface UpdateQueryRequest {
  name?: string;
  description?: string;
  query_string?: string;
  target_type?: QueryTarget;
  visibility?: QueryVisibility;
  tags?: string[];
  parameters?: QueryParameter[];
}

export interface QuerySearchParams {
  search?: string;
  target_type?: QueryTarget;
  visibility?: QueryVisibility;
  owner_id?: string;
  tags?: string[];
  is_favorite?: boolean;
  sort_by?: "name" | "created_at" | "updated_at" | "run_count";
  sort_order?: "asc" | "desc";
  limit?: number;
  offset?: number;
}

export interface RunQueryRequest {
  query_id?: string;
  query_string?: string;
  parameters?: Record<string, string>;
  limit?: number;
}

export interface QueryStats {
  total_queries: number;
  public_queries: number;
  team_queries: number;
  private_queries: number;
  queries_run_today: number;
  queries_run_this_week: number;
  popular_tags: Array<{ tag: string; count: number }>;
  top_queries: Array<{
    id: string;
    name: string;
    run_count: number;
    owner_name: string;
  }>;
}

// ============================================================================
// Query Keys
// ============================================================================

export const queryKeys = {
  all: ["queries"] as const,
  lists: () => [...queryKeys.all, "list"] as const,
  list: (params: QuerySearchParams) => [...queryKeys.lists(), params] as const,
  details: () => [...queryKeys.all, "detail"] as const,
  detail: (id: string) => [...queryKeys.details(), id] as const,
  results: (id: string) => [...queryKeys.all, "results", id] as const,
  favorites: () => [...queryKeys.all, "favorites"] as const,
  stats: () => [...queryKeys.all, "stats"] as const,
  history: () => [...queryKeys.all, "history"] as const,
};

// ============================================================================
// API Functions
// ============================================================================

async function getQueries(
  params: QuerySearchParams = {}
): Promise<SavedQuery[]> {
  const response = await apiClient.get("/api/queries", { params });
  return response.data;
}

async function getQuery(id: string): Promise<SavedQuery> {
  const response = await apiClient.get(`/api/queries/${id}`);
  return response.data;
}

async function createQuery(data: CreateQueryRequest): Promise<SavedQuery> {
  const response = await apiClient.post("/api/queries", data);
  return response.data;
}

async function updateQuery(
  id: string,
  data: UpdateQueryRequest
): Promise<SavedQuery> {
  const response = await apiClient.patch(`/api/queries/${id}`, data);
  return response.data;
}

async function deleteQuery(id: string): Promise<void> {
  await apiClient.delete(`/api/queries/${id}`);
}

async function runQuery(data: RunQueryRequest): Promise<QueryResult> {
  const response = await apiClient.post("/api/queries/run", data);
  return response.data;
}

async function favoriteQuery(id: string): Promise<SavedQuery> {
  const response = await apiClient.post(`/api/queries/${id}/favorite`);
  return response.data;
}

async function unfavoriteQuery(id: string): Promise<SavedQuery> {
  const response = await apiClient.delete(`/api/queries/${id}/favorite`);
  return response.data;
}

async function cloneQuery(id: string): Promise<SavedQuery> {
  const response = await apiClient.post(`/api/queries/${id}/clone`);
  return response.data;
}

async function getFavoriteQueries(): Promise<SavedQuery[]> {
  const response = await apiClient.get("/api/queries/favorites");
  return response.data;
}

async function getQueryHistory(): Promise<
  Array<{ query_id: string; query_name: string; run_at: string }>
> {
  const response = await apiClient.get("/api/queries/history");
  return response.data;
}

async function getQueryStats(): Promise<QueryStats> {
  const response = await apiClient.get("/api/queries/stats");
  return response.data;
}

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Fetch saved queries with optional filtering
 */
export function useQueries(params: QuerySearchParams = {}) {
  return useQuery({
    queryKey: queryKeys.list(params),
    queryFn: () => getQueries(params),
  });
}

/**
 * Fetch a single query by ID
 */
export function useSavedQuery(id: string) {
  return useQuery({
    queryKey: queryKeys.detail(id),
    queryFn: () => getQuery(id),
    enabled: !!id,
  });
}

/**
 * Fetch favorite queries
 */
export function useFavoriteQueries() {
  return useQuery({
    queryKey: queryKeys.favorites(),
    queryFn: getFavoriteQueries,
  });
}

/**
 * Fetch query execution history
 */
export function useQueryHistory() {
  return useQuery({
    queryKey: queryKeys.history(),
    queryFn: getQueryHistory,
  });
}

/**
 * Fetch query statistics
 */
export function useQueryStats() {
  return useQuery({
    queryKey: queryKeys.stats(),
    queryFn: getQueryStats,
    staleTime: 30000, // 30 seconds
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Create a new saved query
 */
export function useCreateQuery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createQuery,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: queryKeys.stats() });
    },
  });
}

/**
 * Update an existing query
 */
export function useUpdateQuery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateQueryRequest }) =>
      updateQuery(id, data),
    onSuccess: (updatedQuery) => {
      queryClient.setQueryData(queryKeys.detail(updatedQuery.id), updatedQuery);
      queryClient.invalidateQueries({ queryKey: queryKeys.lists() });
    },
  });
}

/**
 * Delete a query
 */
export function useDeleteQuery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteQuery,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.all });
    },
  });
}

/**
 * Run a query
 */
export function useRunQuery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: runQuery,
    onSuccess: () => {
      // Invalidate history to show recent execution
      queryClient.invalidateQueries({ queryKey: queryKeys.history() });
      // Invalidate stats for run counts
      queryClient.invalidateQueries({ queryKey: queryKeys.stats() });
    },
  });
}

/**
 * Add query to favorites
 */
export function useFavoriteQuery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: favoriteQuery,
    onSuccess: (updatedQuery) => {
      queryClient.setQueryData(queryKeys.detail(updatedQuery.id), updatedQuery);
      queryClient.invalidateQueries({ queryKey: queryKeys.favorites() });
      queryClient.invalidateQueries({ queryKey: queryKeys.lists() });
    },
  });
}

/**
 * Remove query from favorites
 */
export function useUnfavoriteQuery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: unfavoriteQuery,
    onSuccess: (updatedQuery) => {
      queryClient.setQueryData(queryKeys.detail(updatedQuery.id), updatedQuery);
      queryClient.invalidateQueries({ queryKey: queryKeys.favorites() });
      queryClient.invalidateQueries({ queryKey: queryKeys.lists() });
    },
  });
}

/**
 * Clone a query
 */
export function useCloneQuery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: cloneQuery,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: queryKeys.stats() });
    },
  });
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Format query target type for display
 */
export function getTargetTypeLabel(type: QueryTarget): string {
  const labels: Record<QueryTarget, string> = {
    source: "Sources",
    image: "Images",
    job: "Jobs",
    observation: "Observations",
    ms: "Measurement Sets",
  };
  return labels[type];
}

/**
 * Get icon for visibility
 */
export function getVisibilityIcon(visibility: QueryVisibility): string {
  const icons: Record<QueryVisibility, string> = {
    private: "🔒",
    team: "👥",
    public: "🌐",
  };
  return icons[visibility];
}

/**
 * Get label for visibility
 */
export function getVisibilityLabel(visibility: QueryVisibility): string {
  const labels: Record<QueryVisibility, string> = {
    private: "Private",
    team: "Team",
    public: "Public",
  };
  return labels[visibility];
}

/**
 * Format execution time
 */
export function formatExecutionTime(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

/**
 * Validate query syntax (basic check)
 */
export function validateQuerySyntax(query: string): {
  valid: boolean;
  error?: string;
} {
  if (!query.trim()) {
    return { valid: false, error: "Query cannot be empty" };
  }

  // Check for potentially dangerous keywords
  const dangerousKeywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE"];
  const upperQuery = query.toUpperCase();

  for (const keyword of dangerousKeywords) {
    if (upperQuery.includes(keyword)) {
      return {
        valid: false,
        error: `Query contains potentially dangerous keyword: ${keyword}`,
      };
    }
  }

  return { valid: true };
}

/**
 * Extract parameters from query string
 */
export function extractParameters(query: string): string[] {
  const paramRegex = /\{\{(\w+)\}\}/g;
  const params: string[] = [];
  let match;
  while ((match = paramRegex.exec(query)) !== null) {
    if (!params.includes(match[1])) {
      params.push(match[1]);
    }
  }
  return params;
}

/**
 * Replace parameters in query string
 */
export function substituteParameters(
  query: string,
  params: Record<string, string>
): string {
  let result = query;
  for (const [key, value] of Object.entries(params)) {
    result = result.replace(new RegExp(`\\{\\{${key}\\}\\}`, "g"), value);
  }
  return result;
}
