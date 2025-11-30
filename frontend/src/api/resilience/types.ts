/**
 * Type definitions for API resilience features.
 */

/**
 * Configuration for retry behavior.
 */
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

/**
 * Possible states for the circuit breaker.
 */
export type CircuitState = "closed" | "open" | "half-open";

/**
 * Internal state of the circuit breaker.
 */
export interface CircuitBreakerState {
  /** Number of consecutive failures */
  failures: number;
  /** Timestamp of the last failure */
  lastFailureTime: number | null;
  /** Current circuit state */
  state: CircuitState;
}

/**
 * Configuration for circuit breaker behavior.
 */
export interface CircuitBreakerConfig {
  /** Number of failures before opening circuit */
  failureThreshold: number;
  /** Time in ms before attempting to close circuit */
  resetTimeout: number;
  /** Number of successful requests needed to close circuit in half-open state */
  successThreshold: number;
}

/**
 * Default retry configuration aligned with backend expectations.
 *
 * Rationale for values:
 * - maxRetries: 3 - Provides reasonable balance between persistence and UX
 * - initialDelayMs: 500ms - Quick enough for transient issues, not too aggressive
 * - maxDelayMs: 5000ms (5s) - Prevents indefinite waiting
 * - backoffMultiplier: 2 - Standard exponential backoff (500ms, 1s, 2s, 4s)
 * - retryableStatuses: Server errors and rate limits that may resolve on retry
 * - retryOnNetworkError: true - Network blips are common, worth retrying
 */
export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  initialDelayMs: 500,
  maxDelayMs: 5000,
  backoffMultiplier: 2,
  retryableStatuses: [408, 429, 500, 502, 503, 504],
  retryOnNetworkError: true,
};

/**
 * Default circuit breaker configuration.
 *
 * Rationale for values:
 * - failureThreshold: 5 - Enough to detect pattern, not too sensitive to noise
 * - resetTimeout: 30000ms (30s) - Allows backend time to recover from issues
 * - successThreshold: 2 - Requires multiple successes to confirm recovery
 */
export const DEFAULT_CIRCUIT_BREAKER_CONFIG: CircuitBreakerConfig = {
  failureThreshold: 5,
  resetTimeout: 30000,
  successThreshold: 2,
};
