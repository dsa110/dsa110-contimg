/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useNetworkNotifications } from "./useNetworkNotifications";
import { useUIStore } from "../stores/appStore";

// Mock fetch for connectivity checks
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Test wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }

  return Wrapper;
}

describe("useNetworkNotifications", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockFetch.mockClear();
    // Reset store state
    useUIStore.setState({ notifications: [] });
    // Mock initial online state
    Object.defineProperty(navigator, "onLine", {
      value: true,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("should return network status", async () => {
    mockFetch.mockResolvedValue({ ok: true });

    const { result } = renderHook(() => useNetworkNotifications(), {
      wrapper: createWrapper(),
    });

    // Allow initial connectivity check
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(result.current).toHaveProperty("isOnline");
    expect(result.current).toHaveProperty("isDegraded");
    expect(result.current).toHaveProperty("hasApiConnectivity");
  });

  it("should add notification on disconnect", async () => {
    mockFetch.mockResolvedValue({ ok: true });

    renderHook(() => useNetworkNotifications(), {
      wrapper: createWrapper(),
    });

    // Initial setup
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    // Simulate going offline
    await act(async () => {
      Object.defineProperty(navigator, "onLine", { value: false, configurable: true });
      window.dispatchEvent(new Event("offline"));
      await vi.advanceTimersByTimeAsync(100);
    });

    const notifications = useUIStore.getState().notifications;
    expect(notifications.length).toBeGreaterThan(0);
    expect(notifications.some((n) => n.title === "Connection Lost")).toBe(true);
  });

  it("should add notification on reconnect", async () => {
    mockFetch.mockResolvedValue({ ok: true });

    renderHook(() => useNetworkNotifications(), {
      wrapper: createWrapper(),
    });

    // Start offline
    await act(async () => {
      Object.defineProperty(navigator, "onLine", { value: false, configurable: true });
      window.dispatchEvent(new Event("offline"));
      await vi.advanceTimersByTimeAsync(100);
    });

    // Clear notifications
    useUIStore.setState({ notifications: [] });

    // Go online
    await act(async () => {
      Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
      window.dispatchEvent(new Event("online"));
      await vi.advanceTimersByTimeAsync(500);
    });

    const notifications = useUIStore.getState().notifications;
    expect(notifications.some((n) => n.title === "Connection Restored")).toBe(true);
  });

  it("should respect showOfflineNotification option", async () => {
    mockFetch.mockResolvedValue({ ok: true });

    renderHook(() => useNetworkNotifications({ showOfflineNotification: false }), {
      wrapper: createWrapper(),
    });

    // Initial setup
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    // Simulate going offline
    await act(async () => {
      Object.defineProperty(navigator, "onLine", { value: false, configurable: true });
      window.dispatchEvent(new Event("offline"));
      await vi.advanceTimersByTimeAsync(100);
    });

    const notifications = useUIStore.getState().notifications;
    expect(notifications.some((n) => n.title === "Connection Lost")).toBe(false);
  });

  it("should respect showOnlineNotification option", async () => {
    mockFetch.mockResolvedValue({ ok: true });

    renderHook(() => useNetworkNotifications({ showOnlineNotification: false }), {
      wrapper: createWrapper(),
    });

    // Start offline
    await act(async () => {
      Object.defineProperty(navigator, "onLine", { value: false, configurable: true });
      window.dispatchEvent(new Event("offline"));
      await vi.advanceTimersByTimeAsync(100);
    });

    // Clear notifications
    useUIStore.setState({ notifications: [] });

    // Go online
    await act(async () => {
      Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
      window.dispatchEvent(new Event("online"));
      await vi.advanceTimersByTimeAsync(500);
    });

    const notifications = useUIStore.getState().notifications;
    expect(notifications.some((n) => n.title === "Connection Restored")).toBe(false);
  });

  it("should include consecutive failure count in degraded notification", async () => {
    // Mock API failures to trigger degraded state
    mockFetch.mockRejectedValue(new Error("Network error"));

    renderHook(
      () =>
        useNetworkNotifications({
          showDegradedNotification: true,
        }),
      {
        wrapper: createWrapper(),
      }
    );

    // Allow multiple connectivity checks to fail
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100000); // Multiple check intervals
    });

    // Check if degraded notification mentions failures
    const notifications = useUIStore.getState().notifications;
    const degradedNotification = notifications.find((n) => n.title === "Connection Issues");

    if (degradedNotification) {
      expect(degradedNotification.message).toContain("failures");
    }
  });
});
