import React from "react";

export interface SimpleErrorAlertProps {
  /** Error message to display */
  message: string;
  /** Optional title (defaults to "Error") */
  title?: string;
  /** Optional retry callback */
  onRetry?: () => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Simple inline error alert for displaying error messages.
 * Use this for API errors and other simple error cases.
 * For more complex errors with details and action hints, use ErrorDisplay.
 */
const SimpleErrorAlert: React.FC<SimpleErrorAlertProps> = ({
  message,
  title,
  onRetry,
  className = "",
}) => {
  return (
    <div
      className={`bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg ${className}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <svg
          className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5"
          fill="currentColor"
          viewBox="0 0 20 20"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
            clipRule="evenodd"
          />
        </svg>
        <div className="flex-1">
          {title && <p className="font-semibold mb-1">{title}</p>}
          <p className="text-sm">{message}</p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-2 text-sm font-medium text-red-800 hover:text-red-900 underline"
              aria-label="Retry the failed operation"
            >
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SimpleErrorAlert;
