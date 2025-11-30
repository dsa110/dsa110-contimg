/**
 * Circuit breaker implementation for API resilience.
 *
 * The circuit breaker prevents cascading failures by temporarily
 * stopping requests to a failing service.
 *
 * States:
 * - Closed: Normal operation, requests flow through
 * - Open: Service is failing, requests are blocked
 * - Half-Open: Testing if service has recovered
 */

import type { CircuitBreakerState, CircuitBreakerConfig } from "./types";
import { DEFAULT_CIRCUIT_BREAKER_CONFIG } from "./types";

// =============================================================================
// State
// =============================================================================

let circuitBreaker: CircuitBreakerState = {
  failures: 0,
  lastFailureTime: null,
  state: "closed",
};

let halfOpenSuccesses = 0;

const config: CircuitBreakerConfig = { ...DEFAULT_CIRCUIT_BREAKER_CONFIG };

// =============================================================================
// Public API
// =============================================================================

/**
 * Check if circuit breaker allows request to proceed.
 *
 * @returns true if request should proceed, false if blocked
 */
export function canMakeRequest(): boolean {
  const now = Date.now();

  switch (circuitBreaker.state) {
    case "closed":
      return true;

    case "open":
      // Check if reset timeout has passed
      if (
        circuitBreaker.lastFailureTime &&
        now - circuitBreaker.lastFailureTime >= config.resetTimeout
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
 * Record a successful request.
 * In half-open state, this may close the circuit.
 */
export function recordSuccess(): void {
  if (circuitBreaker.state === "half-open") {
    halfOpenSuccesses++;
    if (halfOpenSuccesses >= config.successThreshold) {
      circuitBreaker = { failures: 0, lastFailureTime: null, state: "closed" };
      halfOpenSuccesses = 0;
    }
  } else if (circuitBreaker.state === "closed") {
    // Reset failure count on success
    circuitBreaker.failures = 0;
  }
}

/**
 * Record a failed request.
 * May open the circuit if threshold is exceeded.
 */
export function recordFailure(): void {
  circuitBreaker.failures++;
  circuitBreaker.lastFailureTime = Date.now();

  if (circuitBreaker.state === "half-open") {
    // Any failure in half-open immediately opens circuit
    circuitBreaker.state = "open";
    halfOpenSuccesses = 0;
  } else if (circuitBreaker.failures >= config.failureThreshold) {
    circuitBreaker.state = "open";
  }
}

/**
 * Get current circuit breaker state (for monitoring/debugging).
 *
 * @returns Copy of current state
 */
export function getCircuitBreakerState(): CircuitBreakerState {
  return { ...circuitBreaker };
}

/**
 * Reset circuit breaker to initial state.
 * Useful for testing or manual recovery.
 */
export function resetCircuitBreaker(): void {
  circuitBreaker = { failures: 0, lastFailureTime: null, state: "closed" };
  halfOpenSuccesses = 0;
}

/**
 * Update circuit breaker configuration.
 *
 * @param newConfig Partial configuration to merge
 */
export function configureCircuitBreaker(newConfig: Partial<CircuitBreakerConfig>): void {
  Object.assign(config, newConfig);
}

/**
 * Check if circuit is currently open (blocking requests).
 *
 * @returns true if circuit is open
 */
export function isCircuitOpen(): boolean {
  return circuitBreaker.state === "open" && !canMakeRequest();
}
