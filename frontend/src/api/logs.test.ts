/**
 * @vitest-environment jsdom
 */

import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import type { LogEntry, LogSearchResponse } from "@/types/logs";
import {
  buildLogQueryParams,
  fetchLogs,
  useLogs,
  useLogTail,
  logKeys,
} from "./logs";

vi.mock("./client", () => ({
  default: {
    get: vi.fn(),
  },
}));

import apiClient from "./client";

const mockedClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>;
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
  return function TestWrapper({ children }: { children: ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children
    );
  };
}

describe("logs API helpers", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockedClient.get.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("builds query params with search, level array, labels, and range", () => {
    const params = buildLogQueryParams({
      q: "error OR timeout",
      level: ["error", "warning"],
      labels: { service: "scheduler", run_id: ["run-1", "run-2"], attempt: 2 },
      range: {
        start: new Date("2024-01-01T00:00:00Z"),
        end: "2024-01-02T00:00:00Z",
      },
      cursor: "next-123",
      limit: 500,
      direction: "forward",
    });

    expect(params).toMatchObject({
      q: "error OR timeout",
      level: "error,warning",
      "labels.service": "scheduler",
      "labels.run_id": "run-1,run-2",
      "labels.attempt": "2",
      start: "2024-01-01T00:00:00.000Z",
      end: "2024-01-02T00:00:00Z",
      cursor: "next-123",
      limit: 500,
      direction: "forward",
    });
  });

  it("calls the search endpoint with built params", async () => {
    const mockResponse: LogSearchResponse = {
      entries: [],
      next_cursor: null,
      prev_cursor: null,
      has_more: false,
    };

    mockedClient.get.mockResolvedValue({ data: mockResponse });

    const result = await fetchLogs({ q: "timeout" });

    expect(mockedClient.get).toHaveBeenCalledWith("/logs/search", {
      params: { q: "timeout" },
    });
    expect(result).toEqual(mockResponse);
  });

  it("tails logs and buffers batches", async () => {
    const firstBatch: LogSearchResponse = {
      entries: [
        {
          timestamp: "2024-01-01T00:00:00Z",
          level: "info",
          message: "Started",
          cursor: "c1",
        },
      ],
      next_cursor: "c1",
    };
    const secondBatch: LogSearchResponse = {
      entries: [
        {
          timestamp: "2024-01-01T00:00:05Z",
          level: "error",
          message: "Failed",
          cursor: "c2",
        },
      ],
      next_cursor: "c2",
    };

    mockedClient.get
      .mockResolvedValueOnce({ data: firstBatch })
      .mockResolvedValueOnce({ data: secondBatch });

    const { result, unmount } = renderHook(() =>
      useLogTail(
        { labels: { service: "api" } },
        { pollInterval: 10, batchSize: 1 }
      )
    );

    // First poll
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(result.current.buffer).toHaveLength(1);
    expect(result.current.cursor).toBe("c1");

    // Second poll
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });

    expect(result.current.buffer).toHaveLength(2);
    expect(result.current.cursor).toBe("c2");

    // Drain clears the buffer
    let drained: LogEntry[] = [];
    await act(async () => {
      drained = result.current.drain();
    });
    expect(drained).toHaveLength(2);
    expect(result.current.buffer).toHaveLength(0);

    unmount();
  });

  it("applies buffer limit and drops oldest entries", async () => {
    const batches: LogSearchResponse[] = [
      {
        entries: [
          {
            timestamp: "2024-01-01T00:00:00Z",
            level: "info",
            message: "first",
            cursor: "c1",
          },
        ],
        next_cursor: "c1",
      },
      {
        entries: [
          {
            timestamp: "2024-01-01T00:00:05Z",
            level: "info",
            message: "second",
            cursor: "c2",
          },
        ],
        next_cursor: "c2",
      },
      {
        entries: [
          {
            timestamp: "2024-01-01T00:00:10Z",
            level: "error",
            message: "third",
            cursor: "c3",
          },
        ],
        next_cursor: "c3",
      },
    ];

    mockedClient.get
      .mockResolvedValueOnce({ data: batches[0] })
      .mockResolvedValueOnce({ data: batches[1] })
      .mockResolvedValueOnce({ data: batches[2] });

    const { result, unmount } = renderHook(() =>
      useLogTail(
        { labels: { service: "api" } },
        { pollInterval: 10, batchSize: 1, bufferLimit: 2 }
      )
    );

    // first poll
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    // second poll
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    // third poll
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });

    expect(result.current.buffer.map((e) => e.message)).toEqual([
      "second",
      "third",
    ]);
    unmount();
  });

  it("captures tail errors and invokes onError", async () => {
    const tailError = new Error("tail failed");
    mockedClient.get.mockRejectedValueOnce(tailError);
    mockedClient.get.mockResolvedValueOnce({
      data: { entries: [], next_cursor: null },
    });
    const onError = vi.fn();

    const { result, unmount } = renderHook(() =>
      useLogTail({ q: "test" }, { pollInterval: 10, onError })
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(onError).toHaveBeenCalledWith(tailError);
    expect(result.current.error).toBe(tailError);

    // allow a follow-up poll to ensure it keeps running
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    expect(result.current.isRunning).toBe(true);
    unmount();
  });
});

