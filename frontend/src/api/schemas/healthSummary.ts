/**
 * Health Summary Schema
 * Validates /api/health responses
 */
import { z } from "zod";
import { HealthCheckResultSchema, unixTimestamp } from "./common";
import type { HealthSummary } from "../types";

export const HealthSummarySchema: z.ZodType<HealthSummary> = z
  .object({
    status: z.enum(["healthy", "degraded", "unhealthy", "unknown"]),
    timestamp: unixTimestamp,
    checks: z.record(z.string(), HealthCheckResultSchema),
  })
  .passthrough(); // Allow additional properties

/**
 * Validate health summary response
 * @throws ZodError if validation fails
 */
export const validateHealthSummary = (payload: unknown): HealthSummary => {
  return HealthSummarySchema.parse(payload);
};

/**
 * Safe validation that returns null instead of throwing
 */
export const safeValidateHealthSummary = (
  payload: unknown
): { success: true; data: HealthSummary } | { success: false; error: z.ZodError } => {
  const result = HealthSummarySchema.safeParse(payload);
  return result;
};
