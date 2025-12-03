/**
 * useNotifications hook
 * Provides notification actions and real-time subscription
 */
import { useEffect, useCallback } from "react";
import { useNotificationStore } from "@/stores/notificationStore";
import type {
  NotificationCategory,
  NotificationSeverity,
  NotificationFilters,
} from "@/types/notifications";

/**
 * Main notifications hook
 */
export function useNotifications() {
  const store = useNotificationStore();

  // Request browser notification permission on mount
  useEffect(() => {
    if (
      store.preferences.desktopEnabled &&
      "Notification" in window &&
      Notification.permission === "default"
    ) {
      Notification.requestPermission();
    }
  }, [store.preferences.desktopEnabled]);

  /**
   * Send a notification
   */
  const notify = useCallback(
    (options: {
      title: string;
      message: string;
      severity?: NotificationSeverity;
      category?: NotificationCategory;
      link?: string;
      metadata?: Record<string, unknown>;
    }) => {
      store.addNotification({
        title: options.title,
        message: options.message,
        severity: options.severity ?? "info",
        category: options.category ?? "system",
        link: options.link,
        metadata: options.metadata,
      });
    },
    [store]
  );

  /**
   * Send an info notification
   */
  const notifyInfo = useCallback(
    (
      title: string,
      message: string,
      options?: { link?: string; category?: NotificationCategory }
    ) => {
      notify({ title, message, severity: "info", ...options });
    },
    [notify]
  );

  /**
   * Send a success notification
   */
  const notifySuccess = useCallback(
    (
      title: string,
      message: string,
      options?: { link?: string; category?: NotificationCategory }
    ) => {
      notify({ title, message, severity: "success", ...options });
    },
    [notify]
  );

  /**
   * Send a warning notification
   */
  const notifyWarning = useCallback(
    (
      title: string,
      message: string,
      options?: { link?: string; category?: NotificationCategory }
    ) => {
      notify({ title, message, severity: "warning", ...options });
    },
    [notify]
  );

  /**
   * Send an error notification
   */
  const notifyError = useCallback(
    (
      title: string,
      message: string,
      options?: { link?: string; category?: NotificationCategory }
    ) => {
      notify({ title, message, severity: "error", ...options });
    },
    [notify]
  );

  return {
    // State
    notifications: store.getFilteredNotifications(),
    summary: store.getSummary(),
    preferences: store.preferences,
    filters: store.filters,
    isPanelOpen: store.isPanelOpen,
    connectionStatus: store.connectionStatus,

    // Actions
    notify,
    notifyInfo,
    notifySuccess,
    notifyWarning,
    notifyError,
    markAsRead: store.markAsRead,
    markAllAsRead: store.markAllAsRead,
    dismiss: store.dismiss,
    dismissAll: store.dismissAll,
    clearAll: store.clearAll,
    setFilters: store.setFilters,
    updatePreferences: store.updatePreferences,
    updateCategoryPreference: store.updateCategoryPreference,
    togglePanel: store.togglePanel,
    setPanelOpen: store.setPanelOpen,
  };
}

/**
 * Hook for subscribing to real-time notifications via SSE or WebSocket
 *
 * NOTE: The notifications stream endpoint (/api/v1/notifications/stream) is not yet
 * implemented in the backend. This hook is disabled by default and will gracefully
 * handle the missing endpoint when enabled.
 */
export function useNotificationSubscription(
  endpoint: string = "/api/v1/notifications/stream",
  enabled: boolean = false // Disabled by default until backend implements the endpoint
) {
  const { addNotification, setConnectionStatus } =
    useNotificationStore.getState();

  useEffect(() => {
    // Skip connection if disabled or endpoint not provided
    if (!enabled || !endpoint) {
      setConnectionStatus("disconnected");
      return;
    }

    let eventSource: EventSource | null = null;
    let reconnectTimeout: NodeJS.Timeout | null = null;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 3;

    const connect = () => {
      // Stop trying after max attempts to avoid spamming logs
      if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        console.warn(
          `Notifications stream: Giving up after ${MAX_RECONNECT_ATTEMPTS} failed attempts. ` +
            `Endpoint ${endpoint} may not be implemented.`
        );
        setConnectionStatus("disconnected");
        return;
      }

      setConnectionStatus("connecting");
      reconnectAttempts++;

      try {
        eventSource = new EventSource(endpoint);

        eventSource.onopen = () => {
          reconnectAttempts = 0; // Reset on successful connection
          setConnectionStatus("connected");
        };

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "notification") {
              addNotification(data.payload);
            }
          } catch {
            console.error("Failed to parse notification event:", event.data);
          }
        };

        eventSource.onerror = () => {
          setConnectionStatus("disconnected");
          eventSource?.close();

          // Attempt to reconnect with exponential backoff
          const delay = Math.min(
            5000 * Math.pow(2, reconnectAttempts - 1),
            30000
          );
          reconnectTimeout = setTimeout(connect, delay);
        };
      } catch {
        setConnectionStatus("disconnected");
        // Attempt to reconnect with exponential backoff
        const delay = Math.min(
          5000 * Math.pow(2, reconnectAttempts - 1),
          30000
        );
        reconnectTimeout = setTimeout(connect, delay);
      }
    };

    // Only connect if enabled
    connect();

    return () => {
      eventSource?.close();
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, [endpoint, enabled, addNotification, setConnectionStatus]);
}

/**
 * Hook to filter notifications by category
 */
export function useNotificationsByCategory(category: NotificationCategory) {
  const notifications = useNotificationStore((state) =>
    state.notifications.filter((n) => n.category === category && !n.dismissed)
  );

  return notifications;
}

/**
 * Hook to filter notifications by severity
 */
export function useNotificationsBySeverity(severity: NotificationSeverity) {
  const notifications = useNotificationStore((state) =>
    state.notifications.filter((n) => n.severity === severity && !n.dismissed)
  );

  return notifications;
}
