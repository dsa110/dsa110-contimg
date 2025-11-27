/**
 * System Metrics Schema
 * Validates /api/metrics/system responses
 */
import { z } from "zod";
import { DiskInfoSchema, positiveNumber, percentNumber, isoTimestamp } from "./common";
import type { SystemMetrics } from "../types";

export const SystemMetricsSchema: z.ZodType<SystemMetrics> = z.object({
  ts: isoTimestamp,
  cpu_percent: percentNumber.nullable().optional(),
  mem_percent: percentNumber.nullable().optional(),
  mem_total: positiveNumber.nullable().optional(),
  mem_used: positiveNumber.nullable().optional(),
  disk_total: positiveNumber.nullable().optional(),
  disk_used: positiveNumber.nullable().optional(),
  disks: z.array(DiskInfoSchema).optional(),
  load_1: positiveNumber.nullable().optional(),
  load_5: positiveNumber.nullable().optional(),
  load_15: positiveNumber.nullable().optional(),
});

/**
 * Validate system metrics response
 * @throws ZodError if validation fails
 */
export const validateSystemMetrics = (payload: unknown): SystemMetrics => {
  return SystemMetricsSchema.parse(payload);
};

/**
 * Safe validation that returns null instead of throwing
 */
export const safeValidateSystemMetrics = (
  payload: unknown
): { success: true; data: SystemMetrics } | { success: false; error: z.ZodError } => {
  const result = SystemMetricsSchema.safeParse(payload);
  return result;
};
