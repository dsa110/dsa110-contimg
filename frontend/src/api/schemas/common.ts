/**
 * Common Zod schemas shared across multiple API responses
 */
import { z } from "zod";

// ============================================
// Primitive helpers
// ============================================

/** Non-negative integer */
export const countNumber = z.number().int().min(0);

/** Non-negative finite number */
export const positiveNumber = z.number().finite().min(0);

/** Percentage (0-100) */
export const percentNumber = z.number().finite().min(0).max(100);

/** ISO timestamp string */
export const isoTimestamp = z.string().datetime({ offset: true }).or(z.string().min(1));

/** Unix timestamp (seconds or milliseconds) */
export const unixTimestamp = z.number().finite().positive();

// ============================================
// Reusable object schemas
// ============================================

/** Disk information */
export const DiskInfoSchema = z.object({
  mount_point: z.string(),
  total: positiveNumber,
  used: positiveNumber,
  free: positiveNumber,
  percent: percentNumber,
});

/** Calibrator match result */
export const CalibratorMatchSchema = z.object({
  name: z.string(),
  ra_deg: z.number().finite(),
  dec_deg: z.number().finite(),
  sep_deg: z.number().finite(),
  weighted_flux: z.number().finite().nullable().optional(),
});

/** Health check result for a single service */
export const HealthCheckResultSchema = z.object({
  healthy: z.boolean(),
  error: z.string().optional(),
  message: z.string().optional(),
  timestamp: unixTimestamp.optional(),
});

/** Circuit breaker state */
export const CircuitBreakerStateSchema = z.object({
  name: z.string(),
  state: z.enum(["closed", "open", "half_open"]),
  failure_count: countNumber,
  last_failure_time: unixTimestamp.optional(),
  recovery_timeout: positiveNumber,
});

// ============================================
// Type exports (inferred from schemas)
// ============================================
export type DiskInfo = z.infer<typeof DiskInfoSchema>;
export type CalibratorMatch = z.infer<typeof CalibratorMatchSchema>;
export type HealthCheckResult = z.infer<typeof HealthCheckResultSchema>;
export type CircuitBreakerState = z.infer<typeof CircuitBreakerStateSchema>;
