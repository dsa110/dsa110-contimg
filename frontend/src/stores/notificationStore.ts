/**
 * Notification store using Zustand
 * Manages notification state, preferences, and actions
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  Notification,
  NotificationPreferences,
  NotificationFilters,
  NotificationSummary,
  NotificationCategory,
  NotificationSeverity,
} from "@/types/notifications";
import {
  DEFAULT_NOTIFICATION_PREFERENCES,
  meetsSeverityThreshold,
} from "@/types/notifications";

/**
 * Maximum number of notifications to keep in store
 */
const MAX_NOTIFICATIONS = 100;

/**
 * Notification store state
 */
interface NotificationState {
  /** List of notifications */
  notifications: Notification[];
  /** User preferences */
  preferences: NotificationPreferences;
  /** Current filters */
  filters: NotificationFilters;
  /** Whether notification panel is open */
  isPanelOpen: boolean;
  /** Connection status for real-time notifications */
  connectionStatus: "connected" | "disconnected" | "connecting";
}

/**
 * Notification store actions
 */
interface NotificationActions {
  /** Add a new notification */
  addNotification: (
    notification: Omit<Notification, "id" | "timestamp" | "read" | "dismissed">
  ) => void;
  /** Mark a notification as read */
  markAsRead: (id: string) => void;
  /** Mark all notifications as read */
  markAllAsRead: () => void;
  /** Dismiss a notification */
  dismiss: (id: string) => void;
  /** Dismiss all notifications */
  dismissAll: () => void;
  /** Clear all notifications */
  clearAll: () => void;
  /** Update filters */
  setFilters: (filters: NotificationFilters) => void;
  /** Update preferences */
  updatePreferences: (preferences: Partial<NotificationPreferences>) => void;
  /** Update a single category preference */
  updateCategoryPreference: (
    category: NotificationCategory,
    updates: Partial<{
      inApp: boolean;
      channels: ("email" | "slack" | "webhook")[];
      minSeverity: NotificationSeverity;
    }>
  ) => void;
  /** Toggle panel open/closed */
  togglePanel: () => void;
  /** Set panel open state */
  setPanelOpen: (open: boolean) => void;
  /** Set connection status */
  setConnectionStatus: (
    status: "connected" | "disconnected" | "connecting"
  ) => void;
  /** Get filtered notifications */
  getFilteredNotifications: () => Notification[];
  /** Get notification summary */
  getSummary: () => NotificationSummary;
}

/**
 * Generate a unique notification ID
 */
