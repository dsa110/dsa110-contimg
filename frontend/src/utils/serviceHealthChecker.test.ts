import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  ServiceHealthChecker,
  DEFAULT_SERVICES,
  getServiceHealthChecker,
  resetServiceHealthChecker,
} from "./serviceHealthChecker";

// Mock fetch
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Mock performance.now
const mockPerformanceNow = vi.fn();
performance.now = mockPerformanceNow;

describe("serviceHealthChecker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockPerformanceNow.mockReturnValue(0);
    resetServiceHealthChecker();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("ServiceHealthChecker", () => {
    describe("checkAllServices - backend API success", () => {
      it("returns results from backend API when successful", async () => {
        const backendResponse = {
          services: [
            {
              name: "Test Service",
              port: 8000,
              description: "Test",
              status: "running",
              responseTime: 50,
              lastChecked: new Date().toISOString(),
              error: null,
              details: null,
            },
          ],
          summary: { total: 1, running: 1, stopped: 0 },
          timestamp: new Date().toISOString(),
        };

        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(backendResponse),
        });

        const checker = new ServiceHealthChecker();
        const result = await checker.checkAllServices();

        expect(result.apiAvailable).toBe(true);
        expect(result.results[0].source).toBe("backend-api");
        expect(result.results[0].status).toBe("running");
        expect(result.diagnostics.backendAttempts).toBe(1);
        expect(result.diagnostics.fallbackUsed).toBe(false);
      });

      it("transforms backend response correctly", async () => {
        const backendResponse = {
          services: [
            {
              name: "FastAPI Backend",
              port: 8000,
              description: "REST API",
              status: "degraded",
              responseTime: 150,
              lastChecked: "2025-01-01T12:00:00Z",
              error: "High latency",
              details: { connections: 50 },
            },
          ],
          summary: { total: 1, running: 0, stopped: 0 },
          timestamp: "2025-01-01T12:00:00Z",
        };

        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(backendResponse),
        });

        const checker = new ServiceHealthChecker();
        const result = await checker.checkAllServices();

        const service = result.results[0];
        expect(service.name).toBe("FastAPI Backend");
        expect(service.status).toBe("degraded");
        expect(service.responseTime).toBe(150);
        expect(service.error).toBe("High latency");
        expect(service.details).toEqual({ connections: 50 });
      });
    });

    describe("checkAllServices - retry logic", () => {
      it("retries on first failure and succeeds", async () => {
        const backendResponse = {
          services: [],
          summary: { total: 0, running: 0, stopped: 0 },
          timestamp: new Date().toISOString(),
        };

        // First call fails, second succeeds
        mockFetch.mockRejectedValueOnce(new Error("Network error")).mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(backendResponse),
        });

        const checker = new ServiceHealthChecker();
        const resultPromise = checker.checkAllServices();

        // Advance through backoff delays
        await vi.advanceTimersByTimeAsync(1000);

        const result = await resultPromise;

        expect(result.apiAvailable).toBe(true);
        expect(result.diagnostics.backendAttempts).toBe(2);
        expect(mockFetch).toHaveBeenCalledTimes(2);
      });

      it("falls back after all retries exhausted", async () => {
        mockFetch.mockRejectedValue(new Error("Network error"));

        const checker = new ServiceHealthChecker();
        const resultPromise = checker.checkAllServices();

        // Advance through all backoff delays
        await vi.advanceTimersByTimeAsync(10000);

        const result = await resultPromise;

        expect(result.apiAvailable).toBe(false);
        expect(result.diagnostics.backendAttempts).toBe(3); // Default max attempts
        expect(result.diagnostics.fallbackUsed).toBe(true);
        expect(result.diagnostics.backendError).toBe("Network error");
      });

      it("uses exponential backoff between retries", async () => {
        const fetchTimes: number[] = [];
        let callCount = 0;
        mockFetch.mockImplementation(() => {
          callCount++;
          fetchTimes.push(Date.now());
          // Only reject for the first 3 calls (backend attempts)
          // Then resolve for fallback probes
          if (callCount <= 3) {
            return Promise.reject(new Error("Network error"));
          }
          return Promise.resolve({ ok: true });
        });

        const checker = new ServiceHealthChecker();
        const resultPromise = checker.checkAllServices();

        // Advance through all retries
        await vi.advanceTimersByTimeAsync(20000);
        await resultPromise;

        // Should have at least 3 backend attempts
        expect(fetchTimes.length).toBeGreaterThanOrEqual(3);

        // Delays should increase (with some jitter)
        if (fetchTimes.length >= 3) {
          const delay1 = fetchTimes[1] - fetchTimes[0];
          const delay2 = fetchTimes[2] - fetchTimes[1];
          // Second delay should be roughly 2x the first (with jitter)
          expect(delay2).toBeGreaterThanOrEqual(delay1 * 1.5);
        }
      });
    });

    describe("checkAllServices - fallback probing", () => {
      it("uses fallback probing when backend fails", async () => {
        mockFetch
          .mockRejectedValueOnce(new Error("Backend down")) // Backend API
          .mockRejectedValueOnce(new Error("Backend down")) // Retry 1
          .mockRejectedValueOnce(new Error("Backend down")) // Retry 2
          .mockResolvedValue({ ok: true }); // Fallback probes

        mockPerformanceNow.mockReturnValue(100);

        const checker = new ServiceHealthChecker();
        const resultPromise = checker.checkAllServices();

        await vi.advanceTimersByTimeAsync(20000);
        const result = await resultPromise;

        expect(result.apiAvailable).toBe(false);
        expect(result.diagnostics.fallbackUsed).toBe(true);
        expect(result.results.length).toBe(DEFAULT_SERVICES.length);
      });

      it("marks non-HTTP services as unknown in fallback mode", async () => {
        // Fail backend
        mockFetch
          .mockRejectedValueOnce(new Error("Backend down"))
          .mockRejectedValueOnce(new Error("Backend down"))
          .mockRejectedValueOnce(new Error("Backend down"));

        // Successful probes for HTTP services
        mockFetch.mockResolvedValue({ ok: true });

        const checker = new ServiceHealthChecker();
        const resultPromise = checker.checkAllServices();

        await vi.advanceTimersByTimeAsync(20000);
        const result = await resultPromise;

        // Find Redis (non-HTTP service)
        const redis = result.results.find((s) => s.name === "Redis");
        expect(redis).toBeDefined();
        expect(redis?.status).toBe("unknown");
        expect(redis?.error).toContain("Cannot probe from browser");
      });
    });

    describe("failure tracking", () => {
      it("tracks consecutive failures", async () => {
        const backendResponse = {
          services: [
            {
              name: "Test Service",
              port: 8000,
              description: "Test",
              status: "stopped",
              responseTime: 0,
              lastChecked: new Date().toISOString(),
              error: "Connection refused",
              details: null,
            },
          ],
          summary: { total: 1, running: 0, stopped: 1 },
          timestamp: new Date().toISOString(),
        };

        mockFetch.mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(backendResponse),
        });

        const checker = new ServiceHealthChecker();

        // First check
        const result1 = await checker.checkAllServices();
        expect(result1.results[0].failureCount).toBe(1);

        // Second check
        const result2 = await checker.checkAllServices();
        expect(result2.results[0].failureCount).toBe(2);

        // Third check
        const result3 = await checker.checkAllServices();
        expect(result3.results[0].failureCount).toBe(3);
      });

      it("resets failure count on success", async () => {
        const createResponse = (status: string) => ({
          services: [
            {
              name: "Test Service",
              port: 8000,
              description: "Test",
              status,
              responseTime: 50,
              lastChecked: new Date().toISOString(),
              error: status === "stopped" ? "Error" : null,
              details: null,
            },
          ],
          summary: {
            total: 1,
            running: status === "running" ? 1 : 0,
            stopped: status === "stopped" ? 1 : 0,
          },
          timestamp: new Date().toISOString(),
        });

        // Fail twice
        mockFetch
          .mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve(createResponse("stopped")),
          })
          .mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve(createResponse("stopped")),
          })
          .mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve(createResponse("running")),
          });

        const checker = new ServiceHealthChecker();

        await checker.checkAllServices();
        const result2 = await checker.checkAllServices();
        expect(result2.results[0].failureCount).toBe(2);

        // Succeed
        const result3 = await checker.checkAllServices();
        expect(result3.results[0].failureCount).toBe(0);
      });
    });

    describe("abort", () => {
      it("can abort in-flight requests", async () => {
        // Create checker
        const checker = new ServiceHealthChecker();
        
        // Mock a slow backend response
        let resolveBackend: () => void;
        mockFetch.mockImplementation(() => {
          return new Promise((resolve) => {
            resolveBackend = () => resolve({ ok: true, json: () => Promise.resolve({ services: [], summary: {}, timestamp: new Date().toISOString() }) });
          });
        });

        // Start the check
        const resultPromise = checker.checkAllServices();

        // Give it time to start
        await vi.advanceTimersByTimeAsync(50);

        // Abort 
        checker.abort();

        // Resolve to allow cleanup
        resolveBackend!();

        // Advance timers to complete
        await vi.advanceTimersByTimeAsync(100);

        // The promise should still resolve with some results
        const result = await resultPromise;
        expect(result).toBeDefined();
      }, 10000);
    });

    describe("reset", () => {
      it("clears cache and failure tracking", async () => {
        // Use a service from DEFAULT_SERVICES so it appears in getFailureStats
        const backendResponse = {
          services: [
            {
              name: "FastAPI Backend", // This matches DEFAULT_SERVICES
              port: 8000,
              description: "REST API for pipeline data",
              status: "stopped",
              responseTime: 0,
              lastChecked: new Date().toISOString(),
              error: "Error",
              details: null,
            },
          ],
          summary: { total: 1, running: 0, stopped: 1 },
          timestamp: new Date().toISOString(),
        };

        mockFetch.mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(backendResponse),
        });

        const checker = new ServiceHealthChecker();

        // Build up failures
        await checker.checkAllServices();
        await checker.checkAllServices();

        // Get failure stats
        const stats = checker.getFailureStats();
        const fastApiStats = stats.get("FastAPI Backend");
        expect(fastApiStats?.count).toBe(2);

        // Reset
        checker.reset();

        // After reset, stats should be cleared  
        const statsAfterReset = checker.getFailureStats();
        const fastApiStatsAfterReset = statsAfterReset.get("FastAPI Backend");
        expect(fastApiStatsAfterReset?.count).toBe(0);
      });
    });
  });

  describe("singleton management", () => {
    it("getServiceHealthChecker returns same instance", () => {
      const instance1 = getServiceHealthChecker();
      const instance2 = getServiceHealthChecker();
      expect(instance1).toBe(instance2);
    });

    it("resetServiceHealthChecker creates new instance", () => {
      const instance1 = getServiceHealthChecker();
      resetServiceHealthChecker();
      const instance2 = getServiceHealthChecker();
      expect(instance1).not.toBe(instance2);
    });
  });

  describe("DEFAULT_SERVICES", () => {
    it("contains expected services", () => {
      const names = DEFAULT_SERVICES.map((s) => s.name);
      expect(names).toContain("Vite Dev Server");
      expect(names).toContain("FastAPI Backend");
      expect(names).toContain("Redis");
      expect(names).toContain("Grafana");
      expect(names).toContain("MkDocs");
      expect(names).toContain("Prometheus");
    });

    it("has correct port configuration", () => {
      const portMap = new Map(DEFAULT_SERVICES.map((s) => [s.name, s.port]));
      expect(portMap.get("Vite Dev Server")).toBe(3000);
      expect(portMap.get("FastAPI Backend")).toBe(8000);
      expect(portMap.get("Redis")).toBe(6379);
    });

    it("marks Redis as non-client-probable", () => {
      const redis = DEFAULT_SERVICES.find((s) => s.name === "Redis");
      expect(redis?.clientProbable).toBe(false);
    });

    it("has health paths for HTTP services", () => {
      const httpServices = DEFAULT_SERVICES.filter((s) => s.clientProbable);
      httpServices.forEach((s) => {
        expect(s.healthPath).toBeDefined();
      });
    });
  });
});
