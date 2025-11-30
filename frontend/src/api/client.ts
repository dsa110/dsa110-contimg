/**
 * Axios API client with resilience features.
 *
 * Features:
 * - Circuit breaker to prevent cascading failures
 * - Automatic retry with exponential backoff
 * - Error normalization to standard ErrorResponse shape
 */

import axios, { AxiosError, AxiosRequestConfig, InternalAxiosRequestConfig } from "axios";
import type { ProvenanceStripProps } from "../types/provenance";
import type { ErrorResponse } from "../types/errors";
import { config } from "../config";
import { logger } from "../utils/logger";
import {
  canMakeRequest,
  recordSuccess,
  recordFailure,
  isRetryable,
  calculateBackoffDelay,
  sleep,
  DEFAULT_RETRY_CONFIG,
  type RetryConfig,
} from "./resilience";

// =============================================================================
// Types
// =============================================================================

/**
 * Extended request config to track retry state.
 */
interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  __retryCount?: number;
  __retryConfig?: RetryConfig;
}

// =============================================================================
// API Client Instance
// =============================================================================

const apiClient = axios.create({
  baseURL: config.api.baseUrl,
  timeout: config.api.timeout,
});

/**
 * Request interceptor to check circuit breaker.
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (!canMakeRequest()) {
      const error = new Error("Circuit breaker is open - API temporarily unavailable");
      (error as Error & { code: string }).code = "CIRCUIT_OPEN";
      return Promise.reject(error);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

/**
 * Response interceptor with retry logic and error normalization
 */
apiClient.interceptors.response.use(
  (response) => {
    recordSuccess();
    return response;
  },
  async (error: AxiosError<ErrorResponse>) => {
    const config = error.config as RetryableRequestConfig | undefined;

    if (!config) {
      recordFailure();
      return Promise.reject(normalizeError(error));
    }

    // Initialize retry state
    config.__retryCount = config.__retryCount ?? 0;
    config.__retryConfig = config.__retryConfig ?? DEFAULT_RETRY_CONFIG;

    const retryConfig = config.__retryConfig;

    // Check if we should retry
    if (config.__retryCount < retryConfig.maxRetries && isRetryable(error, retryConfig)) {
      config.__retryCount++;

      const delay = calculateBackoffDelay(config.__retryCount - 1, retryConfig);
      logger.debug(
        `API retry ${config.__retryCount}/${retryConfig.maxRetries} for ${config.url} after ${delay}ms`
      );

      await sleep(delay);

      // Check circuit breaker again before retry
      if (!canMakeRequest()) {
        recordFailure();
        return Promise.reject(normalizeError(error));
      }

      return apiClient.request(config);
    }

    // No more retries - record failure and reject
    recordFailure();
    return Promise.reject(normalizeError(error));
  }
);

/**
 * Normalize error to standard ErrorResponse shape
 */
function normalizeError(error: AxiosError<ErrorResponse> | Error): Partial<ErrorResponse> {
  if ("response" in error && error.response?.data) {
    return error.response.data;
  }

  if ("code" in error && (error as Error & { code?: string }).code === "CIRCUIT_OPEN") {
    return {
      code: "CIRCUIT_OPEN",
      http_status: 503,
      user_message: "The API is temporarily unavailable",
      action: "Please wait a moment and try again",
      ref_id: "",
    };
  }

  return {
    code: "NETWORK_ERROR",
    http_status: 0,
    user_message: "Unable to reach the server",
    action: "Check your connection and try again",
    ref_id: "",
  };
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Create request config with custom retry settings
 */
export function withRetry(
  config: AxiosRequestConfig,
  retryConfig?: Partial<RetryConfig>
): AxiosRequestConfig {
  return {
    ...config,
    __retryConfig: { ...DEFAULT_RETRY_CONFIG, ...retryConfig },
  } as AxiosRequestConfig;
}

/**
 * Create request config that disables retry
 */
export function noRetry(config: AxiosRequestConfig = {}): AxiosRequestConfig {
  return {
    ...config,
    __retryConfig: { ...DEFAULT_RETRY_CONFIG, maxRetries: 0 },
  } as AxiosRequestConfig;
}

/**
 * Fetch provenance data for a given run/job ID.
 * Used by the ProvenanceStrip component to display pipeline context.
 */
export const fetchProvenanceData = async (runId: string): Promise<ProvenanceStripProps> => {
  const response = await apiClient.get<ProvenanceStripProps>(`/jobs/${runId}/provenance`);
  return response.data;
};

// Re-export resilience utilities for convenience
export { DEFAULT_RETRY_CONFIG } from "./resilience";
export { getCircuitBreakerState, resetCircuitBreaker } from "./resilience";
export type { RetryConfig } from "./resilience";

export default apiClient;
