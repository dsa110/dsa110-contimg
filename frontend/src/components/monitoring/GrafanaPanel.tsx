/**
 * GrafanaPanel Component
 *
 * Embeds individual Grafana dashboard panels via iframe.
 * Supports theming, time range selection, and responsive sizing.
 *
 * @example
 * ```tsx
 * <GrafanaPanel
 *   dashboardUid="pipeline-overview"
 *   panelId={1}
 *   height={300}
 *   from="now-1h"
 *   to="now"
 * />
 * ```
 */

import React, { useState, useCallback, useMemo } from "react";
import { GRAFANA_CONFIG } from "../../config";

export interface GrafanaPanelProps {
  /** Grafana dashboard UID */
  dashboardUid: string;
  /** Panel ID within the dashboard */
  panelId: number;
  /** Height of the embedded panel in pixels */
  height?: number;
  /** Time range start (e.g., "now-1h", "now-6h", "now-24h") */
  from?: string;
  /** Time range end (e.g., "now") */
  to?: string;
  /** Theme override (defaults to system preference) */
  theme?: "light" | "dark";
  /** Additional CSS class */
  className?: string;
  /** Grafana organization ID */
  orgId?: number;
  /** Panel title for accessibility */
  title?: string;
  /** Whether to show refresh control */
  showRefresh?: boolean;
  /** Auto-refresh interval in seconds (0 = disabled) */
  refreshInterval?: number;
  /** Query variables to pass to the dashboard */
  variables?: Record<string, string>;
}

/**
 * Loading skeleton for the panel
 */
function PanelSkeleton({ height }: { height: number }) {
  return (
    <div
      className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded-lg flex items-center justify-center"
      style={{ height }}
    >
      <div className="text-gray-400 dark:text-gray-500 flex items-center gap-2">
        <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        <span>Loading panel...</span>
      </div>
    </div>
  );
}

/**
 * Error state for panel load failures
 */
function PanelError({
  height,
  onRetry,
  message,
}: {
  height: number;
  onRetry: () => void;
  message?: string;
}) {
  return (
    <div
      className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex flex-col items-center justify-center gap-2"
      style={{ height }}
    >
      <svg
        className="w-8 h-8 text-red-500"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      <p className="text-sm text-red-700 dark:text-red-300">
        {message || "Failed to load Grafana panel"}
      </p>
      <button
        onClick={onRetry}
        className="px-3 py-1 text-sm bg-red-100 dark:bg-red-800 text-red-700 dark:text-red-200 rounded hover:bg-red-200 dark:hover:bg-red-700 transition-colors"
      >
        Retry
      </button>
    </div>
  );
}

/**
 * Embeds a single Grafana dashboard panel via iframe.
 */
export function GrafanaPanel({
  dashboardUid,
  panelId,
  height = 300,
  from = "now-1h",
  to = "now",
  theme,
  className = "",
  orgId = 1,
  title,
  showRefresh = false,
  refreshInterval = 0,
  variables = {},
}: GrafanaPanelProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  // Detect system theme if not overridden
  const effectiveTheme = useMemo(() => {
    if (theme) return theme;
    if (typeof window !== "undefined") {
      return window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    }
    return "dark";
  }, [theme]);

  // Build the panel URL with all parameters
  const panelUrl = useMemo(() => {
    const baseUrl = GRAFANA_CONFIG.baseUrl;
    const params = new URLSearchParams({
      orgId: orgId.toString(),
      panelId: panelId.toString(),
      from,
      to,
      theme: effectiveTheme,
    });

    // Add refresh interval if specified
    if (refreshInterval > 0) {
      params.set("refresh", `${refreshInterval}s`);
    }

    // Add any dashboard variables
    Object.entries(variables).forEach(([key, value]) => {
      params.set(`var-${key}`, value);
    });

    return `${baseUrl}/d-solo/${dashboardUid}?${params.toString()}`;
  }, [
    dashboardUid,
    panelId,
    from,
    to,
    effectiveTheme,
    orgId,
    refreshInterval,
    variables,
    retryKey, // Force URL regeneration on retry
  ]);

  const handleLoad = useCallback(() => {
    setIsLoading(false);
    setHasError(false);
  }, []);

  const handleError = useCallback(() => {
    setIsLoading(false);
    setHasError(true);
  }, []);

  const handleRetry = useCallback(() => {
    setIsLoading(true);
    setHasError(false);
    setRetryKey((k) => k + 1);
  }, []);

  const handleRefresh = useCallback(() => {
    setRetryKey((k) => k + 1);
    setIsLoading(true);
  }, []);

  if (hasError) {
    return (
      <PanelError
        height={height}
        onRetry={handleRetry}
        message="Could not connect to Grafana. Ensure Grafana is running and embedding is enabled."
      />
    );
  }

  return (
    <div className={`relative ${className}`}>
      {/* Refresh button */}
      {showRefresh && !isLoading && (
        <button
          onClick={handleRefresh}
          className="absolute top-2 right-2 z-10 p-1.5 bg-gray-100 dark:bg-gray-700 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          title="Refresh panel"
          aria-label="Refresh Grafana panel"
        >
          <svg
            className="w-4 h-4 text-gray-600 dark:text-gray-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </button>
      )}

      {/* Loading skeleton */}
      {isLoading && <PanelSkeleton height={height} />}

      {/* Iframe (hidden while loading) */}
      <iframe
        key={retryKey}
        src={panelUrl}
        width="100%"
        height={height}
        frameBorder="0"
        className={`rounded-lg ${isLoading ? "invisible absolute" : ""}`}
        title={title || `Grafana Panel ${panelId}`}
        onLoad={handleLoad}
        onError={handleError}
        loading="lazy"
        sandbox="allow-scripts allow-same-origin"
      />
    </div>
  );
}

export default GrafanaPanel;
