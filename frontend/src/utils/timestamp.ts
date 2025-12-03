/**
 * Timestamp Utilities
 *
 * Standardized timestamp handling across the application.
 *
 * CONVENTION:
 * - API timestamps: ISO 8601 strings (e.g., "2025-12-03T08:30:00.000Z")
 * - Internal/caching: Unix milliseconds (Date.now())
 * - Display: Formatted via toLocaleString() or formatRelativeTime()
 * - Prometheus: Unix seconds (standard for metrics)
 *
 * This module provides utilities to convert between formats consistently.
 */

// =============================================================================
// Types
// =============================================================================

/** ISO 8601 timestamp string */
export type ISOTimestamp = string;

/** Unix timestamp in milliseconds */
export type UnixMillis = number;

/** Unix timestamp in seconds (Prometheus format) */
export type UnixSeconds = number;

/** Any timestamp input type */
export type TimestampInput =
  | ISOTimestamp
  | UnixMillis
  | UnixSeconds
  | Date
  | null
  | undefined;

// =============================================================================
// Conversion Functions
// =============================================================================

/**
 * Convert any timestamp format to a Date object
 */
export function toDate(timestamp: TimestampInput): Date | null {
  if (timestamp === null || timestamp === undefined) {
    return null;
  }

  if (timestamp instanceof Date) {
    return timestamp;
  }

  if (typeof timestamp === "string") {
    const date = new Date(timestamp);
    return isNaN(date.getTime()) ? null : date;
  }

  if (typeof timestamp === "number") {
    // Heuristic: if < 1e12, assume seconds; otherwise milliseconds
    // (1e12 ms = year 2001, 1e12 s = year 33658)
    const millis = timestamp < 1e12 ? timestamp * 1000 : timestamp;
    return new Date(millis);
  }

  return null;
}

/**
 * Convert any timestamp to ISO string
 */
export function toISO(timestamp: TimestampInput): ISOTimestamp | null {
  const date = toDate(timestamp);
  return date ? date.toISOString() : null;
}

/**
 * Convert any timestamp to Unix milliseconds
 */
export function toUnixMillis(timestamp: TimestampInput): UnixMillis | null {
  const date = toDate(timestamp);
  return date ? date.getTime() : null;
}

/**
 * Convert any timestamp to Unix seconds (for Prometheus)
 */
export function toUnixSeconds(timestamp: TimestampInput): UnixSeconds | null {
  const millis = toUnixMillis(timestamp);
  return millis !== null ? Math.floor(millis / 1000) : null;
}

/**
 * Get current time as ISO string
 */
export function nowISO(): ISOTimestamp {
  return new Date().toISOString();
}

/**
 * Get current time as Unix milliseconds
 */
export function nowMillis(): UnixMillis {
  return Date.now();
}

/**
 * Get current time as Unix seconds
 */
export function nowSeconds(): UnixSeconds {
  return Math.floor(Date.now() / 1000);
}

// =============================================================================
// Formatting Functions
// =============================================================================

/**
 * Format timestamp for display (locale-aware)
 */
export function formatTimestamp(
  timestamp: TimestampInput,
  options?: Intl.DateTimeFormatOptions
): string {
  const date = toDate(timestamp);
  if (!date) return "—";

  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  };

  return date.toLocaleString(undefined, options ?? defaultOptions);
}

/**
 * Format timestamp as date only
 */
export function formatDate(timestamp: TimestampInput): string {
  const date = toDate(timestamp);
  if (!date) return "—";

  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/**
 * Format timestamp as time only
 */
export function formatTime(timestamp: TimestampInput): string {
  const date = toDate(timestamp);
  if (!date) return "—";

  return date.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Format timestamp as relative time (e.g., "5 minutes ago")
 */
export function formatRelative(
  timestamp: TimestampInput,
  relativeTo?: Date
): string {
  const date = toDate(timestamp);
  if (!date) return "—";

  const now = relativeTo ?? new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 0) {
    // Future time
    const absSec = Math.abs(diffSec);
    if (absSec < 60) return `in ${absSec}s`;
    const absMin = Math.floor(absSec / 60);
    if (absMin < 60) return `in ${absMin}m`;
    const absHour = Math.floor(absMin / 60);
    if (absHour < 24) return `in ${absHour}h`;
    const absDay = Math.floor(absHour / 24);
    return `in ${absDay}d`;
  }

  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 30) return `${diffDay}d ago`;

  return formatDate(date);
}

// =============================================================================
// Validation Functions
// =============================================================================

/**
 * Check if a string is a valid ISO timestamp
 */
export function isValidISO(value: unknown): value is ISOTimestamp {
  if (typeof value !== "string") return false;
  const date = new Date(value);
  return !isNaN(date.getTime()) && value.includes("T");
}

/**
 * Check if a number looks like Unix seconds (vs milliseconds)
 */
export function isUnixSeconds(value: number): boolean {
  // Unix seconds for reasonable dates (1970-2100) are < 5e9
  // Unix milliseconds for those dates are > 1e11
  return value < 1e11;
}

/**
 * Check if a number looks like Unix milliseconds
 */
export function isUnixMillis(value: number): boolean {
  return value >= 1e11;
}

// =============================================================================
// Comparison Functions
// =============================================================================

/**
 * Compare two timestamps
 * Returns negative if a < b, positive if a > b, 0 if equal
 */
export function compareTimestamps(
  a: TimestampInput,
  b: TimestampInput
): number {
  const aMillis = toUnixMillis(a) ?? 0;
  const bMillis = toUnixMillis(b) ?? 0;
  return aMillis - bMillis;
}

/**
 * Check if timestamp is within a duration from now
 */
export function isWithin(
  timestamp: TimestampInput,
  durationMs: number
): boolean {
  const millis = toUnixMillis(timestamp);
  if (millis === null) return false;
  return Math.abs(Date.now() - millis) <= durationMs;
}

/**
 * Check if timestamp is in the past
 */
export function isPast(timestamp: TimestampInput): boolean {
  const millis = toUnixMillis(timestamp);
  if (millis === null) return false;
  return millis < Date.now();
}

/**
 * Check if timestamp is in the future
 */
export function isFuture(timestamp: TimestampInput): boolean {
  const millis = toUnixMillis(timestamp);
  if (millis === null) return false;
  return millis > Date.now();
}

// =============================================================================
// Duration Helpers
// =============================================================================

/** Duration constants in milliseconds */
export const DURATION = {
  SECOND: 1000,
  MINUTE: 60 * 1000,
  HOUR: 60 * 60 * 1000,
  DAY: 24 * 60 * 60 * 1000,
  WEEK: 7 * 24 * 60 * 60 * 1000,
} as const;

/**
 * Add duration to timestamp
 */
export function addDuration(
  timestamp: TimestampInput,
  durationMs: number
): Date | null {
  const millis = toUnixMillis(timestamp);
  if (millis === null) return null;
  return new Date(millis + durationMs);
}

/**
 * Subtract duration from timestamp
 */
export function subtractDuration(
  timestamp: TimestampInput,
  durationMs: number
): Date | null {
  return addDuration(timestamp, -durationMs);
}
