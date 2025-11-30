/**
 * Client-side service health checker with fallback probing, retry logic, and failure tracking.
 *
 * This module provides:
 * 1. Retry with exponential backoff for API calls
 * 2. Client-side fallback probes when backend API is unavailable
 * 3. Per-service failure tracking to surface which dependencies really failed
 * 4. Environment-aware port configuration
 */

/**
 * Service status result from health check
 */
export type ServiceStatusValue =
  | "running"
  | "stopped"
  | "degraded"
  | "error"
  | "checking"
  | "unknown";

export interface ServiceHealthResult {
  name: string;
  port: number;
  description: string;
  status: ServiceStatusValue;
  responseTime?: number;
  lastChecked: Date;
  error?: string;
  details?: Record<string, unknown>;
  /** Source of the health check result */
  source: "backend-api" | "client-probe" | "cached" | "fallback";
  /** Consecutive failure count */
  failureCount: number;
}

export interface ServiceConfig {
  name: string;
  port: number;
  description: string;
  /** Environment variable override for port */
  portEnvVar?: string;
  /** Relative health endpoint path for HTTP services */
  healthPath?: string;
  /** Whether this service supports client-side probing */
  clientProbable?: boolean;
}

/**
 * Default service configurations.
 * These can be overridden by environment variables or backend API responses.
 */
export const DEFAULT_SERVICES: ServiceConfig[] = [
  {
    name: "Vite Dev Server",
    port: 3000,
    description: "Frontend development server with HMR",
    portEnvVar: "VITE_PORT",
    healthPath: "/",
    clientProbable: true,
  },
  {
    name: "Grafana",
    port: 3030,
    description: "Metrics visualization dashboards",
    portEnvVar: "GRAFANA_PORT",
    healthPath: "/api/health",
    clientProbable: true,
  },
  {
    name: "Redis",
    port: 6379,
    description: "API response caching",
    portEnvVar: "REDIS_PORT",
    // Redis cannot be probed from browser
    clientProbable: false,
  },
  {
    name: "FastAPI Backend",
    port: 8000,
    description: "REST API for pipeline data",
    portEnvVar: "CONTIMG_API_PORT",
    healthPath: "/api/health",
    clientProbable: true,
  },
  {
    name: "MkDocs",
    port: 8001,
    description: "Documentation server (dev only)",
    portEnvVar: "MKDOCS_PORT",
    healthPath: "/",
    clientProbable: true,
  },
  {
    name: "Prometheus",
    port: 9090,
    description: "Metrics collection and storage",
    portEnvVar: "PROMETHEUS_PORT",
    healthPath: "/-/healthy",
    clientProbable: true,
  },
];

/**
 * Retry configuration
 */
export interface RetryConfig {
  /** Maximum number of retry attempts */
  maxAttempts: number;
  /** Initial delay in ms before first retry */
  initialDelayMs: number;
  /** Maximum delay in ms between retries */
  maxDelayMs: number;
  /** Multiplier for exponential backoff */
  backoffMultiplier: number;
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxAttempts: 3,
  initialDelayMs: 500,
  maxDelayMs: 5000,
  backoffMultiplier: 2,
};

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
 * Service status response from backend API
 */
interface BackendServiceStatus {
  name: string;
  port: number;
  description: string;
  status: ServiceStatusValue;
  responseTime: number;
  lastChecked: string;
  error: string | null;
  details: Record<string, unknown> | null;
}

interface BackendServicesResponse {
  services: BackendServiceStatus[];
  summary: {
    total: number;
    running: number;
    stopped: number;
  };
  timestamp: string;
}

/**
 * Failure tracker for individual services
 */
class FailureTracker {
  private failures: Map<string, number> = new Map();
  private lastSuccess: Map<string, Date> = new Map();

  recordFailure(serviceName: string): number {
    const current = this.failures.get(serviceName) || 0;
    const newCount = current + 1;
    this.failures.set(serviceName, newCount);
    return newCount;
  }

  recordSuccess(serviceName: string): void {
    this.failures.set(serviceName, 0);
    this.lastSuccess.set(serviceName, new Date());
  }

  getFailureCount(serviceName: string): number {
    return this.failures.get(serviceName) || 0;
  }

  getLastSuccess(serviceName: string): Date | undefined {
    return this.lastSuccess.get(serviceName);
  }

  reset(serviceName: string): void {
    this.failures.set(serviceName, 0);
  }

  resetAll(): void {
    this.failures.clear();
  }
}

/**
 * Health check cache entry
 */
interface CacheEntry {
  result: ServiceHealthResult;
  timestamp: number;
  ttlMs: number;
}

/**
 * Result cache to prevent overwhelming services with checks
 */
class HealthCheckCache {
  private cache: Map<string, CacheEntry> = new Map();
  private defaultTtlMs: number = 5000; // 5 seconds default

  set(serviceName: string, result: ServiceHealthResult, ttlMs?: number): void {
    this.cache.set(serviceName, {
      result,
      timestamp: Date.now(),
      ttlMs: ttlMs ?? this.defaultTtlMs,
    });
  }

