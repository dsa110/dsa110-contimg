/**
 * Circuit breaker pattern implementation
 * Prevents cascading failures by stopping requests when service is down
 */

export interface CircuitBreakerOptions {
  failureThreshold?: number; // Number of failures before opening circuit
  resetTimeout?: number; // Time in ms before attempting to close circuit
  monitoringPeriod?: number; // Time window for counting failures
}

const DEFAULT_OPTIONS: Required<CircuitBreakerOptions> = {
  failureThreshold: 5,
  resetTimeout: 30000, // 30 seconds
  monitoringPeriod: 60000, // 1 minute
};

export const CircuitState = {
  CLOSED: "closed", // Normal operation
  OPEN: "open", // Circuit is open, failing fast
  HALF_OPEN: "half_open", // Testing if service recovered
} as const;

export type CircuitState = (typeof CircuitState)[keyof typeof CircuitState];

interface FailureRecord {
  timestamp: number;
}

export class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failures: FailureRecord[] = [];
  private lastFailureTime: number = 0;
  private options: Required<CircuitBreakerOptions>;

  constructor(options: CircuitBreakerOptions = {}) {
    this.options = { ...DEFAULT_OPTIONS, ...options };
  }

  /**
   * Record a successful request
   */
  recordSuccess(): void {
    if (this.state === CircuitState.HALF_OPEN) {
      // Service recovered, close the circuit
      this.state = CircuitState.CLOSED;
      this.failures = [];
      this.lastFailureTime = 0;
    } else if (this.state === CircuitState.CLOSED) {
      // Clean up old failures
      this.cleanupFailures();
    }
  }

  /**
   * Record a failed request
   */
  recordFailure(): void {
    const now = Date.now();
    this.failures.push({ timestamp: now });
    this.lastFailureTime = now;

    this.cleanupFailures();

    // Check if we should open the circuit
    if (this.failures.length >= this.options.failureThreshold) {
      if (this.state === CircuitState.CLOSED) {
        this.state = CircuitState.OPEN;
      }
    }
  }

  /**
   * Check if request should be allowed
   */
  canAttempt(): boolean {
    const now = Date.now();

    // Clean up old failures
    this.cleanupFailures();

    // If circuit is closed, allow requests
    if (this.state === CircuitState.CLOSED) {
      return true;
    }

    // If circuit is open, check if reset timeout has passed
    if (this.state === CircuitState.OPEN) {
      if (now - this.lastFailureTime >= this.options.resetTimeout) {
        // Try half-open state
        this.state = CircuitState.HALF_OPEN;
        return true;
      }
      return false;
    }

    // Half-open: allow one request to test
    return this.state === CircuitState.HALF_OPEN;
  }

  /**
   * Get current state
   */
  getState(): CircuitState {
    return this.state;
  }

  /**
   * Reset circuit breaker
   */
  reset(): void {
    this.state = CircuitState.CLOSED;
    this.failures = [];
    this.lastFailureTime = 0;
  }

  /**
   * Remove failures outside monitoring period
   */
  private cleanupFailures(): void {
    const now = Date.now();
    const cutoff = now - this.options.monitoringPeriod;
    this.failures = this.failures.filter((f) => f.timestamp > cutoff);
  }
}

/**
 * Create a circuit breaker instance
 */
export function createCircuitBreaker(options: CircuitBreakerOptions = {}): CircuitBreaker {
  return new CircuitBreaker(options);
}