describe("useLogs pagination hook", () => {
  beforeEach(() => {
    // Note: using real timers here since React Query's waitFor needs them
    mockedClient.get.mockReset();
  });

  it("fetches initial page and provides hasNextPage when cursor present", async () => {
    const firstPage: LogSearchResponse = {
      entries: [
        {
          timestamp: "2024-01-01T00:00:00Z",
          level: "info",
          message: "page1",
          cursor: "c1",
        },
        {
          timestamp: "2024-01-01T00:00:01Z",
          level: "debug",
          message: "page1-2",
          cursor: "c2",
        },
      ],
      next_cursor: "c2",
      prev_cursor: null,
      has_more: true,
    };

    mockedClient.get.mockResolvedValueOnce({ data: firstPage });

    const { result } = renderHook(
      () => useLogs({ labels: { service: "api" } }, { pageSize: 2 }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.pages).toHaveLength(1);
    expect(result.current.data?.pages[0].entries).toHaveLength(2);
    expect(result.current.hasNextPage).toBe(true);
    expect(mockedClient.get).toHaveBeenCalledWith("/logs/search", {
      params: { "labels.service": "api", limit: 2 },
    });
  });

  it("fetches next page when fetchNextPage called", async () => {
    const firstPage: LogSearchResponse = {
      entries: [
        {
          timestamp: "2024-01-01T00:00:00Z",
          level: "info",
          message: "page1",
          cursor: "c1",
        },
      ],
      next_cursor: "c1",
      prev_cursor: null,
      has_more: true,
    };
    const secondPage: LogSearchResponse = {
      entries: [
        {
          timestamp: "2024-01-01T00:00:05Z",
          level: "error",
          message: "page2",
          cursor: "c2",
        },
      ],
      next_cursor: null,
      prev_cursor: "c1",
      has_more: false,
    };

    mockedClient.get
      .mockResolvedValueOnce({ data: firstPage })
      .mockResolvedValueOnce({ data: secondPage });

    const { result } = renderHook(() => useLogs({}, { pageSize: 1 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.pages).toHaveLength(1);

    await act(async () => {
      await result.current.fetchNextPage();
    });

    await waitFor(() => expect(result.current.data?.pages).toHaveLength(2));
    expect(result.current.hasNextPage).toBe(false);
    expect(result.current.data?.pages[1].entries[0].message).toBe("page2");
  });

  it("returns hasNextPage false when no next_cursor", async () => {
    const onlyPage: LogSearchResponse = {
      entries: [
        {
          timestamp: "2024-01-01T00:00:00Z",
          level: "info",
          message: "only",
          cursor: "c1",
        },
      ],
      next_cursor: null,
      prev_cursor: null,
      has_more: false,
    };

    mockedClient.get.mockResolvedValueOnce({ data: onlyPage });

    const { result } = renderHook(() => useLogs({ q: "only" }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.hasNextPage).toBe(false);
  });

  it("respects enabled option", async () => {
    const { result } = renderHook(() => useLogs({}, { enabled: false }), {
      wrapper: createWrapper(),
    });

    // Should not have called API
    expect(mockedClient.get).not.toHaveBeenCalled();
    expect(result.current.fetchStatus).toBe("idle");
  });

  it("generates consistent query keys", () => {
    const params = { q: "test", level: ["error", "warning"] };
    const key1 = logKeys.search(params, 100);
    const key2 = logKeys.search(params, 100);
    expect(key1).toEqual(key2);

    const differentKey = logKeys.search({ q: "other" }, 100);
    expect(key1).not.toEqual(differentKey);
  });
});

describe("useLogTail reconnection behavior", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockedClient.get.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("continues polling after transient errors", async () => {
    const errorResponse = new Error("network timeout");
    const successResponse: LogSearchResponse = {
      entries: [
        {
          timestamp: "2024-01-01T00:00:10Z",
          level: "info",
          message: "recovered",
          cursor: "c1",
        },
      ],
      next_cursor: "c1",
    };

    mockedClient.get
      .mockRejectedValueOnce(errorResponse)
      .mockRejectedValueOnce(errorResponse)
      .mockResolvedValueOnce({ data: successResponse });

    const onError = vi.fn();
    const { result, unmount } = renderHook(() =>
      useLogTail({}, { pollInterval: 10, onError })
    );

    // First poll - error
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(onError).toHaveBeenCalledTimes(1);
    expect(result.current.isRunning).toBe(true);

    // Second poll - error
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    expect(onError).toHaveBeenCalledTimes(2);
    expect(result.current.isRunning).toBe(true);

    // Third poll - success
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    expect(result.current.buffer).toHaveLength(1);
    expect(result.current.buffer[0].message).toBe("recovered");

    unmount();
  });

  it("resets cursor and buffer when params change", async () => {
    const batch1: LogSearchResponse = {
      entries: [
        {
          timestamp: "2024-01-01T00:00:00Z",
          level: "info",
          message: "svc-a",
          cursor: "c1",
        },
      ],
      next_cursor: "c1",
    };
    const batch2: LogSearchResponse = {
      entries: [
        {
          timestamp: "2024-01-01T00:00:05Z",
          level: "error",
          message: "svc-b",
          cursor: "c2",
        },
      ],
      next_cursor: "c2",
    };

    mockedClient.get
      .mockResolvedValueOnce({ data: batch1 })
      .mockResolvedValueOnce({ data: batch2 });

    const { result, rerender, unmount } = renderHook(
      ({ params }) => useLogTail(params, { pollInterval: 10 }),
      {
        initialProps: { params: { labels: { service: "svc-a" } } },
      }
    );

    // First poll for svc-a
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.buffer[0].message).toBe("svc-a");

    // Change params to svc-b - should reset buffer
    rerender({ params: { labels: { service: "svc-b" } } });

    // Wait for new poll cycle
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    // Buffer should have been reset and now contain svc-b entry
    expect(result.current.buffer.map((e) => e.message)).not.toContain("svc-a");

    unmount();
  });

  it("stops polling when disabled", async () => {
    const response: LogSearchResponse = {
      entries: [
        {
          timestamp: "2024-01-01T00:00:00Z",
          level: "info",
          message: "test",
          cursor: "c1",
        },
      ],
      next_cursor: "c1",
    };
    mockedClient.get.mockResolvedValue({ data: response });

    const { result, rerender, unmount } = renderHook(
      ({ enabled }) => useLogTail({}, { pollInterval: 10, enabled }),
      { initialProps: { enabled: true } }
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.isRunning).toBe(true);
    expect(mockedClient.get).toHaveBeenCalledTimes(1);

    // Disable
    rerender({ enabled: false });
    expect(result.current.isRunning).toBe(false);

    // Advance time - should not poll again
    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });
    expect(mockedClient.get).toHaveBeenCalledTimes(1);

    unmount();
  });

  it("reset() clears buffer and cursor", async () => {
    const response: LogSearchResponse = {
      entries: [
        {
          timestamp: "2024-01-01T00:00:00Z",
          level: "info",
          message: "test",
          cursor: "c1",
        },
      ],
      next_cursor: "c1",
    };
    mockedClient.get.mockResolvedValue({ data: response });

    const { result, unmount } = renderHook(() =>
      useLogTail({}, { pollInterval: 10 })
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.buffer).toHaveLength(1);
    expect(result.current.cursor).toBe("c1");

    await act(async () => {
      result.current.reset();
    });

    expect(result.current.buffer).toHaveLength(0);
    expect(result.current.error).toBeNull();

    unmount();
  });
});

