/**
 * Queue & DLQ Schemas
 * Validates queue-related API responses
 *
 * Note: We define schemas without ZodType<T> constraint to avoid
 * exactOptionalPropertyTypes conflicts. The validate* functions
 * cast to the expected types after validation.
 */
import { z } from "zod";
import { countNumber, unixTimestamp } from "./common";
import type { DLQItem, DLQStats, CircuitBreakerList } from "../types";

// Internal schema for circuit breaker (matches common.ts but without type constraint)
const CircuitBreakerStateSchemaInternal = z.object({
  name: z.string(),
  state: z.enum(["closed", "open", "half_open"]),
  failure_count: countNumber,
  last_failure_time: unixTimestamp.optional(),
  recovery_timeout: z.number().finite().min(0),
});

export const DLQItemSchema = z.object({
  id: z.number().int(),
  component: z.string(),
  operation: z.string(),
  error_type: z.string(),
  error_message: z.string(),
  context: z.record(z.string(), z.unknown()),
  created_at: unixTimestamp,
  retry_count: countNumber,
  status: z.enum(["pending", "retrying", "resolved", "failed"]),
  resolved_at: unixTimestamp.optional(),
  resolution_note: z.string().optional(),
});

export const DLQStatsSchema = z.object({
  total: countNumber,
  pending: countNumber,
  retrying: countNumber,
  resolved: countNumber,
  failed: countNumber,
});

export const CircuitBreakerListSchema = z.object({
  circuit_breakers: z.array(CircuitBreakerStateSchemaInternal),
});

/**
 * Validate DLQ item
 * @throws ZodError if validation fails
 */
export const validateDLQItem = (payload: unknown): DLQItem => {
  // Parse validates, then cast to handle exactOptionalPropertyTypes
  return DLQItemSchema.parse(payload) as DLQItem;
};

/**
 * Validate DLQ stats
 * @throws ZodError if validation fails
 */
export const validateDLQStats = (payload: unknown): DLQStats => {
  return DLQStatsSchema.parse(payload) as DLQStats;
};

/**
 * Validate circuit breaker list
 * @throws ZodError if validation fails
 */
export const validateCircuitBreakerList = (payload: unknown): CircuitBreakerList => {
  // Parse validates, then cast to handle exactOptionalPropertyTypes
  return CircuitBreakerListSchema.parse(payload) as CircuitBreakerList;
};
