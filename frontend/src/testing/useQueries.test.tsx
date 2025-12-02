import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useImages } from "../hooks/useQueries";
import apiClient from "../api/client";

vi.mock("../api/client", () => {
  const get = vi.fn();
  return {
    __esModule: true,
    default: {
      get,
      interceptors: { response: { use: vi.fn() } },
    },
  };
});

const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const client = new QueryClient();
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
};

// Type alias for mocked API client
type MockedApiClient = { get: ReturnType<typeof vi.fn> };

describe("useQueries hooks", () => {
  beforeEach(() => {
    (apiClient as unknown as MockedApiClient).get.mockReset();
  });

  it("fetches images with expected endpoint", async () => {
    const mockData = [
      {
        id: "img-1",
        path: "/data/img1.fits",
        qa_grade: "good",
        created_at: "",
      },
    ];
    (apiClient as unknown as MockedApiClient).get.mockResolvedValue({
      data: mockData,
    });

    const { result } = renderHook(() => useImages(), { wrapper });

    await waitFor(() => expect(result.current.data).toEqual(mockData));
    expect((apiClient as unknown as MockedApiClient).get).toHaveBeenCalledWith(
      "/images"
    );
  });
});
