/**
 * @vitest-environment jsdom
 */

import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import {
  useCARTAStatus,
  useCARTASessions,
  useOpenInCARTA,
  useCloseCARTASession,
  getCARTAViewerUrl,
  useCARTAViewerUrl,
  cartaKeys,
  type CARTAStatus,
  type CARTASession,
  type CARTAOpenResponse,
} from "./carta";

vi.mock("./client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

import apiClient from "./client";

const mockedClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
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

describe("cartaKeys", () => {
  it("generates correct query keys", () => {
    expect(cartaKeys.all).toEqual(["carta"]);
    expect(cartaKeys.status()).toEqual(["carta", "status"]);
    expect(cartaKeys.sessions()).toEqual(["carta", "sessions"]);
    expect(cartaKeys.session("session-123")).toEqual([
      "carta",
      "session",
      "session-123",
    ]);
  });
});

describe("getCARTAViewerUrl", () => {
  it("constructs URL with default base", () => {
    const url = getCARTAViewerUrl("/path/to/file.ms");
    expect(url).toBe("/carta?file=%2Fpath%2Fto%2Ffile.ms");
  });

  it("constructs URL with custom base", () => {
    const url = getCARTAViewerUrl("/path/to/file.fits", "http://carta.local");
    expect(url).toBe("http://carta.local?file=%2Fpath%2Fto%2Ffile.fits");
  });

  it("properly encodes special characters", () => {
    const url = getCARTAViewerUrl("/data/2025-01-01T12:30:00.ms");
    expect(url).toBe("/carta?file=%2Fdata%2F2025-01-01T12%3A30%3A00.ms");
  });
});

describe("useCARTAStatus", () => {
  beforeEach(() => {
    mockedClient.get.mockReset();
  });

  it("returns available status when API responds successfully", async () => {
    const mockStatus: CARTAStatus = {
      available: true,
      version: "4.0.0",
      url: "http://carta.local",
      sessions_active: 2,
      max_sessions: 10,
    };

    mockedClient.get.mockResolvedValue({ data: mockStatus });

    const { result } = renderHook(() => useCARTAStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockStatus);
    expect(mockedClient.get).toHaveBeenCalledWith("/carta/status");
  });

  it("returns unavailable status when API returns 404", async () => {
    mockedClient.get.mockRejectedValue({ response: { status: 404 } });

    const { result } = renderHook(() => useCARTAStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual({
      available: false,
      message: "CARTA server is not available",
    });
  });

  it("returns unavailable status on network error", async () => {
    mockedClient.get.mockRejectedValue(new Error("Network Error"));

    const { result } = renderHook(() => useCARTAStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.available).toBe(false);
  });
});

describe("useCARTASessions", () => {
  beforeEach(() => {
    mockedClient.get.mockReset();
  });

  it("fetches sessions list successfully", async () => {
    const mockSessions: CARTASession[] = [
      {
        id: "session-1",
        file_path: "/data/test.ms",
        file_type: "ms",
        created_at: "2025-01-01T12:00:00Z",
        last_activity: "2025-01-01T12:30:00Z",
        user: "testuser",
      },
      {
        id: "session-2",
        file_path: "/data/test.fits",
        file_type: "fits",
        created_at: "2025-01-01T11:00:00Z",
        last_activity: "2025-01-01T11:45:00Z",
      },
    ];

    mockedClient.get.mockResolvedValue({ data: mockSessions });

    const { result } = renderHook(() => useCARTASessions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockSessions);
    expect(mockedClient.get).toHaveBeenCalledWith("/carta/sessions");
  });

  it("handles empty sessions list", async () => {
    mockedClient.get.mockResolvedValue({ data: [] });

    const { result } = renderHook(() => useCARTASessions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual([]);
  });
});

describe("useOpenInCARTA", () => {
  beforeEach(() => {
    mockedClient.post.mockReset();
  });

  it("opens file in CARTA successfully", async () => {
    const mockResponse: CARTAOpenResponse = {
      success: true,
      session_id: "new-session-123",
      viewer_url: "http://carta.local?session=new-session-123",
    };

    mockedClient.post.mockResolvedValue({ data: mockResponse });

    const { result } = renderHook(() => useOpenInCARTA(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      file_path: "/data/test.ms",
      file_type: "ms",
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockResponse);
    expect(mockedClient.post).toHaveBeenCalledWith("/carta/open", {
      file_path: "/data/test.ms",
      file_type: "ms",
    });
  });

  it("handles open failure", async () => {
    mockedClient.post.mockRejectedValue(new Error("Failed to open file"));

    const { result } = renderHook(() => useOpenInCARTA(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      file_path: "/data/nonexistent.ms",
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });
});

describe("useCloseCARTASession", () => {
  beforeEach(() => {
    mockedClient.delete.mockReset();
  });

  it("closes session successfully", async () => {
    mockedClient.delete.mockResolvedValue({ data: {} });

    const { result } = renderHook(() => useCloseCARTASession(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("session-123");

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockedClient.delete).toHaveBeenCalledWith(
      "/carta/sessions/session-123"
    );
  });
});

describe("useCARTAViewerUrl", () => {
  beforeEach(() => {
    mockedClient.get.mockReset();
  });

  it("returns URL with availability status when CARTA is available", async () => {
    const mockStatus: CARTAStatus = {
      available: true,
      url: "http://carta.local",
    };

    mockedClient.get.mockResolvedValue({ data: mockStatus });

    const { result } = renderHook(() => useCARTAViewerUrl("/data/test.ms"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAvailable).toBe(true);
    expect(result.current.url).toBe(
      "http://carta.local?file=%2Fdata%2Ftest.ms"
    );
  });

  it("returns default URL when CARTA status has no URL", async () => {
    const mockStatus: CARTAStatus = {
      available: true,
    };

    mockedClient.get.mockResolvedValue({ data: mockStatus });

    const { result } = renderHook(() => useCARTAViewerUrl("/data/test.fits"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.url).toBe("/carta?file=%2Fdata%2Ftest.fits");
  });

  it("returns unavailable when CARTA is not running", async () => {
    mockedClient.get.mockRejectedValue(new Error("Network Error"));

    const { result } = renderHook(() => useCARTAViewerUrl("/data/test.ms"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAvailable).toBe(false);
  });
});
