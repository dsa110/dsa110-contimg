import { errorMappings, type ErrorMapping } from "../constants/errorMappings";
import type { ErrorResponse, MappedError } from "../types/errors";

const FALLBACK_ERROR: ErrorMapping = {
  user_message: "Request failed",
  action: "Please try again later",
  severity: "error",
};

/**
 * Normalize backend error responses into a consistent shape for the UI.
 * Uses plain language and keeps the remediation action close to the message.
 *
 * @param errorResponse - Partial error response from the backend
 * @returns MappedError ready for UI display
 */
export const mapErrorResponse = (errorResponse: Partial<ErrorResponse> = {}): MappedError => {
  const mapping = errorResponse.code ? errorMappings[errorResponse.code] : undefined;
  const base = mapping ?? FALLBACK_ERROR;

  return {
    user_message: base.user_message,
    action: base.action,
    severity: base.severity,
    ref_id: errorResponse.ref_id,
    details: errorResponse.details,
    trace_id: errorResponse.trace_id,
    // Prefer mapped doc anchor, otherwise pass through provided value
    doc_anchor: mapping?.doc_anchor ?? errorResponse.doc_anchor,
  };
};
