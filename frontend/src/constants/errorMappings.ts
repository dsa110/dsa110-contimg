import type { ErrorSeverity } from "../types/errors";

/**
 * Error mapping entry for UI display.
 * Uses plain language—avoid jargon (e.g., use "Service paused" instead of "circuit open").
 */
export interface ErrorMapping {
  user_message: string;
  action: string;
  severity: ErrorSeverity;
  doc_anchor?: string;
}

/**
 * Error code to UI mapping table.
 * Codes are UPPER_SNAKE and stable across releases.
 */
export const errorMappings: Record<string, ErrorMapping> = {
  CAL_TABLE_MISSING: {
    user_message: "Calibration table not found for this Measurement Set",
    action: "Re-run calibration or choose an existing table",
    severity: "warn",
    doc_anchor: "calibration_missing_table",
  },
  CAL_APPLY_FAILED: {
    user_message: "Calibration apply failed",
    action: "Inspect cal logs; retry apply",
    severity: "error",
    doc_anchor: "calibration_apply_failed",
  },
  IMAGE_CLEAN_FAILED: {
    user_message: "Imaging step failed",
    action: "Check imaging parameters; retry",
    severity: "error",
    doc_anchor: "imaging_tclean_failed",
  },
  PHOTOMETRY_BAD_COORDS: {
    user_message: "Invalid coordinates for photometry",
    action: "Verify RA/Dec or region selection",
    severity: "warn",
    doc_anchor: "photometry_bad_coords",
  },
  MS_NOT_FOUND: {
    user_message: "Measurement Set not found",
    action: "Confirm path exists; rescan MS directory",
    severity: "error",
    doc_anchor: "ms_not_found",
  },
  PRODUCTS_DB_UNAVAILABLE: {
    user_message: "Products database unavailable",
    action: "Check DB path/permissions; retry",
    severity: "error",
    doc_anchor: "db_unavailable",
  },
  STREAMING_STALE_STATUS: {
    user_message: "Streaming status is stale",
    action: "Verify streaming service is running",
    severity: "warn",
    doc_anchor: "streaming_stale",
  },
  ABSURD_DISABLED: {
    user_message: "Task queue service is disabled",
    action: "Enable queue service or proceed without it",
    severity: "info",
  },
  RATE_LIMITED: {
    user_message: "Too many requests",
    action: "Wait and retry; reduce polling",
    severity: "warn",
  },
  VALIDATION_FAILED: {
    user_message: "Input validation failed",
    action: "Fix highlighted fields and retry",
    severity: "warn",
  },
  NETWORK_ERROR: {
    user_message: "Unable to reach the server",
    action: "Check your connection and try again",
    severity: "error",
  },
};
