import React from "react";
import type { ErrorResponse } from "../../types/errors";
import { mapErrorResponse } from "../../utils/errorMapper";
import ErrorDetailsExpander from "./ErrorDetailsExpander";
import ErrorActionHint from "./ErrorActionHint";

interface ErrorDisplayProps {
  error: ErrorResponse;
  onRetry?: () => void;
}

const severityStyles: Record<string, React.CSSProperties> = {
  error: { borderLeftColor: "#dc3545" },
  warn: { borderLeftColor: "#ffc107" },
  info: { borderLeftColor: "#17a2b8" },
};

/**
 * Unified error display component.
 * Takes a raw ErrorResponse from the backend, maps it to user-friendly text,
 * and renders with severity-appropriate styling, expandable details, and action links.
 */
const ErrorDisplay: React.FC<ErrorDisplayProps> = ({ error, onRetry }) => {
  const mapped = mapErrorResponse(error);

  return (
    <div
      className="error-display"
      style={{
        padding: "16px",
        borderLeft: "4px solid",
        backgroundColor: "#f8f9fa",
        borderRadius: "4px",
        ...severityStyles[mapped.severity],
      }}
    >
      <h3 style={{ margin: "0 0 8px", fontSize: "1.1em" }}>{mapped.user_message}</h3>
      <p style={{ margin: "0 0 12px", color: "#666" }}>{mapped.action}</p>
      {mapped.details && (
        <ErrorDetailsExpander details={mapped.details} traceId={mapped.trace_id} />
      )}
      <ErrorActionHint refId={mapped.ref_id} docAnchor={mapped.doc_anchor} />
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            marginTop: "12px",
            padding: "8px 16px",
            backgroundColor: "#0066cc",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
          }}
        >
          Retry
        </button>
      )}
    </div>
  );
};

export default ErrorDisplay;
