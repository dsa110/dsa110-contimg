import React, { ReactNode } from "react";
import { ErrorBoundary } from "./ErrorBoundary";

/**
 * Props for WidgetErrorBoundary component.
 */
export interface WidgetErrorBoundaryProps {
  /** Content to render */
  children: ReactNode;
  /** Name of the widget (for error message) */
  widgetName: string;
  /** Height of the placeholder when error occurs */
  minHeight?: number | string;
  /** Custom class name */
  className?: string;
  /** Key that resets the boundary when changed */
  resetKey?: string | number;
}

/**
 * Specialized error boundary for visualization widgets.
 *
 * Provides a consistent fallback UI for widgets like charts,
 * maps, and other complex visualizations that may fail to render.
 *
 * @example
 * ```tsx
 * <WidgetErrorBoundary widgetName="Sky Viewer" minHeight={400}>
 *   <AladinLiteViewer ra={180} dec={45} />
 * </WidgetErrorBoundary>
 * ```
 */
export const WidgetErrorBoundary: React.FC<WidgetErrorBoundaryProps> = ({
  children,
  widgetName,
  minHeight = 200,
  className = "",
  resetKey,
}) => {
  const fallback = (
    <div
      className={`p-6 bg-gray-100 rounded-lg border border-gray-200 flex flex-col items-center justify-center text-center ${className}`}
      style={{ minHeight: typeof minHeight === "number" ? `${minHeight}px` : minHeight }}
    >
      <div className="text-gray-400 text-3xl mb-3">📊</div>
      <p className="text-gray-600 font-medium mb-2">Unable to load {widgetName}</p>
      <p className="text-gray-500 text-sm mb-4">There was a problem rendering this component.</p>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
      >
        Reload page
      </button>
    </div>
  );

  return (
    <ErrorBoundary
      fallback={fallback}
      resetKey={resetKey}
      onError={(error) => {
        console.error(`Widget "${widgetName}" failed to render:`, error);
      }}
    >
      {children}
    </ErrorBoundary>
  );
};

export default WidgetErrorBoundary;
