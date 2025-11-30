/**
 * Input Sanitization Utilities
 *
 * Centralized functions for sanitizing and encoding user inputs
 * to prevent security issues and ensure consistent handling.
 *
 * Usage:
 *   import { sanitizeId, sanitizePath } from '@/utils/sanitization';
 *   const url = `/images/${sanitizeId(imageId)}`;
 */

/**
 * Sanitize and encode a resource ID for use in URLs
 *
 * @param id - Resource identifier
 * @returns URL-safe encoded ID
 */
export function sanitizeId(id: string | undefined | null): string {
  if (!id) {
    return "";
  }

  // Trim whitespace and encode for URL safety
  return encodeURIComponent(id.trim());
}

/**
 * Sanitize and encode a file path for use in URLs
 *
 * @param path - File path
 * @returns URL-safe encoded path
 */
export function sanitizePath(path: string | undefined | null): string {
  if (!path) {
    return "";
  }

  // Trim and encode the entire path
  return encodeURIComponent(path.trim());
}

/**
 * Sanitize a search query string
 *
 * @param query - Search query
 * @returns Sanitized query string
 */
export function sanitizeQuery(query: string | undefined | null): string {
  if (!query) {
    return "";
  }

  // Trim and remove potentially dangerous characters
  return query
    .trim()
    .replace(/[<>]/g, "") // Remove angle brackets to prevent XSS
    .substring(0, 500); // Limit length
}

/**
 * Validate and sanitize a numeric ID
 *
 * @param id - Numeric identifier
 * @returns Parsed number or null if invalid
 */
export function sanitizeNumericId(id: string | number | undefined | null): number | null {
  if (id === undefined || id === null || id === "") {
    return null;
  }

  const parsed = typeof id === "number" ? id : parseFloat(id);

  return isNaN(parsed) ? null : parsed;
}

/**
 * Build API URL with sanitized path segments
 *
 * @param baseUrl - Base API URL
 * @param segments - Path segments to append
 * @returns Complete API URL
 */
export function buildApiUrl(baseUrl: string, ...segments: (string | number)[]): string {
  const sanitizedSegments = segments.map((segment) =>
    typeof segment === "number" ? segment.toString() : sanitizeId(segment)
  );

  return `${baseUrl}/${sanitizedSegments.join("/")}`;
}
