import React, { Component, ErrorInfo, ReactNode } from "react";
import Card from "../common/Card";

/**
 * Props for ErrorBoundary component.
 */
export interface ErrorBoundaryProps {
  /** Content to render when no error */
  children: ReactNode;
  /** Custom fallback UI (optional) */
  fallback?: ReactNode;
  /** Callback when error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Key that resets the boundary when changed */
  resetKey?: string | number;
  /** Custom class name for wrapper */
  className?: string;
}

/**
 * Internal state for ErrorBoundary.
 */
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * React Error Boundary for catching render errors.
 *
 * Wraps components to gracefully handle JavaScript errors during rendering.
 * When an error occurs, it displays a fallback UI instead of crashing.
 *
 * @example
 * ```tsx
 * <ErrorBoundary
 *   fallback={<div>Something went wrong</div>}
 *   onError={(error) => logError(error)}
 * >
 *   <MyComponent />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  /**
   * Update state when error is thrown.
   */
  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  /**
   * Log error details when caught.
   */
  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  /**
   * Reset error state when resetKey changes.
   */
  componentDidUpdate(prevProps: ErrorBoundaryProps): void {
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false, error: null });
    }
  }

  /**
   * Reset the error boundary manually.
   */
  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <div className={this.props.className}>
          <Card className="bg-red-50 border-red-200">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 text-red-500 text-xl">⚠️</div>
              <div className="flex-1">
                <h3 className="text-red-800 font-semibold mb-1">Something went wrong</h3>
                <p className="text-red-600 text-sm mb-3">
                  {this.state.error?.message || "An unexpected error occurred"}
                </p>
                <button
                  type="button"
                  onClick={this.handleReset}
                  className="btn btn-secondary text-sm"
                >
                  Try Again
                </button>
              </div>
            </div>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
