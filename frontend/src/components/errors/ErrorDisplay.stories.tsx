import type { Meta, StoryObj } from "@storybook/react";
import ErrorDisplay from "./ErrorDisplay";

/**
 * ErrorDisplay shows user-friendly error messages with optional technical details.
 *
 * Features:
 * - User-friendly message
 * - Expandable technical details
 * - Error code display
 * - Trace ID for debugging
 * - Retry action support
 */
const meta = {
  title: "Components/Errors/ErrorDisplay",
  component: ErrorDisplay,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
} satisfies Meta<typeof ErrorDisplay>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Simple error message
 */
export const Simple: Story = {
  args: {
    error: {
      code: "DATA_LOAD_FAILED",
      http_status: 500,
      user_message:
        "Unable to retrieve the requested information. Please try again.",
      action: "Retry the request or contact support if the issue persists.",
      ref_id: "job-001",
    },
  },
};

/**
 * Error with technical details
 */
export const WithDetails: Story = {
  args: {
    error: {
      code: "NETWORK_ERROR",
      http_status: 503,
      user_message:
        "Unable to connect to the server. Please check your network connection.",
      action: "Check your network connection and retry.",
      ref_id: "req-002",
      details: {
        statusCode: 503,
        endpoint: "/api/sources",
        timestamp: new Date().toISOString(),
      },
    },
  },
};

/**
 * Error with error code
 */
export const WithErrorCode: Story = {
  args: {
    error: {
      code: "MS_NOT_FOUND",
      http_status: 404,
      user_message:
        "The requested measurement set could not be found in the archive.",
      action: "Verify the measurement set path and try again.",
      ref_id: "ms-003",
    },
  },
};

/**
 * Error with trace ID
 */
export const WithTraceId: Story = {
  args: {
    error: {
      code: "INTERNAL_ERROR",
      http_status: 500,
      user_message: "An unexpected error occurred. Our team has been notified.",
      action: "Please try again later or contact support.",
      ref_id: "err-004",
      trace_id: "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    },
  },
};

/**
 * Complete error with all fields
 */
export const Complete: Story = {
  args: {
    error: {
      code: "CAL_TABLE_MISSING",
      http_status: 400,
      user_message:
        "The calibration data required for this image is missing. Please run calibration first.",
      action: "Run the calibration pipeline before attempting imaging.",
      ref_id: "cal-005",
      details: {
        msPath: "/data/ms/58000_000.ms",
        missingTable: "ANTENNA",
        attemptedAt: new Date().toISOString(),
      },
      trace_id: "f7e8d9c0-b1a2-3456-7890-1234567890ab",
      doc_anchor: "calibration-tables",
    },
  },
};

/**
 * Network error
 */
export const NetworkError: Story = {
  args: {
    error: {
      code: "NETWORK_ERROR",
      message: "Failed to fetch",
      userMessage:
        "Unable to connect to the server. Please check your internet connection and try again.",
      details: {
        url: "https://api.example.com/data",
        error: "net::ERR_INTERNET_DISCONNECTED",
      },
    },
  },
};

/**
 * Validation error
 */
export const ValidationError: Story = {
  args: {
    error: {
      code: "INVALID_COORDINATES",
      message: "Validation failed",
      userMessage:
        "The coordinates you entered are invalid. RA must be 0-360° and Dec must be -90 to +90°.",
      details: {
        field: "coordinates",
        provided: { ra: 400, dec: 100 },
        valid: { ra: "0-360", dec: "-90 to +90" },
      },
    },
  },
};

/**
 * Permission error
 */
export const PermissionError: Story = {
  args: {
    error: {
      code: "FORBIDDEN",
      message: "Access denied",
      userMessage: "You don't have permission to access this resource.",
      details: {
        resource: "/api/admin/users",
        requiredRole: "admin",
        userRole: "viewer",
      },
    },
  },
};

/**
 * Rate limit error
 */
export const RateLimitError: Story = {
  args: {
    error: {
      code: "RATE_LIMIT_EXCEEDED",
      message: "Too many requests",
      userMessage:
        "You've made too many requests. Please wait a moment and try again.",
      details: {
        limit: 100,
        window: "1 hour",
        retryAfter: "45 minutes",
      },
    },
  },
};

/**
 * Timeout error
 */
export const TimeoutError: Story = {
  args: {
    error: {
      code: "TIMEOUT",
      message: "Request timeout",
      userMessage:
        "The request took too long to complete. The server might be busy. Please try again.",
      details: {
        timeout: "30000ms",
        elapsed: "30001ms",
      },
    },
  },
};

/**
 * Multiple errors in a list
 */
export const MultipleErrors: Story = {
  render: () => (
    <div className="space-y-4">
      <ErrorDisplay
        error={{
          message: "Error 1",
          userMessage: "First error occurred",
        }}
      />
      <ErrorDisplay
        error={{
          message: "Error 2",
          userMessage: "Second error occurred",
        }}
      />
      <ErrorDisplay
        error={{
          message: "Error 3",
          userMessage: "Third error occurred",
        }}
      />
    </div>
  ),
};
