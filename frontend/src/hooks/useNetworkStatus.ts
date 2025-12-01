/**
 * Network status hook for detecting online/offline state and reconnection events.
 *
 * Provides:
 * - Real-time online/offline detection
 * - Reconnection event callbacks
 * - Connection quality assessment (when available)
 * - Automatic refetch trigger on reconnection
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

export interface NetworkStatus {
  /** Whether the browser reports being online */
  isOnline: boolean;
  /** Whether we've detected actual API connectivity */
  hasApiConnectivity: boolean;
  /** Time since last successful API call (ms) */
  timeSinceLastSuccess: number | null;
  /** Number of consecutive API failures */
  consecutiveFailures: number;
  /** Effective connection type from Navigator API (if available) */
  effectiveType: "slow-2g" | "2g" | "3g" | "4g" | null;
  /** Estimated downlink speed in Mbps (if available) */
  downlink: number | null;
  /** Estimated round-trip time in ms (if available) */
  rtt: number | null;
  /** Whether connection is considered degraded */
  isDegraded: boolean;
}

interface UseNetworkStatusOptions {
  /** Callback when network comes back online */
  onReconnect?: () => void;
  /** Callback when network goes offline */
  onDisconnect?: () => void;
  /** Whether to automatically invalidate queries on reconnection */
  autoRefetchOnReconnect?: boolean;
  /** How often to check API connectivity (ms) */
  connectivityCheckInterval?: number;
  /** Threshold for considering connection degraded (consecutive failures) */
  degradedThreshold?: number;
}

/**
 * Hook to monitor network status and handle disconnection scenarios
 */
export function useNetworkStatus(options: UseNetworkStatusOptions = {}): NetworkStatus {
  const {
    onReconnect,
    onDisconnect,
    autoRefetchOnReconnect = true,
    connectivityCheckInterval = 30000,
    degradedThreshold = 3,
  } = options;

  const queryClient = useQueryClient();
  const lastSuccessRef = useRef<number | null>(null);
  const failureCountRef = useRef(0);
  const wasOnlineRef = useRef(navigator.onLine);

  // Helper functions to safely access Network Information API
  // (Defined before useState to avoid "accessed before declared" errors)
  function getEffectiveType(): NetworkStatus["effectiveType"] {
    const connection = (navigator as NavigatorWithConnection).connection;
    return connection?.effectiveType ?? null;
  }

  function getDownlink(): number | null {
    const connection = (navigator as NavigatorWithConnection).connection;
    return connection?.downlink ?? null;
  }

  function getRtt(): number | null {
    const connection = (navigator as NavigatorWithConnection).connection;
    return connection?.rtt ?? null;
  }

  const [status, setStatus] = useState<NetworkStatus>(() => ({
    isOnline: navigator.onLine,
    hasApiConnectivity: navigator.onLine,
    timeSinceLastSuccess: null,
    consecutiveFailures: 0,
    effectiveType: getEffectiveType(),
    downlink: getDownlink(),
    rtt: getRtt(),
    isDegraded: false,
  }));

  // Record successful API call
  const recordSuccess = useCallback(() => {
    lastSuccessRef.current = Date.now();
    failureCountRef.current = 0;
    setStatus((prev) => ({
      ...prev,
      hasApiConnectivity: true,
      timeSinceLastSuccess: 0,
      consecutiveFailures: 0,
      isDegraded: false,
    }));
  }, []);

  // Record failed API call
  const recordFailure = useCallback(() => {
    failureCountRef.current += 1;
    const isDegraded = failureCountRef.current >= degradedThreshold;
    setStatus((prev) => ({
      ...prev,
      hasApiConnectivity: failureCountRef.current < degradedThreshold,
      consecutiveFailures: failureCountRef.current,
      isDegraded,
    }));
  }, [degradedThreshold]);

  // Check API connectivity
  const checkConnectivity = useCallback(async () => {
    try {
      const response = await fetch("/api/health", {
        method: "GET",
        cache: "no-store",
        signal: AbortSignal.timeout(5000),
      });
      if (response.ok) {
        recordSuccess();
        return true;
      }
      recordFailure();
      return false;
    } catch {
      recordFailure();
      return false;
    }
  }, [recordSuccess, recordFailure]);

  // Handle online event
  const handleOnline = useCallback(() => {
    setStatus((prev) => ({ ...prev, isOnline: true }));

    // Check actual connectivity before declaring reconnection
    checkConnectivity().then((hasConnectivity) => {
      if (hasConnectivity && !wasOnlineRef.current) {
        onReconnect?.();
        if (autoRefetchOnReconnect) {
          // Invalidate all queries to trigger refetch
          queryClient.invalidateQueries();
        }
      }
      wasOnlineRef.current = true;
    });
  }, [checkConnectivity, onReconnect, autoRefetchOnReconnect, queryClient]);

  // Handle offline event
  const handleOffline = useCallback(() => {
    wasOnlineRef.current = false;
    setStatus((prev) => ({
      ...prev,
      isOnline: false,
      hasApiConnectivity: false,
      isDegraded: true,
    }));
    onDisconnect?.();
  }, [onDisconnect]);

  // Handle connection change (Network Information API)
  const handleConnectionChange = useCallback(() => {
    setStatus((prev) => ({
      ...prev,
      effectiveType: getEffectiveType(),
      downlink: getDownlink(),
      rtt: getRtt(),
    }));
  }, []);

  // Set up event listeners
  useEffect(() => {
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // Network Information API (Chrome, Edge, Opera)
    const connection = (navigator as NavigatorWithConnection).connection;
    if (connection) {
      connection.addEventListener("change", handleConnectionChange);
    }

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      if (connection) {
        connection.removeEventListener("change", handleConnectionChange);
      }
    };
  }, [handleOnline, handleOffline, handleConnectionChange]);

  // Periodic connectivity check
  useEffect(() => {
    const interval = setInterval(() => {
      if (navigator.onLine) {
        checkConnectivity();
      }
    }, connectivityCheckInterval);

    // Initial check
    checkConnectivity();

    return () => clearInterval(interval);
  }, [checkConnectivity, connectivityCheckInterval]);

  // Update time since last success
  useEffect(() => {
    const interval = setInterval(() => {
      if (lastSuccessRef.current) {
        setStatus((prev) => ({
          ...prev,
          timeSinceLastSuccess: Date.now() - lastSuccessRef.current!,
        }));
      }
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return status;
}

// Type augmentation for Network Information API
interface NavigatorWithConnection extends Navigator {
  connection?: {
    effectiveType: "slow-2g" | "2g" | "3g" | "4g";
    downlink: number;
    rtt: number;
    addEventListener: (type: string, listener: () => void) => void;
    removeEventListener: (type: string, listener: () => void) => void;
  };
}

export default useNetworkStatus;
