/**
 * Error Recovery Suggestions
 * Provides actionable recovery suggestions for common errors
 */

import { ErrorType, type ClassifiedError } from "./errorUtils";

export interface RecoverySuggestion {
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

/**
 * Get recovery suggestions for an error
 */
export function getRecoverySuggestions(error: ClassifiedError): RecoverySuggestion[] {
  const suggestions: RecoverySuggestion[] = [];

  switch (error.type) {
    case ErrorType.NETWORK:
      suggestions.push({
        title: "Check your internet connection",
        description: "Verify that you are connected to the internet and try again.",
        action: {
          label: "Retry",
          onClick: () => window.location.reload(),
        },
      });
      suggestions.push({
        title: "Check if the server is running",
        description: "The backend API may be unavailable. Contact your administrator.",
      });
      break;

    case ErrorType.TIMEOUT:
      suggestions.push({
        title: "The request took too long",
        description: "The server may be experiencing high load. Try again in a moment.",
        action: {
          label: "Retry",
          onClick: () => window.location.reload(),
        },
      });
      break;

    case ErrorType.SERVER:
      if (error.statusCode === 500) {
        suggestions.push({
          title: "Server error",
          description: "The server encountered an unexpected error. This has been logged.",
          action: {
            label: "Refresh page",
            onClick: () => window.location.reload(),
          },
        });
      } else if (error.statusCode === 503) {
        suggestions.push({
          title: "Service unavailable",
          description: "The service is temporarily unavailable. Please try again later.",
          action: {
            label: "Retry",
            onClick: () => window.location.reload(),
          },
        });
      }
      break;

    case ErrorType.CLIENT:
      if (error.statusCode === 401) {
        suggestions.push({
          title: "Authentication required",
          description: "Your session may have expired. Please log in again.",
          action: {
            label: "Go to login",
            onClick: () => {
              // Clear auth tokens and redirect
              localStorage.removeItem("auth_token");
              window.location.href = "/login";
            },
          },
        });
      } else if (error.statusCode === 403) {
        suggestions.push({
          title: "Permission denied",
          description: "You don't have permission to perform this action.",
        });
      } else if (error.statusCode === 404) {
        suggestions.push({
          title: "Resource not found",
          description: "The requested resource could not be found.",
          action: {
            label: "Go to dashboard",
            onClick: () => {
              window.location.href = "/dashboard";
            },
          },
        });
      } else if (error.statusCode === 429) {
        suggestions.push({
          title: "Too many requests",
          description: "You've made too many requests. Please wait a moment before trying again.",
          action: {
            label: "Retry in 30s",
            onClick: () => {
              setTimeout(() => window.location.reload(), 30000);
            },
          },
        });
      }
      break;

    case ErrorType.UNKNOWN:
      suggestions.push({
        title: "Unexpected error",
        description: "An unexpected error occurred. Try refreshing the page.",
        action: {
          label: "Refresh page",
          onClick: () => window.location.reload(),
        },
      });
      break;
  }

  // Always add a generic suggestion if no specific ones
  if (suggestions.length === 0) {
    suggestions.push({
      title: "Try refreshing the page",
      description: "Sometimes a simple refresh can resolve the issue.",
      action: {
        label: "Refresh",
        onClick: () => window.location.reload(),
      },
    });
  }

  return suggestions;
}
