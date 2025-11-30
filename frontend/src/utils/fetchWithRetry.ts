/**
 * Fetch with retry and exponential backoff for external service calls.
 * Provides consistent retry behavior for VizieR, Sesame, and other external APIs.
 */

export interface RetryConfig {
  /** Maximum number of retry attempts (default: 3) */
  maxRetries: number;
  /** Base delay in ms for exponential backoff (default: 1000) */
  baseDelayMs: number;
  /** Maximum delay in ms between retries (default: 10000) */
  maxDelayMs: number;
  /** Multiplier for exponential backoff (default: 2) */
  backoffMultiplier: number;
  /** Jitter factor to add randomness (0-1, default: 0.1) */
  jitterFactor: number;
  /** HTTP status codes that should trigger a retry (default: [408, 429, 500, 502, 503, 504]) */
  retryStatusCodes: number[];
  /** Timeout in ms for each request (default: 30000) */
  timeoutMs: number;
}

export const DEFAULT_EXTERNAL_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelayMs: 1000,
  maxDelayMs: 10000,
  backoffMultiplier: 2,
  jitterFactor: 0.1,
  retryStatusCodes: [408, 429, 500, 502, 503, 504],
  timeoutMs: 30000,
};

/**
 * Conservative config for services known to rate-limit (like VizieR).
 */
export const RATE_LIMITED_RETRY_CONFIG: RetryConfig = {
  ...DEFAULT_EXTERNAL_RETRY_CONFIG,
  maxRetries: 2,
  baseDelayMs: 2000,
  backoffMultiplier: 3,
  jitterFactor: 0.2,
};

export interface RetryResult<T> {
  data: T;
  attempts: number;
  finalDelay?: number;
}

/**
 * Calculate delay with exponential backoff and jitter.
 */
function calculateDelay(
  attempt: number,
  config: RetryConfig,
  retryAfterHeader?: string | null
): number {
  // Check for Retry-After header (for 429 responses)
  if (retryAfterHeader) {
    const retryAfter = parseInt(retryAfterHeader, 10);
    if (!isNaN(retryAfter)) {
      return retryAfter * 1000; // Convert seconds to ms
    }
  }

  // Exponential backoff: baseDelay * multiplier^attempt
  const exponentialDelay = config.baseDelayMs * Math.pow(config.backoffMultiplier, attempt);
  const clampedDelay = Math.min(exponentialDelay, config.maxDelayMs);

  // Add jitter to prevent thundering herd
  const jitter = clampedDelay * config.jitterFactor * Math.random();

  return Math.floor(clampedDelay + jitter);
}

/**
 * Determine if an error should trigger a retry.
 */
function shouldRetry(
  error: unknown,
  response: Response | null,
  config: RetryConfig,
  attempt: number
): boolean {
  if (attempt >= config.maxRetries) {
    return false;
  }

  // Network errors (no response) should be retried
  if (!response && error instanceof TypeError) {
    return true;
  }

  // Check for retryable status codes
  if (response && config.retryStatusCodes.includes(response.status)) {
    return true;
  }

  return false;
}

/**
 * Create an AbortSignal that combines an external signal with a timeout.
 */
function createTimeoutSignal(
  timeoutMs: number,
  externalSignal?: AbortSignal
): { signal: AbortSignal; cleanup: () => void } {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(new Error("Request timeout")), timeoutMs);

  // If there's an external signal, abort when it aborts
  const onExternalAbort = () => {
    clearTimeout(timeoutId);
    controller.abort(externalSignal?.reason);
  };

  if (externalSignal) {
    if (externalSignal.aborted) {
      clearTimeout(timeoutId);
      controller.abort(externalSignal.reason);
    } else {
      externalSignal.addEventListener("abort", onExternalAbort);
    }
  }

  return {
    signal: controller.signal,
    cleanup: () => {
      clearTimeout(timeoutId);
      if (externalSignal) {
        externalSignal.removeEventListener("abort", onExternalAbort);
      }
    },
  };
}

