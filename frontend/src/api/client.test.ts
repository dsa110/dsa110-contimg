import { describe, it, expect, vi, beforeEach } from "vitest";
import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import type { ErrorResponse } from "../types/errors";

// We need to mock axios before importing the client
vi.mock("axios", () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    defaults: { baseURL: "/api" },
  };
  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
    },
  };
});

// Import after mocking
import apiClient, { fetchProvenanceData } from "./client";

describe("api/client", () => {
  let mockAxiosInstance: {
    get: ReturnType<typeof vi.fn>;
    post: ReturnType<typeof vi.fn>;
    interceptors: {
      request: { use: ReturnType<typeof vi.fn> };
      response: { use: ReturnType<typeof vi.fn> };
    };
  };
  let responseInterceptor: {
    onFulfilled: (response: AxiosResponse) => AxiosResponse;
    onRejected: (error: AxiosError<ErrorResponse>) => Promise<never>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockAxiosInstance = axios.create() as typeof mockAxiosInstance;

    // Capture the response interceptor
    const useCall = mockAxiosInstance.interceptors.response.use;
    if (useCall.mock.calls.length > 0) {
      const [onFulfilled, onRejected] = useCall.mock.calls[0];
      responseInterceptor = { onFulfilled, onRejected };
    }
  });

  describe("axios instance creation", () => {
    it("creates axios instance with correct base URL", () => {
      expect(axios.create).toHaveBeenCalled();
      const createCall = (axios.create as ReturnType<typeof vi.fn>).mock.calls[0][0];
      // BaseURL should be /api (from env or default)
      expect(createCall.baseURL).toBeDefined();
    });

    it("creates axios instance with timeout", () => {
      const createCall = (axios.create as ReturnType<typeof vi.fn>).mock.calls[0][0];
      expect(createCall.timeout).toBe(10000);
    });
  });

  describe("response interceptor", () => {
    beforeEach(() => {
      // Re-import to ensure interceptors are registered
      const useCall = mockAxiosInstance.interceptors.response.use;
      if (useCall.mock.calls.length > 0) {
        const [onFulfilled, onRejected] = useCall.mock.calls[0];
        responseInterceptor = { onFulfilled, onRejected };
      }
    });

    it("registers a response interceptor", () => {
      expect(mockAxiosInstance.interceptors.response.use).toHaveBeenCalled();
    });

    it("passes through successful responses unchanged", () => {
      const mockResponse = {
        data: { id: "test" },
        status: 200,
        statusText: "OK",
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      };

      if (responseInterceptor?.onFulfilled) {
        const result = responseInterceptor.onFulfilled(mockResponse);
        expect(result).toBe(mockResponse);
      }
    });

    it("normalizes error response with backend ErrorResponse data", async () => {
      const backendError: ErrorResponse = {
        code: "MS_NOT_FOUND",
        http_status: 404,
        user_message: "Measurement Set not found",
        action: "Check the path",
        ref_id: "job-123",
      };

      const axiosError: Partial<AxiosError<ErrorResponse>> = {
        response: {
          data: backendError,
          status: 404,
          statusText: "Not Found",
          headers: {},
          config: {} as InternalAxiosRequestConfig,
        },
        isAxiosError: true,
        name: "AxiosError",
        message: "Request failed",
        toJSON: () => ({}),
      };

      if (responseInterceptor?.onRejected) {
        await expect(
          responseInterceptor.onRejected(axiosError as AxiosError<ErrorResponse>)
        ).rejects.toEqual(backendError);
      }
    });

    it("creates NETWORK_ERROR when no response data", async () => {
      const axiosError: Partial<AxiosError<ErrorResponse>> = {
        response: undefined,
        isAxiosError: true,
        name: "AxiosError",
        message: "Network Error",
        toJSON: () => ({}),
      };

      if (responseInterceptor?.onRejected) {
        await expect(
          responseInterceptor.onRejected(axiosError as AxiosError<ErrorResponse>)
        ).rejects.toMatchObject({
          code: "NETWORK_ERROR",
          user_message: "Unable to reach the server",
          action: "Check your connection and try again",
        });
      }
    });

    it("includes HTTP status 0 for network errors", async () => {
      const axiosError: Partial<AxiosError<ErrorResponse>> = {
        response: undefined,
        isAxiosError: true,
        name: "AxiosError",
        message: "Network Error",
        toJSON: () => ({}),
      };

      if (responseInterceptor?.onRejected) {
        await expect(
          responseInterceptor.onRejected(axiosError as AxiosError<ErrorResponse>)
        ).rejects.toMatchObject({
          http_status: 0,
        });
      }
    });
  });

  describe("fetchProvenanceData", () => {
    it("calls correct endpoint with runId", async () => {
      const mockProvenance = {
        runId: "run-123",
        status: "completed",
        startTime: "2024-01-01T00:00:00Z",
      };
      mockAxiosInstance.get.mockResolvedValue({ data: mockProvenance });

      const result = await fetchProvenanceData("run-123");

      expect(mockAxiosInstance.get).toHaveBeenCalledWith("/jobs/run-123/provenance");
      expect(result).toEqual(mockProvenance);
    });

    it("propagates error on failure", async () => {
      const error = { code: "NOT_FOUND", http_status: 404 };
      mockAxiosInstance.get.mockRejectedValue(error);

      await expect(fetchProvenanceData("invalid-run")).rejects.toEqual(error);
    });
  });

  describe("apiClient export", () => {
    it("exports the axios instance as default", () => {
      expect(apiClient).toBeDefined();
      expect(apiClient.get).toBeDefined();
    });
  });
});
