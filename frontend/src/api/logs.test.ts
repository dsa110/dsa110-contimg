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

  it("applies buffer limit and drops oldest entries", async () => {
    const batches: LogSearchResponse[] = [
      {
        entries: [
          { timestamp: "2024-01-01T00:00:00Z", level: "info", message: "first", cursor: "c1" },
        ],
        next_cursor: "c1",
      },
      {
        entries: [
          { timestamp: "2024-01-01T00:00:05Z", level: "info", message: "second", cursor: "c2" },
        ],
        next_cursor: "c2",
      },
      {
        entries: [
          { timestamp: "2024-01-01T00:00:10Z", level: "error", message: "third", cursor: "c3" },
        ],
        next_cursor: "c3",
      },
    ];

    mockedClient.get
      .mockResolvedValueOnce({ data: batches[0] })
      .mockResolvedValueOnce({ data: batches[1] })
      .mockResolvedValueOnce({ data: batches[2] });

    const { result, unmount } = renderHook(() =>
      useLogTail({ labels: { service: "api" } }, { pollInterval: 10, batchSize: 1, bufferLimit: 2 })
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

    expect(result.current.buffer.map((e) => e.message)).toEqual(["second", "third"]);
    unmount();
  });

  it("captures tail errors and invokes onError", async () => {
    const tailError = new Error("tail failed");
    mockedClient.get.mockRejectedValueOnce(tailError);
    mockedClient.get.mockResolvedValueOnce({ data: { entries: [], next_cursor: null } });
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
