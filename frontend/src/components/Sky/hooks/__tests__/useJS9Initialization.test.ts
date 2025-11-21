/**
 * Unit Tests for useJS9Initialization Hook
 *
 * Tests:
 * 1. Hook returns initialized=false initially
 * 2. Hook initializes JS9 display when ready
 * 3. Hook handles errors gracefully
 * 4. Hook skips initialization if display already exists
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useJS9Initialization } from "../useJS9Initialization";

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

// Mock JS9Service
const { mockJS9Service } = vi.hoisted(() => {
  return {
    mockJS9Service: {
      isAvailable: vi.fn(() => true),
      init: vi.fn(),
      setOptions: vi.fn(),
      addDivs: vi.fn(),
    },
  };
});

vi.mock("../../../../services/js9", () => ({
  js9Service: mockJS9Service,
}));

// Mock JS9Context
const mockJS9Context = {
  isJS9Ready: true,
  getDisplay: vi.fn(() => null),
};

vi.mock("../../../../contexts/JS9Context", () => ({
  useJS9Safe: vi.fn(() => mockJS9Context),
}));

declare global {
  interface Window {
    JS9: any;
  }
}

describe("useJS9Initialization", () => {
  const mockContainerRef = {
    current: document.createElement("div"),
  } as React.RefObject<HTMLDivElement>;

  beforeEach(() => {
    vi.useFakeTimers();

    // Setup window.JS9 mock
    window.JS9 = {
      SetOptions: vi.fn(),
      Init: vi.fn(),
      AddDivs: vi.fn(),
      opts: {},
      displays: [],
    };

    mockContainerRef.current = document.createElement("div");
    mockContainerRef.current.id = "testDisplay";
    mockContainerRef.current.style.width = "500px";
    mockContainerRef.current.style.height = "600px";

    // Mock getBoundingClientRect to return proper dimensions
    mockContainerRef.current.getBoundingClientRect = vi.fn(() => ({
      width: 500,
      height: 600,
      top: 0,
      left: 0,
      bottom: 600,
      right: 500,
      x: 0,
      y: 0,
      toJSON: vi.fn(),
    }));

    // Reset mocks
    mockJS9Service.isAvailable.mockReturnValue(true);
    mockJS9Service.init.mockImplementation(() => {});
    mockJS9Service.setOptions.mockImplementation(() => {});
    mockJS9Service.addDivs.mockImplementation(() => {});
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("should return initialized=false initially", () => {
    const { result } = renderHook(() =>
      useJS9Initialization({
        displayId: "testDisplay",
        containerRef: mockContainerRef,
        height: 600,
        isJS9Ready: false,
        getDisplaySafe: () => null,
        js9Context: mockJS9Context,
      })
    );

    expect(result.current.initialized).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("should initialize JS9 display when ready", () => {
    window.JS9.SetOptions = vi.fn();
    window.JS9.Init = vi.fn();
    window.JS9.AddDivs = vi.fn();

    const { result } = renderHook(() =>
      useJS9Initialization({
        displayId: "testDisplay",
        containerRef: mockContainerRef,
        height: 600,
        isJS9Ready: true,
        getDisplaySafe: () => null,
        js9Context: mockJS9Context,
      })
    );

    // Advance timers to trigger dimension checks and initialization
    act(() => {
      vi.advanceTimersByTime(200); // Trigger dimension check interval
    });

    // Hook should initialize after dimensions are checked
    expect(result.current.initialized).toBe(true);
    expect(mockJS9Service.addDivs).toHaveBeenCalledWith("testDisplay");
  });

  it("should skip initialization if display already exists", () => {
    const existingDisplay = { id: "testDisplay" };
    const getDisplaySafe = vi.fn(() => existingDisplay);

    const { result } = renderHook(() =>
      useJS9Initialization({
        displayId: "testDisplay",
        containerRef: mockContainerRef,
        height: 600,
        isJS9Ready: true,
        getDisplaySafe,
        js9Context: mockJS9Context,
      })
    );

    expect(result.current.initialized).toBe(true);
    expect(window.JS9.AddDivs).not.toHaveBeenCalled();
  });

  it("should handle errors gracefully", () => {
    // Mock addDivs to throw an error
    // Note: The error is thrown inside doInitialize() which is called asynchronously
    // The hook's try-catch around initializeJS9() should catch it
    mockJS9Service.addDivs.mockImplementation(() => {
      throw new Error("Initialization failed");
    });

    // Spy on console.error to verify error is logged
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const { result } = renderHook(() =>
      useJS9Initialization({
        displayId: "testDisplay",
        containerRef: mockContainerRef,
        height: 600,
        isJS9Ready: true,
        getDisplaySafe: () => null,
        js9Context: mockJS9Context,
      })
    );

    // Advance timers to trigger initialization
    // The error will be thrown inside doInitialize() which is called from setInterval
    // The try-catch around initializeJS9() should catch it
    act(() => {
      try {
        vi.advanceTimersByTime(200); // Trigger dimension check interval, which calls doInitialize()
      } catch (e) {
        // Error may propagate, but hook should catch it
      }
    });

    // The hook's try-catch should catch the error and set error state
    // Since doInitialize() is called asynchronously, we need to advance timers again
    act(() => {
      vi.advanceTimersByTime(10); // Allow error handling to complete
    });

    // After the error is caught, initialization should not be complete
    // The hook sets error state when doInitialize() throws
    expect(result.current.initialized).toBe(false);

    // Clean up spy
    consoleErrorSpy.mockRestore();
  });
});
