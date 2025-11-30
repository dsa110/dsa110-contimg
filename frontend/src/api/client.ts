import axios, { AxiosError, AxiosRequestConfig, InternalAxiosRequestConfig } from "axios";
import type { ProvenanceStripProps } from "../types/provenance";
import type { ErrorResponse } from "../types/errors";

// =============================================================================
// Retry Configuration
// =============================================================================

export interface RetryConfig {
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Initial delay in ms before first retry */
  initialDelayMs: number;
  /** Maximum delay in ms between retries */
  maxDelayMs: number;
  /** Multiplier for exponential backoff */
  backoffMultiplier: number;
  /** HTTP status codes that should trigger a retry */
  retryableStatuses: number[];
  /** Whether to retry on network errors */
  retryOnNetworkError: boolean;
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  initialDelayMs: 500,
  maxDelayMs: 5000,
  backoffMultiplier: 2,
  retryableStatuses: [408, 429, 500, 502, 503, 504],
  retryOnNetworkError: true,
};

// =============================================================================
// Circuit Breaker
// =============================================================================

interface CircuitBreakerState {
  failures: number;
  lastFailureTime: number | null;
  state: "closed" | "open" | "half-open";
}

const CIRCUIT_BREAKER_CONFIG = {
  /** Number of failures before opening circuit */
  failureThreshold: 5,
  /** Time in ms before attempting to close circuit */
  resetTimeout: 30000,
  /** Number of successful requests needed to close circuit in half-open state */
  successThreshold: 2,
};

let circuitBreaker: CircuitBreakerState = {
  failures: 0,
  lastFailureTime: null,
  state: "closed",
};

let halfOpenSuccesses = 0;

/**
 * Check if circuit breaker allows request
 */
function canMakeRequest(): boolean {
  const now = Date.now();

  switch (circuitBreaker.state) {
    case "closed":
      return true;

    case "open":
      // Check if reset timeout has passed
      if (
        circuitBreaker.lastFailureTime &&
        now - circuitBreaker.lastFailureTime >= CIRCUIT_BREAKER_CONFIG.resetTimeout
      ) {
        circuitBreaker.state = "half-open";
        halfOpenSuccesses = 0;
        return true;
      }
      return false;

    case "half-open":
      return true;

    default:
      return true;
  }
}

/**
 * Record a successful request
 */
function recordSuccess(): void {
  if (circuitBreaker.state === "half-open") {
    halfOpenSuccesses++;
    if (halfOpenSuccesses >= CIRCUIT_BREAKER_CONFIG.successThreshold) {
      circuitBreaker = { failures: 0, lastFailureTime: null, state: "closed" };
    }
  } else if (circuitBreaker.state === "closed") {
    // Reset failure count on success
    circuitBreaker.failures = 0;
  }
}

/**
 * Record a failed request
 */
function recordFailure(): void {
  circuitBreaker.failures++;
  circuitBreaker.lastFailureTime = Date.now();

  if (circuitBreaker.state === "half-open") {
    circuitBreaker.state = "open";
  } else if (circuitBreaker.failures >= CIRCUIT_BREAKER_CONFIG.failureThreshold) {
    circuitBreaker.state = "open";
  }
}

/**
 * Get current circuit breaker state (for monitoring)
 */
export function getCircuitBreakerState(): CircuitBreakerState {
  return { ...circuitBreaker };
}

/**
 * Reset circuit breaker (for testing or manual reset)
 */
export function resetCircuitBreaker(): void {
  circuitBreaker = { failures: 0, lastFailureTime: null, state: "closed" };
  halfOpenSuccesses = 0;
}

// =============================================================================
// Retry Logic
// =============================================================================

/**
 * Calculate delay for a given attempt using exponential backoff with jitter
 */
function calculateBackoffDelay(attempt: number, config: RetryConfig): number {
  const exponentialDelay = config.initialDelayMs * Math.pow(config.backoffMultiplier, attempt);
  const cappedDelay = Math.min(exponentialDelay, config.maxDelayMs);
  // Add jitter (±25%) to prevent thundering herd
  const jitter = cappedDelay * 0.25 * (Math.random() * 2 - 1);
  return Math.round(cappedDelay + jitter);
}

/**
 * Sleep for a given number of milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Check if an error is retryable
 */
function isRetryable(error: AxiosError, config: RetryConfig): boolean {
  // Network errors (no response)
  if (!error.response && config.retryOnNetworkError) {
    return true;
  }

  // Check status code
  if (error.response && config.retryableStatuses.includes(error.response.status)) {
    return true;
  }

  // Timeout errors
  if (error.code === "ECONNABORTED") {
    return true;
  }

  return false;
}

// Extend AxiosRequestConfig to track retry state
interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  __retryCount?: number;
  __retryConfig?: RetryConfig;
}

// =============================================================================
// API Client
// =============================================================================

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
  timeout: 10000,
});

/**
 * Request interceptor to check circuit breaker
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (!canMakeRequest()) {
      const error = new Error("Circuit breaker is open - API temporarily unavailable");
      (error as any).code = "CIRCUIT_OPEN";
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
      console.debug(
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

  if ("code" in error && (error as any).code === "CIRCUIT_OPEN") {
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
export function withRetry(config: AxiosRequestConfig, retryConfig?: Partial<RetryConfig>): AxiosRequestConfig {
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

export { DEFAULT_RETRY_CONFIG };
export default apiClient;