describe("buildLogQueryParams edge cases", () => {
  it("handles empty params", () => {
    expect(buildLogQueryParams()).toEqual({});
    expect(buildLogQueryParams({})).toEqual({});
  });

  it("handles single level string", () => {
    expect(buildLogQueryParams({ level: "error" })).toEqual({ level: "error" });
  });

  it("filters out null/undefined label values", () => {
    const params = buildLogQueryParams({
      labels: {
        service: "api",
        run_id: null as unknown as string,
        attempt: undefined,
        valid: "yes",
      },
    });
    expect(params).toEqual({
      "labels.service": "api",
      "labels.valid": "yes",
    });
  });

  it("handles Date objects in range", () => {
    const start = new Date("2024-06-01T12:00:00Z");
    const params = buildLogQueryParams({ range: { start } });
    expect(params.start).toBe("2024-06-01T12:00:00.000Z");
  });

  it("handles numeric timestamp in range", () => {
    const params = buildLogQueryParams({ range: { start: 1717243200000 } });
    expect(params.start).toBe(1717243200000);
  });

  it("handles array labels with mixed values", () => {
    const params = buildLogQueryParams({
      labels: {
        tags: [
          "a",
          null as unknown as string,
          "b",
          undefined as unknown as string,
        ],
      },
    });
    expect(params["labels.tags"]).toBe("a,b");
  });
});
