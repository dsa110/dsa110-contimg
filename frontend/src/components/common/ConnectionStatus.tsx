/**
 * Connection status indicator component.
 *
 * Displays a banner when:
 * - Browser is offline
 * - API connectivity is lost
 * - Connection is degraded
 *
 * Auto-hides when connection is restored.
 */

import { useState, useEffect } from "react";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";

interface ConnectionStatusProps {
  /** Whether to show detailed diagnostics */
  showDetails?: boolean;
  /** Custom class names */
  className?: string;
}

export function ConnectionStatus({
  showDetails = false,
  className = "",
}: ConnectionStatusProps): JSX.Element | null {
  const status = useNetworkStatus({
    autoRefetchOnReconnect: true,
    degradedThreshold: 3,
  });

  const [isVisible, setIsVisible] = useState(false);
  const [showReconnected, setShowReconnected] = useState(false);

  // Show banner when offline or degraded
  useEffect(() => {
    if (!status.isOnline || status.isDegraded) {
      setIsVisible(true);
      setShowReconnected(false);
    } else if (isVisible) {
      // Connection restored - show success briefly
      setShowReconnected(true);
      const timer = setTimeout(() => {
        setIsVisible(false);
        setShowReconnected(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [status.isOnline, status.isDegraded, isVisible]);

  // Don't render if everything is fine
  if (!isVisible) {
    return null;
  }

  // Connection restored state
  if (showReconnected) {
    return (
      <div
        className={`fixed top-0 left-0 right-0 z-50 bg-green-600 text-white px-4 py-2 text-center text-sm shadow-lg transition-all ${className}`}
        role="status"
        aria-live="polite"
      >
        <span className="inline-flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          Connection restored
        </span>
      </div>
    );
  }

  // Offline state
  if (!status.isOnline) {
    return (
      <div
        className={`fixed top-0 left-0 right-0 z-50 bg-red-600 text-white px-4 py-2 text-center text-sm shadow-lg ${className}`}
        role="alert"
        aria-live="assertive"
      >
        <span className="inline-flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M18.364 5.636a9 9 0 010 12.728M5.636 18.364a9 9 0 010-12.728M12 12h.01"
            />
          </svg>
          You are offline
          <span className="text-red-200">— Waiting for network connection...</span>
        </span>
        {showDetails && status.timeSinceLastSuccess && (
          <span className="ml-4 text-red-200 text-xs">
            Last connected: {Math.round(status.timeSinceLastSuccess / 1000)}s ago
          </span>
        )}
      </div>
    );
  }

  // Degraded state (online but API unreachable)
  if (status.isDegraded) {
    return (
      <div
        className={`fixed top-0 left-0 right-0 z-50 bg-yellow-600 text-white px-4 py-2 text-center text-sm shadow-lg ${className}`}
        role="alert"
        aria-live="polite"
      >
        <span className="inline-flex items-center gap-2">
          <svg
            className="w-4 h-4 animate-pulse"
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
          Connection unstable
          <span className="text-yellow-200">— Having trouble reaching the server</span>
        </span>
        {showDetails && (
          <span className="ml-4 text-yellow-200 text-xs">
            {status.consecutiveFailures} failed attempts
            {status.rtt && ` • RTT: ${status.rtt}ms`}
          </span>
        )}
      </div>
    );
  }

  return null;
}

export default ConnectionStatus;