/**
 * Fetch with automatic retry and exponential backoff.
 *
 * @param url - The URL to fetch
 * @param options - Fetch options (RequestInit)
 * @param config - Retry configuration
 * @returns Promise resolving to the fetch Response
 * @throws Error if all retries are exhausted or request is aborted
 *
 * @example
 * ```ts
 * const response = await fetchWithRetry(
 *   'https://api.example.com/data',
 *   { headers: { Accept: 'application/json' } },
 *   { maxRetries: 3, timeoutMs: 5000 }
 * );
 * ```
 */
export async function fetchWithRetry(
  url: string,
  options: RequestInit = {},
  config: Partial<RetryConfig> = {}
): Promise<Response> {
  const fullConfig: RetryConfig = { ...DEFAULT_EXTERNAL_RETRY_CONFIG, ...config };
  const externalSignal = options.signal;

  let lastError: Error | null = null;
  let lastResponse: Response | null = null;

  for (let attempt = 0; attempt <= fullConfig.maxRetries; attempt++) {
    // Create timeout signal for this attempt
    const { signal, cleanup } = createTimeoutSignal(fullConfig.timeoutMs, externalSignal);

    try {
      const response = await fetch(url, {
        ...options,
        signal,
      });

      cleanup();

      // Success or non-retryable error
      if (response.ok || !shouldRetry(null, response, fullConfig, attempt)) {
        return response;
      }

      // Retryable error - store response and calculate delay
      lastResponse = response;
      const delay = calculateDelay(attempt, fullConfig, response.headers.get("Retry-After"));

      console.debug(
        `[fetchWithRetry] Retryable status ${response.status} for ${url}, ` +
          `attempt ${attempt + 1}/${fullConfig.maxRetries + 1}, waiting ${delay}ms`
      );

      await new Promise((resolve) => setTimeout(resolve, delay));
    } catch (err) {
      cleanup();

      // Check if externally aborted
      if (externalSignal?.aborted) {
        throw new DOMException("Aborted", "AbortError");
      }

      // Check if it's our timeout
      if (err instanceof Error && err.message === "Request timeout") {
        lastError = new Error(`Request timeout after ${fullConfig.timeoutMs}ms`);
      } else if (err instanceof Error) {
        lastError = err;
      } else {
        lastError = new Error(String(err));
      }

      // Check if we should retry network errors
      if (!shouldRetry(err, null, fullConfig, attempt)) {
        throw lastError;
      }

      const delay = calculateDelay(attempt, fullConfig);
      console.debug(
        `[fetchWithRetry] Network error for ${url}, ` +
          `attempt ${attempt + 1}/${fullConfig.maxRetries + 1}, waiting ${delay}ms: ${lastError.message}`
      );

      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  // All retries exhausted
  if (lastResponse) {
    throw new Error(
      `Request failed after ${fullConfig.maxRetries + 1} attempts: ` +
        `HTTP ${lastResponse.status} ${lastResponse.statusText}`
    );
  }

  throw lastError || new Error(`Request failed after ${fullConfig.maxRetries + 1} attempts`);
}

/**
 * Parse common error responses and return user-friendly messages.
 */
export function parseExternalServiceError(error: unknown, serviceName: string): string {
  if (error instanceof Error) {
    // Abort errors
    if (error.name === "AbortError") {
      return "Request was cancelled";
    }

    // Timeout errors
    if (error.message.includes("timeout")) {
      return `${serviceName} is taking too long to respond. Please try again.`;
    }

    // Network errors (CORS, DNS, etc.)
    if (
      error.message.includes("fetch") ||
      error.message.includes("network") ||
      error.message.includes("Failed to fetch")
    ) {
      return `Could not connect to ${serviceName}. The service may be down or blocked by CORS.`;
    }

    // HTTP status errors
    const statusMatch = error.message.match(/HTTP (\d+)/);
    if (statusMatch) {
      const status = parseInt(statusMatch[1], 10);
      switch (status) {
        case 429:
          return `${serviceName} rate limit exceeded. Please wait a moment and try again.`;
        case 503:
        case 502:
        case 504:
          return `${serviceName} is temporarily unavailable. Please try again later.`;
        default:
          return `${serviceName} returned an error (${status}). Please try again.`;
      }
    }

    return error.message;
  }

  return `An unexpected error occurred with ${serviceName}`;
}
