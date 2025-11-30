/**
 * Hook that connects network status changes to the notification system.
 *
 * Automatically shows notifications when:
 * - Network goes offline
 * - Connection becomes degraded (consecutive API failures)
 * - Connection is restored
 */

import { useEffect, useRef, useCallback } from "react";
import useNetworkStatus from "./useNetworkStatus";
import { useUIStore } from "../stores/appStore";

export interface UseNetworkNotificationsOptions {
  /** Whether to show a notification when going offline */
  showOfflineNotification?: boolean;
  /** Whether to show a notification when connection is restored */
  showOnlineNotification?: boolean;
  /** Whether to show a notification when connection becomes degraded */
  showDegradedNotification?: boolean;
  /** Duration for non-critical notifications (ms). 0 = sticky */
  notificationDuration?: number;
}

/**
 * Hook to display network status changes as notifications.
 *
 * Usage:
 * ```tsx
 * function App() {
 *   useNetworkNotifications();
 *   // ...
 * }
 * ```
 */
export function useNetworkNotifications(options: UseNetworkNotificationsOptions = {}) {
  const {
    showOfflineNotification = true,
    showOnlineNotification = true,
    showDegradedNotification = true,
    notificationDuration = 5000,
  } = options;

  const addNotification = useUIStore((state) => state.addNotification);
  const previousStatusRef = useRef<{
    isOnline: boolean;
    isDegraded: boolean;
    hasApiConnectivity: boolean;
  } | null>(null);

  const handleReconnect = useCallback(() => {
    if (showOnlineNotification) {
      addNotification({
        type: "success",
        title: "Connection Restored",
        message:
          "Your connection to the server has been restored. Data will refresh automatically.",
        duration: notificationDuration,
      });
    }
  }, [addNotification, showOnlineNotification, notificationDuration]);

  const handleDisconnect = useCallback(() => {
    if (showOfflineNotification) {
      addNotification({
        type: "error",
        title: "Connection Lost",
        message: "You appear to be offline. Changes may not be saved until connection is restored.",
        duration: 0, // Sticky until connection is restored
      });
    }
  }, [addNotification, showOfflineNotification]);

  const status = useNetworkStatus({
    onReconnect: handleReconnect,
    onDisconnect: handleDisconnect,
    autoRefetchOnReconnect: true,
  });

  // Handle degraded state changes
  useEffect(() => {
    const prevStatus = previousStatusRef.current;

    // Only show degraded notification if we transition from non-degraded to degraded
    // and we're still online (but having API issues)
    if (
      showDegradedNotification &&
      status.isDegraded &&
      status.isOnline &&
      prevStatus &&
      !prevStatus.isDegraded
    ) {
      addNotification({
        type: "warning",
        title: "Connection Issues",
        message: `Experiencing connectivity issues. ${status.consecutiveFailures} consecutive failures detected.`,
        duration: notificationDuration,
      });
    }

    // Update previous status
    previousStatusRef.current = {
      isOnline: status.isOnline,
      isDegraded: status.isDegraded,
      hasApiConnectivity: status.hasApiConnectivity,
    };
  }, [
    status.isOnline,
    status.isDegraded,
    status.hasApiConnectivity,
    status.consecutiveFailures,
    addNotification,
    showDegradedNotification,
    notificationDuration,
  ]);

  return status;
}

export default useNetworkNotifications;