function generateId(): string {
  return `notif_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Filter notifications based on current filters
 */
function filterNotifications(
  notifications: Notification[],
  filters: NotificationFilters
): Notification[] {
  return notifications.filter((notification) => {
    // Filter by read status
    if (filters.read !== undefined && notification.read !== filters.read) {
      return false;
    }

    // Filter by categories
    if (
      filters.categories &&
      filters.categories.length > 0 &&
      !filters.categories.includes(notification.category)
    ) {
      return false;
    }

    // Filter by severities
    if (
      filters.severities &&
      filters.severities.length > 0 &&
      !filters.severities.includes(notification.severity)
    ) {
      return false;
    }

    // Filter by date range
    if (filters.dateRange) {
      const timestamp = new Date(notification.timestamp).getTime();
      const start = new Date(filters.dateRange.start).getTime();
      const end = new Date(filters.dateRange.end).getTime();
      if (timestamp < start || timestamp > end) {
        return false;
      }
    }

    return true;
  });
}

/**
 * Calculate notification summary
 */
function calculateSummary(notifications: Notification[]): NotificationSummary {
  const unread = notifications.filter((n) => !n.read && !n.dismissed);

  const bySeverity: Record<NotificationSeverity, number> = {
    info: 0,
    success: 0,
    warning: 0,
    error: 0,
  };

  const byCategory: Record<NotificationCategory, number> = {
    system: 0,
    pipeline: 0,
    calibration: 0,
    source: 0,
    data: 0,
    user: 0,
  };

  for (const notification of unread) {
    bySeverity[notification.severity]++;
    byCategory[notification.category]++;
  }

  return {
    unreadCount: unread.length,
    bySeverity,
    byCategory,
    mostRecent: notifications[0],
  };
}

/**
 * Notification store
 */
export const useNotificationStore = create<
  NotificationState & NotificationActions
>()(
  persist(
    (set, get) => ({
      // Initial state
      notifications: [],
      preferences: DEFAULT_NOTIFICATION_PREFERENCES,
      filters: {},
      isPanelOpen: false,
      connectionStatus: "disconnected",

      // Actions
      addNotification: (notificationData) => {
        const { preferences, notifications } = get();

        // Check if notifications are enabled
        if (!preferences.enabled) return;

        // Check category preferences
        const categoryPref = preferences.categoryPreferences.find(
          (p) => p.category === notificationData.category
        );

        if (categoryPref) {
          // Check if in-app notifications are enabled for this category
          if (!categoryPref.inApp) return;

          // Check severity threshold
          if (
            !meetsSeverityThreshold(
              notificationData.severity,
              categoryPref.minSeverity
            )
          ) {
            return;
          }
        }

        const notification: Notification = {
          ...notificationData,
          id: generateId(),
          timestamp: new Date().toISOString(),
          read: false,
          dismissed: false,
        };

        // Add to beginning of list, trim if over max
        const updatedNotifications = [notification, ...notifications].slice(
          0,
          MAX_NOTIFICATIONS
        );

        set({ notifications: updatedNotifications });

        // Play sound if enabled
        if (preferences.soundEnabled) {
          // Sound would be played here via Audio API
        }

        // Show desktop notification if enabled
        if (
          preferences.desktopEnabled &&
          "Notification" in window &&
          Notification.permission === "granted"
        ) {
          new Notification(notification.title, {
            body: notification.message,
            icon: "/favicon.ico",
          });
        }
      },

      markAsRead: (id) => {
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n
          ),
        }));
      },

      markAllAsRead: () => {
        set((state) => ({
          notifications: state.notifications.map((n) => ({ ...n, read: true })),
        }));
      },

      dismiss: (id) => {
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, dismissed: true } : n
          ),
        }));
      },

      dismissAll: () => {
        set((state) => ({
          notifications: state.notifications.map((n) => ({
            ...n,
            dismissed: true,
          })),
        }));
      },

      clearAll: () => {
        set({ notifications: [] });
      },

      setFilters: (filters) => {
        set({ filters });
      },

      updatePreferences: (updates) => {
        set((state) => ({
          preferences: { ...state.preferences, ...updates },
        }));
      },

      updateCategoryPreference: (category, updates) => {
        set((state) => ({
          preferences: {
            ...state.preferences,
            categoryPreferences: state.preferences.categoryPreferences.map(
              (pref) =>
                pref.category === category ? { ...pref, ...updates } : pref
            ),
          },
        }));
      },

      togglePanel: () => {
        set((state) => ({ isPanelOpen: !state.isPanelOpen }));
      },

      setPanelOpen: (open) => {
        set({ isPanelOpen: open });
      },

      setConnectionStatus: (status) => {
        set({ connectionStatus: status });
      },

      getFilteredNotifications: () => {
        const { notifications, filters } = get();
        return filterNotifications(
          notifications.filter((n) => !n.dismissed),
          filters
        );
      },

      getSummary: () => {
        const { notifications } = get();
        return calculateSummary(notifications.filter((n) => !n.dismissed));
      },
    }),
    {
      name: "dsa110-notifications",
      partialize: (state) => ({
        notifications: state.notifications.slice(0, 50), // Only persist last 50
        preferences: state.preferences,
      }),
    }
  )
);

/**
 * Helper hook to get just the unread count
 */
export function useUnreadCount(): number {
  return useNotificationStore(
    (state) => state.notifications.filter((n) => !n.read && !n.dismissed).length
  );
}

/**
 * Helper hook to check if there are any error notifications
 */
export function useHasErrors(): boolean {
  return useNotificationStore((state) =>
    state.notifications.some(
      (n) => n.severity === "error" && !n.read && !n.dismissed
    )
  );
}
