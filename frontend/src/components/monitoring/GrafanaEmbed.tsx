/**
 * GrafanaEmbed Component
 *
 * Embeds a full Grafana dashboard with kiosk mode.
 * Useful for dedicated monitoring pages.
 *
 * @example
 * ```tsx
 * <GrafanaEmbed
 *   dashboardUid="pipeline-overview"
 *   height="100vh"
 *   kioskMode="tv"
 * />
 * ```
 */

import React, { useState, useCallback, useMemo } from "react";
import { GRAFANA_CONFIG } from "../../config";

export type KioskMode = "off" | "tv" | "full";

export interface GrafanaEmbedProps {
  /** Grafana dashboard UID */
  dashboardUid: string;
  /** Height of the embedded dashboard (CSS value) */
  height?: string | number;
  /** Kiosk mode: "off" (normal), "tv" (no sidebar), "full" (minimal UI) */
  kioskMode?: KioskMode;
  /** Time range start (e.g., "now-1h") */
  from?: string;
  /** Time range end (e.g., "now") */
  to?: string;
  /** Theme override */
  theme?: "light" | "dark";
  /** Additional CSS class */
  className?: string;
  /** Grafana organization ID */
  orgId?: number;
  /** Title for accessibility */
  title?: string;
  /** Auto-refresh interval (e.g., "5s", "1m") */
  refresh?: string;
  /** Query variables to pass to the dashboard */
  variables?: Record<string, string>;
}

/**
 * Loading state component
 */
function LoadingOverlay() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-lg">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
        <p className="text-gray-600 dark:text-gray-300">
          Loading Grafana dashboard...
        </p>
      </div>
    </div>
  );
}

/**
 * Error state component
 */
function ErrorOverlay({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-red-50 dark:bg-red-900/20 rounded-lg">
      <div className="text-center">
        <svg
          className="w-12 h-12 text-red-500 mx-auto mb-4"
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
        <p className="text-red-700 dark:text-red-300 mb-2">
          Failed to load Grafana dashboard
        </p>
        <p className="text-sm text-red-600 dark:text-red-400 mb-4">
          Ensure Grafana is running at {GRAFANA_CONFIG.baseUrl}
        </p>
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
        >
          Retry
        </button>
      </div>
    </div>
  );
}

/**
 * Embeds a full Grafana dashboard.
 */
export function GrafanaEmbed({
  dashboardUid,
  height = "600px",
  kioskMode = "tv",
  from = "now-1h",
  to = "now",
  theme,
  className = "",
  orgId = 1,
  title,
  refresh,
  variables = {},
}: GrafanaEmbedProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  // Detect system theme
  const effectiveTheme = useMemo(() => {
    if (theme) return theme;
    if (typeof window !== "undefined") {
      return window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    }
    return "dark";
  }, [theme]);

  // Build the dashboard URL
  const dashboardUrl = useMemo(() => {
    const baseUrl = GRAFANA_CONFIG.baseUrl;
    const params = new URLSearchParams({
      orgId: orgId.toString(),
      from,
      to,
      theme: effectiveTheme,
    });

    // Add kiosk mode
    if (kioskMode !== "off") {
      params.set("kiosk", kioskMode);
    }

    // Add refresh interval
    if (refresh) {
      params.set("refresh", refresh);
    }

    // Add dashboard variables
    Object.entries(variables).forEach(([key, value]) => {
      params.set(`var-${key}`, value);
    });

    return `${baseUrl}/d/${dashboardUid}?${params.toString()}`;
  }, [
    dashboardUid,
    from,
    to,
    effectiveTheme,
    orgId,
    kioskMode,
    refresh,
    variables,
    retryKey,
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

  const cssHeight = typeof height === "number" ? `${height}px` : height;

  return (
    <div className={`relative ${className}`} style={{ height: cssHeight }}>
      {isLoading && <LoadingOverlay />}
      {hasError && <ErrorOverlay onRetry={handleRetry} />}

      <iframe
        key={retryKey}
        src={dashboardUrl}
        width="100%"
        height="100%"
        frameBorder="0"
        className={`rounded-lg ${isLoading || hasError ? "invisible" : ""}`}
        title={title || `Grafana Dashboard: ${dashboardUid}`}
        onLoad={handleLoad}
        onError={handleError}
        loading="lazy"
        sandbox="allow-scripts allow-same-origin"
      />
    </div>
  );
}

export default GrafanaEmbed;
