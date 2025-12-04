/**
 * Log aggregation API helpers and hooks.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import apiClient from "./client";
import type {
  LogEntry,
  LogQueryParams,
  LogQueryRequest,
  LogSearchResponse,
  LogTimeRange,
} from "@/types/logs";

const BASE_PATH = "/v1/logs";

// =============================================================================
// Query Keys
// =============================================================================

export const logKeys = {
  all: ["logs"] as const,
  search: (params?: LogQueryParams, limit?: number) =>
    [...logKeys.all, "search", params ?? {}, limit] as const,
  tail: (params?: LogQueryParams) =>
    [...logKeys.all, "tail", params ?? {}] as const,
};

// =============================================================================
// Helpers
// =============================================================================

function formatRangeValue(value: LogTimeRange["start"]): string | number {
  if (value instanceof Date) {
    return value.toISOString();
  }
  return value;
}

/**
 * Build query params for the logs search endpoint.
 */
export function buildLogQueryParams(
  params?: LogQueryRequest
): Record<string, string | number> {
  const query: Record<string, string | number> = {};
  if (!params) return query;

  const { q, level, labels, range, cursor, limit, direction } = params;

  if (q) query.q = q;
  if (level) {
    query.level = Array.isArray(level) ? level.join(",") : level;
  }
  if (labels) {
    Object.entries(labels).forEach(([key, value]) => {
      if (value === undefined || value === null) return;
      if (Array.isArray(value)) {
        const filtered = value.filter(
          (v) => v !== undefined && v !== null
        ) as Array<string | number>;
        if (filtered.length > 0) {
          query[`labels.${key}`] = filtered.join(",");
        }
      } else {
        query[`labels.${key}`] = String(value);
      }
    });
  }
  if (range?.start !== undefined) {
    query.start = formatRangeValue(range.start);
  }
  if (range?.end !== undefined) {
    query.end = formatRangeValue(range.end);
  }
  if (cursor) query.cursor = cursor;
  if (limit !== undefined) query.limit = limit;
  if (direction) query.direction = direction;

  return query;
}

// =============================================================================
// API Functions
// =============================================================================

export async function fetchLogs(
  params?: LogQueryRequest
): Promise<LogSearchResponse> {
  const response = await apiClient.get<LogSearchResponse>(
    `${BASE_PATH}/search`,
    { params: buildLogQueryParams(params) }
  );
  return response.data;
}

// =============================================================================
// React Query Hooks
// =============================================================================

export function useLogs(
  params: LogQueryParams = {},
  options?: {
    pageSize?: number;
    enabled?: boolean;
    refetchInterval?: number;
  }
) {
  const { pageSize = 200, enabled = true, refetchInterval } = options ?? {};

  return useInfiniteQuery({
    queryKey: logKeys.search(params, pageSize),
    initialPageParam: params.cursor ?? null,
    queryFn: ({ pageParam }) =>
      fetchLogs({
        ...params,
        cursor: pageParam ?? params.cursor,
        limit: pageSize,
      }),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? null,
    getPreviousPageParam: (lastPage) => lastPage.prev_cursor ?? null,
    enabled,
    refetchInterval,
    staleTime: 5000,
  });
}

// =============================================================================
// Live Tail Hook
// =============================================================================

export interface UseLogTailOptions {
  /** Number of entries per poll */
  batchSize?: number;
  /** Polling interval (ms) */
  pollInterval?: number;
  /** Max buffered entries to retain */
  bufferLimit?: number;
  /** Whether to start polling */
  enabled?: boolean;
  /** Optional error callback */
  onError?: (error: unknown) => void;
}

export interface UseLogTailResult {
  /** Buffered entries since the last drain */
  buffer: LogEntry[];
  /** Latest cursor returned by the server */
  cursor?: string;
  /** Last error encountered */
  error: unknown;
  /** Whether the tail loop is active */
  isRunning: boolean;
  /** Drain and clear the buffer */
  drain: () => LogEntry[];
  /** Reset buffer and cursor to the initial state */
  reset: () => void;
}

/**
 * Polls the log endpoint for new entries and buffers results in batches.
 */
export function useLogTail(
  params: LogQueryParams = {},
  options?: UseLogTailOptions
): UseLogTailResult {
  const {
    batchSize = 200,
    pollInterval = 2000,
    bufferLimit = 2000,
    enabled = true,
    onError,
  } = options ?? {};

  const [buffer, setBuffer] = useState<LogEntry[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [isRunning, setIsRunning] = useState(false);
  const cursorRef = useRef<string | undefined>(params.cursor);
  const bufferRef = useRef<LogEntry[]>([]);

  const serializedParams = useMemo(
    () => JSON.stringify({ ...params, cursor: undefined }),
    [params]
  );
  const baseParams = useMemo(
    () => ({ ...params, cursor: undefined }),
    [serializedParams]
  );

  const drain = useCallback(() => {
    const batch = bufferRef.current;
    bufferRef.current = [];
    setBuffer([]);
    return batch;
  }, []);

  const reset = useCallback(() => {
    bufferRef.current = [];
    setBuffer([]);
    cursorRef.current = params.cursor;
    setError(null);
  }, [params.cursor]);

  useEffect(() => {
    // Reset buffer when filters change
    bufferRef.current = [];
    setBuffer([]);
    cursorRef.current = params.cursor;
  }, [serializedParams, params.cursor]);

  useEffect(() => {
    if (!enabled) {
      setIsRunning(false);
      return;
    }

    let cancelled = false;
    let timerId: number | undefined;

    setIsRunning(true);
    setError(null);

    const poll = async () => {
      try {
        const response = await fetchLogs({
          ...baseParams,
          cursor: cursorRef.current,
          limit: batchSize,
          direction: "forward",
        });

        if (cancelled) return;

        if (response.next_cursor) {
          cursorRef.current = response.next_cursor;
        }

        if (response.entries?.length) {
          bufferRef.current = [...bufferRef.current, ...response.entries];
          if (bufferRef.current.length > bufferLimit) {
            bufferRef.current = bufferRef.current.slice(
              bufferRef.current.length - bufferLimit
            );
          }
          setBuffer(bufferRef.current);
        }
      } catch (err) {
        if (cancelled) return;
        setError(err);
        onError?.(err);
      } finally {
        if (!cancelled) {
          timerId = window.setTimeout(poll, pollInterval);
        }
      }
    };

    timerId = window.setTimeout(poll, 0);

    return () => {
      cancelled = true;
      if (timerId) {
        window.clearTimeout(timerId);
      }
      setIsRunning(false);
    };
  }, [
    baseParams,
    batchSize,
    bufferLimit,
    enabled,
    onError,
    pollInterval,
    serializedParams,
  ]);

  return {
    buffer,
    cursor: cursorRef.current,
    error,
    isRunning,
    drain,
    reset,
  };
}
