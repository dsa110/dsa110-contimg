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
    (title: string, message: string, options?: { link?: string; category?: NotificationCategory }) => {
      notify({ title, message, severity: "info", ...options });
    },
    [notify]
  );

  /**
   * Send a success notification
   */
  const notifySuccess = useCallback(
    (title: string, message: string, options?: { link?: string; category?: NotificationCategory }) => {
      notify({ title, message, severity: "success", ...options });
    },
    [notify]
  );

  /**
   * Send a warning notification
   */
  const notifyWarning = useCallback(
    (title: string, message: string, options?: { link?: string; category?: NotificationCategory }) => {
      notify({ title, message, severity: "warning", ...options });
    },
    [notify]
  );

  /**
   * Send an error notification
   */
  const notifyError = useCallback(
    (title: string, message: string, options?: { link?: string; category?: NotificationCategory }) => {
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
 */
export function useNotificationSubscription(
  endpoint: string = "/api/notifications/stream"
) {
  const { addNotification, setConnectionStatus } = useNotificationStore.getState();

  useEffect(() => {
    let eventSource: EventSource | null = null;
    let reconnectTimeout: NodeJS.Timeout | null = null;

    const connect = () => {
      setConnectionStatus("connecting");

      try {
        eventSource = new EventSource(endpoint);

        eventSource.onopen = () => {
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

          // Attempt to reconnect after 5 seconds
          reconnectTimeout = setTimeout(connect, 5000);
        };
      } catch {
        setConnectionStatus("disconnected");
        // Attempt to reconnect after 5 seconds
        reconnectTimeout = setTimeout(connect, 5000);
      }
    };

    // Don't auto-connect in development without a real endpoint
    // connect();

    return () => {
      eventSource?.close();
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, [endpoint, addNotification, setConnectionStatus]);
}

/**
 * Hook to filter notifications by category
 */
export function useNotificationsByCategory(category: NotificationCategory) {
  const notifications = useNotificationStore((state) =>
    state.notifications.filter(
      (n) => n.category === category && !n.dismissed
    )
  );

  return notifications;
}

/**
 * Hook to filter notifications by severity
 */
export function useNotificationsBySeverity(severity: NotificationSeverity) {
  const notifications = useNotificationStore((state) =>
    state.notifications.filter(
      (n) => n.severity === severity && !n.dismissed
    )
  );

  return notifications;
}
