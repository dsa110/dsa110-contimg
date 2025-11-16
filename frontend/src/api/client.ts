/**
 * API client configuration for DSA-110 pipeline backend.
 */
import axios, { AxiosError } from "axios";
import type { InternalAxiosRequestConfig } from "axios";
import { logger } from "../utils/logger";
import { classifyError, getUserFriendlyMessage } from "../utils/errorUtils";
import { createCircuitBreaker } from "./circuitBreaker";

// API base URL configuration
// - If VITE_API_URL is explicitly set, use it (e.g., "http://localhost:8000/api")
// - When served from /ui, use origin + /api (e.g., "http://localhost:8000/api")
// - Otherwise use relative /api for Vite proxy
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  (typeof window !== "undefined" && window.location.pathname.startsWith("/ui")
    ? `${window.location.origin}/api`
    : "/api");

// Create circuit breaker for API calls
const circuitBreaker = createCircuitBreaker({
  failureThreshold: 5,
  resetTimeout: 30000, // 30 seconds
  monitoringPeriod: 60000, // 1 minute
});

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 120 seconds - increased for slow cold-start requests
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor: Check circuit breaker
apiClient.interceptors.request.use(
  (config) => {
    if (!circuitBreaker.canAttempt()) {
      const error = new Error("Service temporarily unavailable. Please try again later.");
      (error as { isCircuitBreakerOpen?: boolean }).isCircuitBreakerOpen = true;
      return Promise.reject(error);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: Handle errors with retry and circuit breaker
apiClient.interceptors.response.use(
  (response) => {
    // Record success for circuit breaker
    circuitBreaker.recordSuccess();
    return response;
  },
  async (error: AxiosError) => {
    const classified = classifyError(error);

    logger.apiError("API request failed", error);

    // Record failure for circuit breaker if retryable
    if (classified.retryable) {
      circuitBreaker.recordFailure();
    }

    // Add user-friendly message to error
    const userMessage = getUserFriendlyMessage(error);
    (error as { userMessage?: string }).userMessage = userMessage;
    (error as { errorType?: string }).errorType = classified.type;

    // Retry logic for retryable errors
    // Check if error.config exists (it may be undefined for non-Axios errors)
    if (!error.config) {
      return Promise.reject(error);
    }

    const config = error.config as InternalAxiosRequestConfig & {
      _retryCount?: number;
    };
    const retryCount = config._retryCount || 0;
    const maxRetries = 3;

    if (classified.retryable && retryCount < maxRetries && circuitBreaker.canAttempt()) {
      config._retryCount = retryCount + 1;

      // Exponential backoff: 1s, 2s, 4s
      const delay = Math.min(1000 * Math.pow(2, retryCount), 10000);

      await new Promise((resolve) => setTimeout(resolve, delay));

      try {
        return await apiClient.request(config);
      } catch (retryError) {
        // If retry also fails, fall through to reject
        return Promise.reject(retryError);
      }
    }

    return Promise.reject(error);
  }
);

// Export circuit breaker for monitoring
export { circuitBreaker };
