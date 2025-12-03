/**
 * Notification Store Tests
 */
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useNotificationStore } from "./notificationStore";
import type { NotificationPreferences } from "../types/notifications";
import { DEFAULT_NOTIFICATION_PREFERENCES } from "../types/notifications";

// Mock Date.now for consistent IDs
const MOCK_TIMESTAMP = 1700000000000;
let dateNowSpy: ReturnType<typeof vi.spyOn>;

// Helper to create valid preferences
function createTestPreferences(
  overrides: Partial<NotificationPreferences> = {}
): NotificationPreferences {
  return {
    ...DEFAULT_NOTIFICATION_PREFERENCES,
    ...overrides,
  };
}

beforeEach(() => {
  dateNowSpy = vi.spyOn(Date, "now").mockReturnValue(MOCK_TIMESTAMP);
  // Reset store
  act(() => {
    useNotificationStore.setState({
      notifications: [],
      preferences: createTestPreferences(),
      filters: {},
      isPanelOpen: false,
      connectionStatus: "disconnected",
    });
  });
});

afterEach(() => {
  dateNowSpy.mockRestore();
});

describe("useNotificationStore", () => {
  describe("initial state", () => {
    it("should have empty notifications by default", () => {
      const { result } = renderHook(() => useNotificationStore());
      expect(result.current.notifications).toEqual([]);
    });

    it("should have default preferences", () => {
      const { result } = renderHook(() => useNotificationStore());
      expect(result.current.preferences.desktopEnabled).toBe(false);
      expect(result.current.preferences.enabled).toBe(true);
    });
  });

  describe("addNotification", () => {
    it("should add a notification with generated id", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        result.current.addNotification({
          title: "Test",
          message: "Test message",
          severity: "info",
          category: "system",
        });
      });

      expect(result.current.notifications).toHaveLength(1);
      expect(result.current.notifications[0].id).toBeDefined();
      expect(result.current.notifications[0].title).toBe("Test");
    });

    it("should mark notification as unread by default", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        result.current.addNotification({
          title: "Test",
          message: "Test message",
          severity: "info",
          category: "system",
        });
      });

      expect(result.current.notifications[0].read).toBe(false);
    });

    it("should set timestamp automatically", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        result.current.addNotification({
          title: "Test",
          message: "Test message",
          severity: "info",
          category: "system",
        });
      });

      expect(result.current.notifications[0].timestamp).toBeDefined();
    });

    it("should prepend new notifications", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP);
        result.current.addNotification({
          title: "First",
          message: "First message",
          severity: "info",
          category: "system",
        });
      });

      act(() => {
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP + 1000);
        result.current.addNotification({
          title: "Second",
          message: "Second message",
          severity: "info",
          category: "system",
        });
      });

      expect(result.current.notifications[0].title).toBe("Second");
    });
  });

  describe("markAsRead", () => {
    it("should mark a notification as read", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        result.current.addNotification({
          title: "Test",
          message: "Test message",
          severity: "info",
          category: "system",
        });
      });

      const notificationId = result.current.notifications[0].id;

      act(() => {
        result.current.markAsRead(notificationId);
      });

      expect(result.current.notifications[0].read).toBe(true);
    });
  });

  describe("markAllAsRead", () => {
    it("should mark all notifications as read", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP);
        result.current.addNotification({
          title: "First",
          message: "First",
          severity: "info",
          category: "system",
        });
      });

      act(() => {
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP + 1);
        result.current.addNotification({
          title: "Second",
          message: "Second",
          severity: "warning",
          category: "pipeline",
        });
      });

      act(() => {
        result.current.markAllAsRead();
      });

      expect(
        result.current.notifications.every((n) => n.read)
      ).toBe(true);
    });
  });

  describe("dismiss", () => {
    it("should dismiss a notification", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        result.current.addNotification({
          title: "Test",
          message: "Test message",
          severity: "info",
          category: "system",
        });
      });

      const notificationId = result.current.notifications[0].id;

      act(() => {
        result.current.dismiss(notificationId);
      });

      expect(result.current.notifications[0].dismissed).toBe(true);
    });
  });

  describe("clearAll", () => {
    it("should remove all notifications", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP);
        result.current.addNotification({
          title: "First",
          message: "First",
          severity: "info",
          category: "system",
        });
      });

      act(() => {
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP + 1);
        result.current.addNotification({
          title: "Second",
          message: "Second",
          severity: "info",
          category: "system",
        });
      });

      act(() => {
        result.current.clearAll();
      });

      expect(result.current.notifications).toHaveLength(0);
    });
  });

  describe("updatePreferences", () => {
    it("should update preferences", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        result.current.updatePreferences({
          desktopEnabled: true,
        });
      });

      expect(result.current.preferences.desktopEnabled).toBe(true);
    });

    it("should preserve other preferences when updating", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        result.current.updatePreferences({
          soundEnabled: true,
        });
      });

      expect(result.current.preferences.desktopEnabled).toBe(false);
      expect(result.current.preferences.soundEnabled).toBe(true);
    });
  });

  describe("getSummary", () => {
    it("should return count of unread notifications", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP);
        result.current.addNotification({
          title: "First",
          message: "First",
          severity: "info",
          category: "system",
        });
      });

      act(() => {
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP + 1);
        result.current.addNotification({
          title: "Second",
          message: "Second",
          severity: "info",
          category: "system",
        });
      });

      expect(result.current.getSummary().unreadCount).toBe(2);

      act(() => {
        result.current.markAsRead(result.current.notifications[0].id);
      });

      expect(result.current.getSummary().unreadCount).toBe(1);
    });
  });

  describe("getFilteredNotifications", () => {
    it("should return notifications filtered by filters", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP);
        result.current.addNotification({
          title: "System",
          message: "System message",
          severity: "info",
          category: "system",
        });
      });

      act(() => {
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP + 1);
        result.current.addNotification({
          title: "Pipeline",
          message: "Pipeline message",
          severity: "info",
          category: "pipeline",
        });
      });

      act(() => {
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP + 2);
        result.current.addNotification({
          title: "Another System",
          message: "Another system message",
          severity: "warning",
          category: "system",
        });
      });

      // Set filter to show only system notifications
      act(() => {
        result.current.setFilters({ categories: ["system"] });
      });

      const filteredNotifications = result.current.getFilteredNotifications();
      expect(filteredNotifications).toHaveLength(2);
      expect(
        filteredNotifications.every((n) => n.category === "system")
      ).toBe(true);
    });
  });

  describe("togglePanel", () => {
    it("should toggle panel open state", () => {
      const { result } = renderHook(() => useNotificationStore());

      expect(result.current.isPanelOpen).toBe(false);

      act(() => {
        result.current.togglePanel();
      });

      expect(result.current.isPanelOpen).toBe(true);

      act(() => {
        result.current.togglePanel();
      });

      expect(result.current.isPanelOpen).toBe(false);
    });
  });
});
