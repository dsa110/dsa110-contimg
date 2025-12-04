/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { LogEntry, LogSearchResponse } from "@/types/logs";
import { buildLogQueryParams, fetchLogs, useLogTail } from "./logs";

vi.mock("./client", () => ({
  default: {
    get: vi.fn(),
  },
}));

import apiClient from "./client";

const mockedClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>;
};

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

    expect(mockedClient.get).toHaveBeenCalledWith("/v1/logs/search", {
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
      useLogTail({ labels: { service: "api" } }, { pollInterval: 10, batchSize: 1 })
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
});
