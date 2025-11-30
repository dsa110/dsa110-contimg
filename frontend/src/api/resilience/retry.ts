/**
 * Retry logic for API requests.
 *
 * Implements exponential backoff with jitter to handle
 * transient failures gracefully.
 */

import type { AxiosError, AxiosRequestConfig } from "axios";
import type { RetryConfig } from "./types";
import { DEFAULT_RETRY_CONFIG } from "./types";

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Sleep for a given number of milliseconds.
 *
 * @param ms Milliseconds to sleep
 * @returns Promise that resolves after the delay
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Calculate delay for a given attempt using exponential backoff with jitter.
 *
 * @param attempt Zero-based attempt number
 * @param config Retry configuration
 * @returns Delay in milliseconds
 */
export function calculateBackoffDelay(attempt: number, config: RetryConfig): number {
  const exponentialDelay = config.initialDelayMs * Math.pow(config.backoffMultiplier, attempt);
  const cappedDelay = Math.min(exponentialDelay, config.maxDelayMs);
  // Add jitter (±25%) to prevent thundering herd
  const jitter = cappedDelay * 0.25 * (Math.random() * 2 - 1);
  return Math.round(cappedDelay + jitter);
}

/**
 * Check if an error is retryable based on configuration.
 *
 * @param error Axios error to check
 * @param config Retry configuration
 * @returns true if the request should be retried
 */
export function isRetryable(error: AxiosError, config: RetryConfig): boolean {
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

// =============================================================================
// Request Config Helpers
// =============================================================================

/**
 * Create request config with custom retry settings.
 *
 * @param config Base request config
 * @param retryConfig Custom retry configuration
 * @returns Request config with retry settings attached
 */
export function withRetry(
  config: AxiosRequestConfig = {},
  retryConfig?: Partial<RetryConfig>
): AxiosRequestConfig {
  return {
    ...config,
    __retryConfig: { ...DEFAULT_RETRY_CONFIG, ...retryConfig },
  } as AxiosRequestConfig;
}

/**
 * Create request config that disables retry.
 * Useful for non-idempotent operations like DELETE.
 *
 * @param config Base request config
 * @returns Request config with retry disabled
 */
export function noRetry(config: AxiosRequestConfig = {}): AxiosRequestConfig {
  return {
    ...config,
    __retryConfig: { ...DEFAULT_RETRY_CONFIG, maxRetries: 0 },
  } as AxiosRequestConfig;
}

// Re-export default config
export { DEFAULT_RETRY_CONFIG };
