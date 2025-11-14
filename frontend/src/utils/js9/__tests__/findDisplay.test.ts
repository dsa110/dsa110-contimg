/**
 * Unit tests for JS9 display finding utilities
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { findDisplay, isJS9Available, getDisplayImageId } from "../findDisplay";

// Mock window.JS9
const mockJS9 = {
  displays: [] as any[],
  Load: vi.fn(),
};

describe("findDisplay", () => {
  beforeEach(() => {
    // Reset window.JS9
    (window as any).JS9 = { ...mockJS9 };
    mockJS9.displays = [];
  });

  afterEach(() => {
    delete (window as any).JS9;
  });

  it("should return null when JS9 is not available", () => {
    delete (window as any).JS9;

    expect(findDisplay("test-display")).toBeNull();
  });

  it("should return null when JS9.displays is not available", () => {
    (window as any).JS9 = {};

    expect(findDisplay("test-display")).toBeNull();
  });

  it("should return null when display not found", () => {
    mockJS9.displays = [{ id: "display1" }, { id: "display2" }];

    expect(findDisplay("display3")).toBeNull();
  });

  it("should find display by id property", () => {
    const display = { id: "test-display", name: "Test Display" };
    mockJS9.displays = [display];
    (window as any).JS9 = { ...mockJS9 };

    expect(findDisplay("test-display")).toBe(display);
  });

  it("should find display by display property", () => {
    const display = { display: "test-display", name: "Test Display" };
    mockJS9.displays = [display];
    (window as any).JS9 = { ...mockJS9 };

    expect(findDisplay("test-display")).toBe(display);
  });

  it("should find display by divID property", () => {
    const display = { divID: "test-display", name: "Test Display" };
    mockJS9.displays = [display];
    (window as any).JS9 = { ...mockJS9 };

    expect(findDisplay("test-display")).toBe(display);
  });

  it("should return first matching display when multiple exist", () => {
    const display1 = { id: "test-display", name: "Display 1" };
    const display2 = { id: "test-display", name: "Display 2" };
    mockJS9.displays = [display1, display2];
    (window as any).JS9 = { ...mockJS9 };

    expect(findDisplay("test-display")).toBe(display1);
  });

  it("should handle empty displays array", () => {
    mockJS9.displays = [];
    (window as any).JS9 = { ...mockJS9 };

    expect(findDisplay("test-display")).toBeNull();
  });
});

describe("isJS9Available", () => {
  beforeEach(() => {
    delete (window as any).JS9;
  });

  afterEach(() => {
    delete (window as any).JS9;
  });

  it("should return false when JS9 is not available", () => {
    expect(isJS9Available()).toBe(false);
  });

  it("should return false when JS9 exists but Load is not a function", () => {
    (window as any).JS9 = {};

    expect(isJS9Available()).toBe(false);
  });

  it("should return false when JS9.Load is not a function", () => {
    (window as any).JS9 = { Load: "not a function" };

    expect(isJS9Available()).toBe(false);
  });

  it("should return true when JS9 is available and Load is a function", () => {
    (window as any).JS9 = {
      Load: vi.fn(),
    };

    expect(isJS9Available()).toBe(true);
  });
});

describe("getDisplayImageId", () => {
  beforeEach(() => {
    (window as any).JS9 = { ...mockJS9 };
    mockJS9.displays = [];
  });

  afterEach(() => {
    delete (window as any).JS9;
  });

  it("should return null when display not found", () => {
    mockJS9.displays = [{ id: "display1" }];

    expect(getDisplayImageId("display2")).toBeNull();
  });

  it("should return null when display has no image", () => {
    const display = { id: "test-display" };
    mockJS9.displays = [display];

    expect(getDisplayImageId("test-display")).toBeNull();
  });

  it("should return null when display.im is null", () => {
    const display = { id: "test-display", im: null };
    mockJS9.displays = [display];

    expect(getDisplayImageId("test-display")).toBeNull();
  });

  it("should return image id when available", () => {
    const display = {
      id: "test-display",
      im: { id: "image-123" },
    };
    mockJS9.displays = [display];
    (window as any).JS9 = { ...mockJS9 };

    expect(getDisplayImageId("test-display")).toBe("image-123");
  });

  it("should return null when JS9 is not available", () => {
    delete (window as any).JS9;

    expect(getDisplayImageId("test-display")).toBeNull();
  });
});
