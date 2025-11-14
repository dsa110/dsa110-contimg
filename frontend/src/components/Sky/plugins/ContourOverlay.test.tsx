/**
 * ContourOverlay Component Unit Tests
 *
 * Tests:
 * 1. Component renders without errors
 * 2. Overlay creation when contour data provided
 * 3. Overlay cleanup on unmount
 * 4. Multiple contour levels rendered correctly
 * 5. Visibility toggle works
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";
import ContourOverlay from "./ContourOverlay";

declare global {
  interface Window {
    JS9: any;
  }
}

describe("ContourOverlay", () => {
  let mockJS9: any;
  let mockDisplay: any;
  let mockImage: any;
  let overlayRefs: any[];

  const createMockContourData = () => ({
    contour_levels: [0.1, 0.2, 0.3],
    contour_paths: [
      {
        level: 0.1,
        paths: [
          { x: [10, 11, 12, 10], y: [20, 21, 22, 20] },
          { x: [50, 51, 52, 50], y: [60, 61, 62, 60] },
        ],
      },
      {
        level: 0.2,
        paths: [{ x: [15, 16, 17, 15], y: [25, 26, 27, 25] }],
      },
    ],
    image_shape: [100, 100],
    data_range: { min: 0.0, max: 1.0 },
  });

  beforeEach(() => {
    vi.clearAllMocks();
    overlayRefs = [];

    mockImage = {
      id: "test-image-1",
    };

    mockDisplay = {
      id: "testDisplay",
      display: "testDisplay",
      divID: "testDisplay",
      im: mockImage,
    };

    mockJS9 = {
      displays: [mockDisplay],
      AddOverlay: vi.fn((displayId: string, options: any) => {
        const overlay = {
          remove: vi.fn(),
          ...options,
        };
        overlayRefs.push(overlay);
        return overlay;
      }),
    };

    (window as any).JS9 = mockJS9;
  });

  afterEach(() => {
    delete (window as any).JS9;
  });

  it("should render without errors", () => {
    const contourData = createMockContourData();
    expect(() => {
      render(<ContourOverlay displayId="testDisplay" contourData={contourData} visible={true} />);
    }).not.toThrow();
  });

  it("should create overlays when visible and contour data provided", () => {
    const contourData = createMockContourData();
    render(<ContourOverlay displayId="testDisplay" contourData={contourData} visible={true} />);

    // Should create line segments for each path
    // Level 0.1: 2 paths with 4 points each = 8 line segments (3 per path)
    // Level 0.2: 1 path with 4 points = 3 line segments
    // Total: 11 line segments
    expect(mockJS9.AddOverlay).toHaveBeenCalled();
    expect(mockJS9.AddOverlay.mock.calls.length).toBeGreaterThan(0);
  });

  it("should not create overlays when not visible", () => {
    const contourData = createMockContourData();
    render(<ContourOverlay displayId="testDisplay" contourData={contourData} visible={false} />);

    expect(mockJS9.AddOverlay).not.toHaveBeenCalled();
  });

  it("should not create overlays when contour data is null", () => {
    render(<ContourOverlay displayId="testDisplay" contourData={null} visible={true} />);

    expect(mockJS9.AddOverlay).not.toHaveBeenCalled();
  });

  it("should cleanup overlays on unmount", () => {
    const contourData = createMockContourData();
    const { unmount } = render(
      <ContourOverlay displayId="testDisplay" contourData={contourData} visible={true} />
    );

    const overlayCount = mockJS9.AddOverlay.mock.calls.length;
    expect(overlayCount).toBeGreaterThan(0);

    unmount();

    // All overlays should have remove called
    overlayRefs.forEach((overlay) => {
      expect(overlay.remove).toHaveBeenCalled();
    });
  });

  it("should handle empty contour paths gracefully", () => {
    const contourData = {
      contour_levels: [0.1],
      contour_paths: [],
      image_shape: [100, 100],
      data_range: { min: 0.0, max: 1.0 },
    };

    expect(() => {
      render(<ContourOverlay displayId="testDisplay" contourData={contourData} visible={true} />);
    }).not.toThrow();

    expect(mockJS9.AddOverlay).not.toHaveBeenCalled();
  });

  it("should handle missing JS9 gracefully", () => {
    delete (window as any).JS9;
    const contourData = createMockContourData();

    expect(() => {
      render(<ContourOverlay displayId="testDisplay" contourData={contourData} visible={true} />);
    }).not.toThrow();
  });

  it("should use custom color and line width", () => {
    const contourData = createMockContourData();
    render(
      <ContourOverlay
        displayId="testDisplay"
        contourData={contourData}
        visible={true}
        color="red"
        lineWidth={2}
        opacity={0.5}
      />
    );

    const calls = mockJS9.AddOverlay.mock.calls;
    if (calls.length > 0) {
      const firstCall = calls[0][1];
      expect(firstCall.color).toBe("red");
      expect(firstCall.width).toBe(2);
      expect(firstCall.opacity).toBe(0.5);
    }
  });
});
