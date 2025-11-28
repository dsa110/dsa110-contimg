/**
 * Shape of error responses from the backend API.
 * All backend error endpoints should return this structure.
 */
export interface ErrorResponse {
  code: string; // short, stable identifier (e.g., "CAL_TABLE_MISSING")
  http_status: number; // numeric HTTP status code (e.g., 400)
  user_message: string; // user-friendly message
  action: string; // suggested action for the user
  ref_id: string; // job/run id for log correlation
  details?: Record<string, unknown>; // optional structured context (paths, params)
  trace_id?: string; // optional trace ID for log correlation
  doc_anchor?: string; // optional documentation anchor slug
}

/**
 * Severity levels for error display styling.
 */
export type ErrorSeverity = "info" | "warn" | "error";

/**
 * Mapped error for UI display, produced by errorMapper.
 */
export interface MappedError {
  user_message: string;
  action: string;
  severity: ErrorSeverity;
  ref_id?: string;
  details?: Record<string, unknown>;
  trace_id?: string;
  doc_anchor?: string;
}
