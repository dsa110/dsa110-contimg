/**
 * Utils barrel export.
 *
 * Re-exports all utility functions for easier imports:
 * import { formatRA, relativeTime } from '../utils';
 */

// Coordinate formatting (display strings with symbols)
export {
  formatRA,
  formatDec,
  formatCoordinates,
  formatDegrees,
} from "./coordinateFormatter";

// Coordinate parsing (parse various formats to decimal degrees)
export {
  parseRA,
  parseDec,
  parseCoordinatePair,
  formatRAtoHMS,
  formatDectoDMS,
} from "./coordinateParser";

// Error mapping
export { mapErrorResponse } from "./errorMapper";

// Relative time formatting
export { relativeTime } from "./relativeTime";

// Provenance data mappers
export {
  mapProvenanceFromImageDetail,
  mapProvenanceFromMSDetail,
  mapProvenanceFromSourceDetail,
} from "./provenanceMappers";

// Fetch utilities with retry
export {
  fetchWithRetry,
  DEFAULT_EXTERNAL_RETRY_CONFIG,
} from "./fetchWithRetry";

// Service health checker
export {
  ServiceHealthChecker,
  getServiceHealthChecker,
  resetServiceHealthChecker,
  DEFAULT_SERVICES,
} from "./serviceHealthChecker";

export type {
  ServiceStatusValue,
  ServiceHealthResult,
  ServiceConfig,
  RetryConfig,
  CheckDiagnostics,
} from "./serviceHealthChecker";

// VizieR query utilities
export { queryCatalog } from "./vizierQuery";

export type { CatalogSource, CatalogQueryResult } from "./vizierQuery";

// Input sanitization and validation
export {
  sanitizeId,
  sanitizePath,
  sanitizeQuery,
  sanitizeNumericId,
  buildApiUrl,
} from "./sanitization";

// Centralized logging
export { logger } from "./logger";

// Timestamp utilities
export {
  toDate,
  toISO,
  toUnixMillis,
  toUnixSeconds,
  nowISO,
  nowMillis,
  nowSeconds,
  formatTimestamp,
  formatDate,
  formatTime,
  formatRelative,
  isValidISO,
  isUnixSeconds,
  isUnixMillis,
  compareTimestamps,
  isWithin,
  isPast,
  isFuture,
  addDuration,
  subtractDuration,
  DURATION,
} from "./timestamp";

export type {
  ISOTimestamp,
  UnixMillis,
  UnixSeconds,
  TimestampInput,
} from "./timestamp";
