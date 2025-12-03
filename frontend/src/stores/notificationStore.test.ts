/**
 * Notification Store Tests
 */
import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useNotificationStore } from "../notificationStore";

// Mock Date.now for consistent IDs
const MOCK_TIMESTAMP = 1700000000000;
let dateNowSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  dateNowSpy = vi.spyOn(Date, "now").mockReturnValue(MOCK_TIMESTAMP);
  // Reset store
  act(() => {
    useNotificationStore.setState({
      notifications: [],
      preferences: {
        enableDesktop: false,
        enableSound: false,
        minimumSeverity: "info",
        mutedCategories: [],
      },
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
      expect(result.current.preferences.enableDesktop).toBe(false);
      expect(result.current.preferences.minimumSeverity).toBe("info");
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
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP + 1);
        result.current.addNotification({
          title: "Second",
          message: "Second",
          severity: "warning",
          category: "job",
        });
      });

      act(() => {
        result.current.markAllAsRead();
      });

      expect(result.current.notifications.every((n) => n.read)).toBe(true);
    });
  });

  describe("removeNotification", () => {
    it("should remove a notification", () => {
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
        result.current.removeNotification(notificationId);
      });

      expect(result.current.notifications).toHaveLength(0);
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
          enableDesktop: true,
          minimumSeverity: "warning",
        });
      });

      expect(result.current.preferences.enableDesktop).toBe(true);
      expect(result.current.preferences.minimumSeverity).toBe("warning");
    });

    it("should preserve other preferences when updating", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        result.current.updatePreferences({
          enableSound: true,
        });
      });

      expect(result.current.preferences.enableDesktop).toBe(false);
      expect(result.current.preferences.enableSound).toBe(true);
    });
  });

  describe("getUnreadCount", () => {
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
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP + 1);
        result.current.addNotification({
          title: "Second",
          message: "Second",
          severity: "info",
          category: "system",
        });
      });

      expect(result.current.getUnreadCount()).toBe(2);

      act(() => {
        result.current.markAsRead(result.current.notifications[0].id);
      });

      expect(result.current.getUnreadCount()).toBe(1);
    });
  });

  describe("getNotificationsByCategory", () => {
    it("should return notifications filtered by category", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP);
        result.current.addNotification({
          title: "System",
          message: "System message",
          severity: "info",
          category: "system",
        });
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP + 1);
        result.current.addNotification({
          title: "Job",
          message: "Job message",
          severity: "info",
          category: "job",
        });
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP + 2);
        result.current.addNotification({
          title: "Another System",
          message: "Another system message",
          severity: "warning",
          category: "system",
        });
      });

      const systemNotifications =
        result.current.getNotificationsByCategory("system");
      expect(systemNotifications).toHaveLength(2);
      expect(systemNotifications.every((n) => n.category === "system")).toBe(
        true
      );
    });
  });

  describe("getNotificationsBySeverity", () => {
    it("should return notifications filtered by severity", () => {
      const { result } = renderHook(() => useNotificationStore());

      act(() => {
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP);
        result.current.addNotification({
          title: "Info",
          message: "Info message",
          severity: "info",
          category: "system",
        });
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP + 1);
        result.current.addNotification({
          title: "Warning",
          message: "Warning message",
          severity: "warning",
          category: "system",
        });
        dateNowSpy.mockReturnValue(MOCK_TIMESTAMP + 2);
        result.current.addNotification({
          title: "Error",
          message: "Error message",
          severity: "error",
          category: "system",
        });
      });

      const warningNotifications =
        result.current.getNotificationsBySeverity("warning");
      expect(warningNotifications).toHaveLength(1);
      expect(warningNotifications[0].severity).toBe("warning");
    });
  });
});
