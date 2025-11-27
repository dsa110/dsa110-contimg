/**
 * API Schema Validation - Central export for all Zod schemas
 *
 * This module provides runtime validation for API responses using Zod.
 * Benefits:
 * - Fails fast with clear errors when backend contracts change
 * - Provides TypeScript type inference from schemas
 * - Documents expected API response structure
 *
 * Usage:
 *   import { validateSystemMetrics } from './schemas';
 *   const data = validateSystemMetrics(response.data);
 */

// Re-export all schemas and validators
export * from "./pipelineStatus";
export * from "./systemMetrics";
export * from "./healthSummary";
export * from "./workflowStatus";
export * from "./eventStatistics";
export * from "./queueTypes";
export * from "./common";
