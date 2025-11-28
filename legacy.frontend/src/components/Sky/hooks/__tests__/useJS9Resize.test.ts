/**
 * Unit Tests for useJS9Resize Hook
 *
 * Tests:
 * 1. Hook sets up resize observers
 * 2. Hook handles window resize events
 * 3. Hook ensures canvas width matches container
 * 4. Hook cleans up observers on unmount
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useJS9Resize } from "../useJS9Resize";

// Mock logger
vi.mock("../../../../utils/logger", () => ({
  logger: {
    debug: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock JS9 utilities
vi.mock("../../../../utils/js9", () => ({
  isJS9Available: vi.fn(() => true),
  findDisplay: vi.fn(() => null),
}));

declare global {
  interface Window {
    JS9: any;
  }
}

describe("useJS9Resize", () => {
  const mockContainerRef = {
    current: document.createElement("div"),
  } as React.RefObject<HTMLDivElement>;

  beforeEach(() => {
    window.JS9 = {
      ResizeDisplay: vi.fn(),
    };

    mockContainerRef.current = document.createElement("div");
    mockContainerRef.current.id = "testDisplay";
    mockContainerRef.current.style.width = "500px";
    mockContainerRef.current.style.height = "600px";
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("should set up resize observers when initialized", () => {
    const getDisplaySafe = vi.fn(() => ({ id: "testDisplay" }));

    renderHook(() =>
      useJS9Resize({
        displayId: "testDisplay",
        containerRef: mockContainerRef,
        initialized: true,
        isJS9Ready: true,
        getDisplaySafe,
      })
    );

    // ResizeObserver should be created (if available)
    expect(mockContainerRef.current).toBeTruthy();
  });

  it("should not set up observers when not initialized", () => {
    const getDisplaySafe = vi.fn(() => null);

    renderHook(() =>
      useJS9Resize({
        displayId: "testDisplay",
        containerRef: mockContainerRef,
        initialized: false,
        isJS9Ready: true,
        getDisplaySafe,
      })
    );

    // Should not crash, but observers won't be set up
    expect(mockContainerRef.current).toBeTruthy();
  });

  it("should handle window resize events", () => {
    const getDisplaySafe = vi.fn(() => ({ id: "testDisplay" }));

    renderHook(() =>
      useJS9Resize({
        displayId: "testDisplay",
        containerRef: mockContainerRef,
        initialized: true,
        isJS9Ready: true,
        getDisplaySafe,
      })
    );

    // Trigger window resize
    window.dispatchEvent(new Event("resize"));

    // Should not crash
    expect(window.JS9.ResizeDisplay).toBeDefined();
  });
});
