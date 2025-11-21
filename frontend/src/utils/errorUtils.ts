/**
 * Error classification and utility functions for error handling
 */

export const ErrorType = {
  NETWORK: "network",
  SERVER: "server",
  CLIENT: "client",
  TIMEOUT: "timeout",
  UNKNOWN: "unknown",
} as const;

export type ErrorType = (typeof ErrorType)[keyof typeof ErrorType];

export interface ClassifiedError {
  type: ErrorType;
  message: string;
  statusCode?: number;
  retryable: boolean;
  originalError: unknown;
}

/**
 * Classify an error to determine its type and whether it's retryable
 */
export function classifyError(error: unknown): ClassifiedError {
  const defaultError: ClassifiedError = {
    type: ErrorType.UNKNOWN,
    message: "An unknown error occurred",
    retryable: false,
    originalError: error,
  };

  if (!error) {
    return defaultError;
  }

  // Axios errors
  if (typeof error === "object" && "isAxiosError" in error && error.isAxiosError) {
    const axiosError = error as {
      code?: string;
      message?: string;
      response?: { status?: number; statusText?: string };
      request?: unknown;
    };

    // Network errors (no response received)
    if (axiosError.code === "ECONNABORTED" || axiosError.code === "ETIMEDOUT") {
      return {
        type: ErrorType.TIMEOUT,
        message: axiosError.message || "Request timed out",
        retryable: true,
        originalError: error,
      };
    }

    if (!axiosError.response && axiosError.request) {
      return {
        type: ErrorType.NETWORK,
        message: "Network error: Unable to reach server",
        retryable: true,
        originalError: error,
      };
    }

    // HTTP response errors
    if (axiosError.response) {
      const status = axiosError.response.status || 500;
      const isRetryable = status >= 500 || status === 429 || status === 408;

      return {
        type: status >= 500 ? ErrorType.SERVER : ErrorType.CLIENT,
        message: axiosError.response.statusText || `HTTP ${status}`,
        statusCode: status,
        retryable: isRetryable,
        originalError: error,
      };
    }
  }

  // Generic Error objects
  if (error instanceof Error) {
    const message = error.message || "An error occurred";
    const isNetworkError =
      message.includes("Network") ||
      message.includes("fetch") ||
      message.includes("Failed to fetch");

    return {
      type: isNetworkError ? ErrorType.NETWORK : ErrorType.UNKNOWN,
      message,
      retryable: isNetworkError,
      originalError: error,
    };
  }

  return defaultError;
}

/**
 * Check if an error is retryable
 */
export function isRetryableError(error: unknown): boolean {
  try {
    return classifyError(error).retryable;
  } catch {
    // If classification fails, assume error is not retryable
    return false;
  }
}

/**
 * Get user-friendly error message
 */
export function getUserFriendlyMessage(error: unknown): string {
  const classified = classifyError(error);

  switch (classified.type) {
    case ErrorType.NETWORK:
      return "Unable to connect to the server. Please check your internet connection.";
    case ErrorType.TIMEOUT:
      return "The request took too long. Please try again.";
    case ErrorType.SERVER:
      return "Server error occurred. Please try again later.";
    case ErrorType.CLIENT:
      if (classified.statusCode === 401) {
        return "Access denied.";
      }
      if (classified.statusCode === 403) {
        return "You do not have permission to perform this action.";
      }
      if (classified.statusCode === 404) {
        return "The requested resource was not found.";
      }
      return "Invalid request. Please check your input and try again.";
    default:
      return classified.message;
  }
}

/**
 * Sanitize a navigation path to prevent open redirect and XSS attacks
 *
 * Security: This function validates paths before using them with window.location.href
 * to prevent open redirect attacks (e.g., redirecting to malicious external sites)
 * and XSS via javascript: URLs.
 *
 * @param path - The path to sanitize
 * @returns Sanitized path if valid, null if invalid
 *
 * @example
 * sanitizePath("/dashboard") // returns "/dashboard"
 * sanitizePath("https://evil.com") // returns null
 * sanitizePath("javascript:alert('xss')") // returns null
 * sanitizePath("//evil.com") // returns null
 */
export function sanitizePath(path: string): string | null {
  if (!path || typeof path !== "string") {
    return null;
  }

  // Trim whitespace
  const trimmed = path.trim();

  // Reject empty paths
  if (!trimmed) {
    return null;
  }

  // Reject absolute URLs (http://, https://, ftp://, etc.)
  if (/^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(trimmed)) {
    // Matches any protocol (http:, https:, javascript:, data:, etc.)
    return null;
  }

  // Reject protocol-relative URLs (//example.com)
  if (trimmed.startsWith("//")) {
    return null;
  }

  // Only allow relative paths starting with /
  if (!trimmed.startsWith("/")) {
    return null;
  }

  // Remove path traversal sequences (..) for security
  // This prevents attempts to escape the application's path structure
  if (trimmed.includes("..")) {
    return null;
  }

  // Allow valid relative paths like /dashboard, /users/123, etc.
  // Basic validation: should contain only alphanumeric, /, -, _, and query string characters
  if (!/^\/[a-zA-Z0-9\/\-_?#=&.]*$/.test(trimmed)) {
    return null;
  }

  return trimmed;
}
