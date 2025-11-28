import React, { useState } from "react";

interface ErrorDetailsExpanderProps {
  details: Record<string, unknown>;
  traceId?: string;
}

/**
 * Expandable section for error details and trace ID.
 * Hidden when no content is available.
 */
const ErrorDetailsExpander: React.FC<ErrorDetailsExpanderProps> = ({ details, traceId }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const hasContent = Object.keys(details).length > 0 || traceId;
  if (!hasContent) return null;

  return (
    <div className="error-details-expander" style={{ marginTop: "8px" }}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        type="button"
        style={{
          background: "none",
          border: "1px solid #ccc",
          padding: "4px 8px",
          cursor: "pointer",
          borderRadius: "4px",
        }}
      >
        {isExpanded ? "Hide Details" : "Show Details"}
      </button>
      {isExpanded && (
        <div className="error-details-content" style={{ marginTop: "8px" }}>
          {Object.keys(details).length > 0 && (
            <pre
              style={{
                background: "#f5f5f5",
                padding: "8px",
                borderRadius: "4px",
                overflow: "auto",
              }}
            >
              {JSON.stringify(details, null, 2)}
            </pre>
          )}
          {traceId && (
            <p className="trace-id" style={{ fontSize: "0.85em", color: "#666", marginTop: "4px" }}>
              Trace ID: {traceId}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default ErrorDetailsExpander;