  get(serviceName: string): ServiceHealthResult | null {
    const entry = this.cache.get(serviceName);
    if (!entry) return null;

    const isExpired = Date.now() - entry.timestamp > entry.ttlMs;
    if (isExpired) {
      this.cache.delete(serviceName);
      return null;
    }

    return { ...entry.result, source: "cached" };
  }

  clear(): void {
    this.cache.clear();
  }
}

/**
 * Main service health checker class
 */
export class ServiceHealthChecker {
  private services: ServiceConfig[];
  private retryConfig: RetryConfig;
  private failureTracker: FailureTracker;
  private cache: HealthCheckCache;
  private backendApiUrl: string;
  private abortController: AbortController | null = null;

  constructor(
    services: ServiceConfig[] = DEFAULT_SERVICES,
    retryConfig: RetryConfig = DEFAULT_RETRY_CONFIG,
    backendApiUrl: string = "/api/services/status"
  ) {
    this.services = services;
    this.retryConfig = retryConfig;
    this.failureTracker = new FailureTracker();
    this.cache = new HealthCheckCache();
    this.backendApiUrl = backendApiUrl;
  }

  /**
   * Cancel any in-flight health checks
   */
  abort(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  /**
   * Main entry point: check all services with retry and fallback
   */
  async checkAllServices(): Promise<{
    results: ServiceHealthResult[];
    apiAvailable: boolean;
    diagnostics: CheckDiagnostics;
  }> {
    this.abort();
    this.abortController = new AbortController();
    const signal = this.abortController.signal;

    const diagnostics: CheckDiagnostics = {
      backendAttempts: 0,
      backendError: null,
      fallbackUsed: false,
      individualProbes: [],
    };

    // First, try backend API with retry
    const backendResult = await this.fetchFromBackendWithRetry(signal, diagnostics);

    if (backendResult) {
      // Backend succeeded - use its results but update failure tracking
      const results = this.processBackendResults(backendResult);
      return { results, apiAvailable: true, diagnostics };
    }

    // Backend failed - use fallback probing
    diagnostics.fallbackUsed = true;
    const results = await this.performFallbackProbes(signal, diagnostics);

    return { results, apiAvailable: false, diagnostics };
  }

  /**
   * Fetch from backend API with retry and exponential backoff
   */
  private async fetchFromBackendWithRetry(
    signal: AbortSignal,
    diagnostics: CheckDiagnostics
  ): Promise<BackendServicesResponse | null> {
    for (let attempt = 0; attempt < this.retryConfig.maxAttempts; attempt++) {
      diagnostics.backendAttempts++;

      if (signal.aborted) return null;

      try {
        const result = await this.fetchFromBackend(signal);
        this.failureTracker.recordSuccess("backend-api");
        return result;
      } catch (err) {
        const error = err instanceof Error ? err.message : String(err);
        diagnostics.backendError = error;

        // Don't retry on abort
        if (signal.aborted) return null;

        // Don't wait after the last attempt
        if (attempt < this.retryConfig.maxAttempts - 1) {
          const delay = calculateBackoffDelay(attempt, this.retryConfig);
          await sleep(delay);
        }
      }
    }

    this.failureTracker.recordFailure("backend-api");
    return null;
  }

  /**
   * Single fetch attempt to backend API
   */
  private async fetchFromBackend(signal: AbortSignal): Promise<BackendServicesResponse> {
    const timeoutMs = 10000;
    const timeoutId = setTimeout(() => {
      // Create a new AbortController specifically for this timeout
    }, timeoutMs);

    try {
      const response = await fetch(this.backendApiUrl, {
        method: "GET",
        signal,
        headers: { Accept: "application/json" },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      throw err;
    }
  }

  /**
   * Process backend API results into our internal format
   */
  private processBackendResults(response: BackendServicesResponse): ServiceHealthResult[] {
    return response.services.map((svc) => {
      const isSuccess = svc.status === "running";
      if (isSuccess) {
        this.failureTracker.recordSuccess(svc.name);
      } else {
        this.failureTracker.recordFailure(svc.name);
      }

      return {
        name: svc.name,
        port: svc.port,
        description: svc.description,
        status: svc.status,
        responseTime: svc.responseTime,
        lastChecked: new Date(svc.lastChecked),
        error: svc.error || undefined,
        details: svc.details || undefined,
        source: "backend-api" as const,
        failureCount: this.failureTracker.getFailureCount(svc.name),
      };
    });
  }

  /**
   * Perform client-side fallback probes when backend is unavailable
   */
  private async performFallbackProbes(
    signal: AbortSignal,
    diagnostics: CheckDiagnostics
  ): Promise<ServiceHealthResult[]> {
    const results: ServiceHealthResult[] = [];

    // Check services in parallel
    const probePromises = this.services.map(async (service) => {
      if (signal.aborted) {
        return this.createFallbackResult(service, "unknown", "Check aborted");
      }

      // Check cache first
      const cached = this.cache.get(service.name);
      if (cached) {
        diagnostics.individualProbes.push({
          service: service.name,
          success: cached.status === "running",
          source: "cached",
        });
        return cached;
      }

      const result = await this.probeService(service, signal);
      diagnostics.individualProbes.push({
        service: service.name,
        success: result.status === "running",
        source: "client-probe",
        error: result.error,
      });

      // Cache the result
      this.cache.set(service.name, result);

      return result;
    });

    const probeResults = await Promise.all(probePromises);
    results.push(...probeResults);

    return results;
  }

  /**
   * Probe a single service from the client side
   */
  private async probeService(
    service: ServiceConfig,
    signal: AbortSignal
  ): Promise<ServiceHealthResult> {
    if (!service.clientProbable) {
      // Service cannot be probed from browser (e.g., Redis)
      return this.createFallbackResult(
        service,
        "unknown",
        "Cannot probe from browser (non-HTTP service)"
      );
    }

    const startTime = performance.now();

    try {
      // Build the probe URL
      const baseUrl = `http://127.0.0.1:${service.port}`;
      const url = service.healthPath ? `${baseUrl}${service.healthPath}` : baseUrl;

      // Use a shorter timeout for client probes
      const timeoutMs = 5000;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

      // Forward abort from parent signal
      signal.addEventListener("abort", () => controller.abort());

      const response = await fetch(url, {
        method: "GET",
        signal: controller.signal,
        // Note: We cannot use no-cors mode because we need to read the response status
        // CORS/CSP restrictions may prevent this from working in some environments
        mode: "cors",
        cache: "no-store",
      });

      clearTimeout(timeoutId);

      const responseTime = performance.now() - startTime;

      if (response.ok) {
        this.failureTracker.recordSuccess(service.name);
        return {
          name: service.name,
          port: service.port,
          description: service.description,
          status: "running",
          responseTime,
          lastChecked: new Date(),
          source: "client-probe",
          failureCount: 0,
        };
      } else {
        const failureCount = this.failureTracker.recordFailure(service.name);
        return {
          name: service.name,
          port: service.port,
          description: service.description,
          status: "degraded",
          responseTime,
          lastChecked: new Date(),
          error: `HTTP ${response.status}`,
          source: "client-probe",
          failureCount,
        };
      }
    } catch (err) {
      const error = err instanceof Error ? err.message : String(err);
      const failureCount = this.failureTracker.recordFailure(service.name);

      // Distinguish between different types of failures
      let status: ServiceStatusValue = "stopped";
      let errorMessage = error;

      if (error.includes("NetworkError") || error.includes("Failed to fetch")) {
        // Could be CORS, service down, or network issue
        status = "error";
        errorMessage = "Network error (may be CORS restriction or service down)";
      } else if (error.includes("abort")) {
        status = "unknown";
        errorMessage = "Request timed out";
      }

      return {
        name: service.name,
        port: service.port,
        description: service.description,
        status,
        responseTime: performance.now() - startTime,
        lastChecked: new Date(),
        error: errorMessage,
        source: "client-probe",
        failureCount,
      };
    }
  }

  /**
   * Create a fallback result when we can't determine status
   */
  private createFallbackResult(
    service: ServiceConfig,
    status: ServiceStatusValue,
    error?: string
  ): ServiceHealthResult {
    return {
      name: service.name,
      port: service.port,
      description: service.description,
      status,
      lastChecked: new Date(),
      error,
      source: "fallback",
      failureCount: this.failureTracker.getFailureCount(service.name),
    };
  }

  /**
   * Get failure statistics
   */
  getFailureStats(): Map<string, { count: number; lastSuccess?: Date }> {
    const stats = new Map<string, { count: number; lastSuccess?: Date }>();
    for (const service of this.services) {
      stats.set(service.name, {
        count: this.failureTracker.getFailureCount(service.name),
        lastSuccess: this.failureTracker.getLastSuccess(service.name),
      });
    }
    stats.set("backend-api", {
      count: this.failureTracker.getFailureCount("backend-api"),
      lastSuccess: this.failureTracker.getLastSuccess("backend-api"),
    });
    return stats;
  }

  /**
   * Clear all cached data and reset failure tracking
   */
  reset(): void {
    this.cache.clear();
    this.failureTracker.resetAll();
  }
}

/**
 * Diagnostics from a health check operation
 */
export interface CheckDiagnostics {
  /** Number of attempts made to reach the backend API */
  backendAttempts: number;
  /** Error message if backend failed */
  backendError: string | null;
  /** Whether fallback probing was used */
  fallbackUsed: boolean;
  /** Individual probe results */
  individualProbes: Array<{
    service: string;
    success: boolean;
    source: string;
    error?: string;
  }>;
}

/**
 * Create a singleton instance with default configuration
 */
let defaultInstance: ServiceHealthChecker | null = null;

export function getServiceHealthChecker(): ServiceHealthChecker {
  if (!defaultInstance) {
    defaultInstance = new ServiceHealthChecker();
  }
  return defaultInstance;
}

/**
 * Reset the singleton instance (useful for testing)
 */
export function resetServiceHealthChecker(): void {
  if (defaultInstance) {
    defaultInstance.abort();
    defaultInstance.reset();
  }
  defaultInstance = null;
}
