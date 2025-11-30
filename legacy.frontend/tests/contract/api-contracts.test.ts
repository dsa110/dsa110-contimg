/**
 * API Contract Tests
 *
 * These tests verify that the backend API responses match our Zod schemas.
 * Run against the live API to catch contract drift.
 *
 * Run with: npx vitest run tests/contract
 */
import { describe, it, expect, beforeAll } from "vitest";
import { z } from "zod";
import axios from "axios";

// Import our Zod schemas
import { PipelineStatusSchema } from "../../src/api/schemas/pipelineStatus";
import { SystemMetricsSchema } from "../../src/api/schemas/systemMetrics";
import { HealthSummarySchema } from "../../src/api/schemas/healthSummary";
import { WorkflowStatusSchema } from "../../src/api/schemas/workflowStatus";
import { EventStatisticsSchema } from "../../src/api/schemas/eventStatistics";
import { DLQStatsSchema, CircuitBreakerListSchema } from "../../src/api/schemas/queueTypes";

// API base URL - use environment variable or default to local
const API_BASE = process.env.VITE_API_URL || "http://localhost:8000/api";

// Create axios instance with timeout
const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
});

// Helper to test an endpoint against a schema
async function testEndpoint<T>(
  endpoint: string,
  schema: z.ZodType<T>,
  options?: { expectError?: boolean }
): Promise<{ success: boolean; data?: T; error?: string }> {
  try {
    const response = await api.get(endpoint);
    const result = schema.safeParse(response.data);

    if (!result.success) {
      const errors = result.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("\n");
      return { success: false, error: `Schema validation failed:\n${errors}` };
    }

    return { success: true, data: result.data };
  } catch (error) {
    if (options?.expectError) {
      return { success: true };
    }
    const message = error instanceof Error ? error.message : String(error);
    return { success: false, error: `Request failed: ${message}` };
  }
}

describe("API Contract Tests", () => {
  // Skip if API is not available
  let apiAvailable = false;

  beforeAll(async () => {
    try {
      // Use /status endpoint which we know exists
      await api.get("/status", { timeout: 5000 });
      apiAvailable = true;
      console.log(":white_heavy_check_mark: API available at", API_BASE);
    } catch (error) {
      console.warn(":warning: API not available at", API_BASE, "- skipping contract tests");
      console.warn("   Error:", error instanceof Error ? error.message : error);
    }
  });

  describe("Core Status Endpoints", () => {
    it("GET /status returns valid PipelineStatus", async () => {
      if (!apiAvailable) return;

      const result = await testEndpoint("/status", PipelineStatusSchema);
      expect(result.success, result.error).toBe(true);

      if (result.data) {
        // Additional semantic checks
        expect(result.data.queue.total).toBeGreaterThanOrEqual(0);
        expect(result.data.recent_groups).toBeInstanceOf(Array);
      }
    });

    it("GET /metrics/system returns valid SystemMetrics", async () => {
      if (!apiAvailable) return;

      const result = await testEndpoint("/metrics/system", SystemMetricsSchema);
      expect(result.success, result.error).toBe(true);

      if (result.data) {
        // CPU/memory should be percentages
        if (result.data.cpu_percent !== null) {
          expect(result.data.cpu_percent).toBeGreaterThanOrEqual(0);
          expect(result.data.cpu_percent).toBeLessThanOrEqual(100);
        }
      }
    });

    it("GET /health/summary returns valid HealthSummary", async () => {
      if (!apiAvailable) return;

      const result = await testEndpoint("/health/summary", HealthSummarySchema);
      expect(result.success, result.error).toBe(true);

      if (result.data) {
        expect(["healthy", "degraded", "unhealthy", "unknown"]).toContain(result.data.status);
      }
    });
  });

  describe("Pipeline Endpoints", () => {
    it("GET /pipeline/workflow-status returns valid WorkflowStatus", async () => {
      if (!apiAvailable) return;

      const result = await testEndpoint("/pipeline/workflow-status", WorkflowStatusSchema);
      expect(result.success, result.error).toBe(true);

      if (result.data) {
        expect(["healthy", "degraded", "stalled"]).toContain(result.data.overall_health);
        expect(result.data.stages).toBeInstanceOf(Array);
      }
    });
  });

  describe("Operations Endpoints", () => {
    it("GET /operations/dlq/stats returns valid DLQStats", async () => {
      if (!apiAvailable) return;

      const result = await testEndpoint("/operations/dlq/stats", DLQStatsSchema);
      expect(result.success, result.error).toBe(true);

      if (result.data) {
        // Total should equal sum of statuses
        const sum =
          result.data.pending + result.data.retrying + result.data.resolved + result.data.failed;
        expect(result.data.total).toBe(sum);
      }
    });

    it("GET /operations/circuit-breakers returns valid CircuitBreakerList", async () => {
      if (!apiAvailable) return;

      const result = await testEndpoint("/operations/circuit-breakers", CircuitBreakerListSchema);
      expect(result.success, result.error).toBe(true);

      if (result.data) {
        expect(result.data.circuit_breakers).toBeInstanceOf(Array);
        for (const cb of result.data.circuit_breakers) {
          expect(["closed", "open", "half_open"]).toContain(cb.state);
        }
      }
    });
  });

  describe("Events Endpoints", () => {
    it("GET /events/stats returns valid EventStatistics", async () => {
      if (!apiAvailable) return;

      const result = await testEndpoint("/events/stats", EventStatisticsSchema);
      expect(result.success, result.error).toBe(true);

      if (result.data) {
        expect(result.data.total_events).toBeGreaterThanOrEqual(0);
        expect(result.data.events_per_type).toBeInstanceOf(Object);
      }
    });
  });
});

/**
 * Export test utilities for use in other tests
 */
export { testEndpoint, api, API_BASE };
