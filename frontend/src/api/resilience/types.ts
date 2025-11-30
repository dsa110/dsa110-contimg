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
 */
export const DEFAULT_CIRCUIT_BREAKER_CONFIG: CircuitBreakerConfig = {
  failureThreshold: 5,
  resetTimeout: 30000,
  successThreshold: 2,
};
