import React from "react";

interface ErrorActionHintProps {
  refId?: string;
  docAnchor?: string;
}

/**
 * Renders action links for error troubleshooting.
 * Shows "View logs" link when refId is available, and "Troubleshoot" link
 * when docAnchor is provided for documentation deep-linking.
 */
const ErrorActionHint: React.FC<ErrorActionHintProps> = ({ refId, docAnchor }) => {
  if (!refId && !docAnchor) return null;

  return (
    <div className="error-action-hint" style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
      {refId && (
        <a href={`/logs/${refId}`} className="error-link">
          View logs
        </a>
      )}
      {docAnchor && (
        <a href={`/docs#${docAnchor}`} className="error-link">
          Troubleshoot
        </a>
      )}
    </div>
  );
};

export default ErrorActionHint;
