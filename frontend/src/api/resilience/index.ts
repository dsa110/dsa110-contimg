/**
 * API Resilience Module
 *
 * Provides retry logic and circuit breaker functionality
 * for robust API communication.
 */

// Types
export type { RetryConfig, CircuitState, CircuitBreakerState, CircuitBreakerConfig } from "./types";

export { DEFAULT_RETRY_CONFIG, DEFAULT_CIRCUIT_BREAKER_CONFIG } from "./types";

// Circuit breaker
export {
  canMakeRequest,
  recordSuccess,
  recordFailure,
  getCircuitBreakerState,
  resetCircuitBreaker,
  configureCircuitBreaker,
  isCircuitOpen,
} from "./circuit-breaker";

// Retry utilities
export { sleep, calculateBackoffDelay, isRetryable, withRetry, noRetry } from "./retry";
