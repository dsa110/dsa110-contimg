import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import GifPlayer from "../components/widgets/GifPlayer";

// Create proper mock ImageData
const createMockImageData = () => ({
  data: new Uint8ClampedArray(100 * 100 * 4),
  width: 100,
  height: 100,
  colorSpace: "srgb" as PredefinedColorSpace,
});

describe("GifPlayer", () => {
  let mockCanvasContext: any;

  beforeEach(() => {
    vi.clearAllMocks();

    // Create mock canvas context
    mockCanvasContext = {
      putImageData: vi.fn(),
      getImageData: vi.fn().mockReturnValue(createMockImageData()),
      drawImage: vi.fn(),
    };

    // Mock HTMLCanvasElement.getContext
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(mockCanvasContext as any);

    // Mock Image constructor that loads via microtask
    (global as any).Image = class {
      crossOrigin = "";
      onload: (() => void) | null = null;
      onerror: ((e: Error) => void) | null = null;
      width = 100;
      height = 100;
      private _src = "";

      get src() {
        return this._src;
      }

      set src(value: string) {
        this._src = value;
        Promise.resolve().then(() => {
          if (this.onload) this.onload();
        });
      }
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state initially", () => {
    // Override to never complete loading
    (global as any).Image = class {
      crossOrigin = "";
      onload: (() => void) | null = null;
      onerror: ((e: Error) => void) | null = null;
      width = 100;
      height = 100;
      set src(_value: string) {
        // Don't call onload - stay in loading state
      }
    };

    render(<GifPlayer src="/test.gif" />);
    expect(screen.getByText("Loading animation...")).toBeInTheDocument();
  });

  it("loads and displays the GIF", async () => {
    render(<GifPlayer src="/test.gif" width={400} height={300} />);

    await waitFor(() => {
      expect(screen.queryByText("Loading animation...")).not.toBeInTheDocument();
    });

    // Canvas should be rendered
    expect(document.querySelector("canvas")).toBeInTheDocument();
  });

  it("displays error state when image fails to load", async () => {
    // Override Image mock to trigger error
    (global as any).Image = class {
      crossOrigin = "";
      onload: (() => void) | null = null;
      onerror: ((e: Error) => void) | null = null;
      private _src = "";

      set src(_value: string) {
        this._src = _value;
        Promise.resolve().then(() => {
          if (this.onerror) this.onerror(new Error("Failed to load image"));
        });
      }
    };

    render(<GifPlayer src="/invalid.gif" />);

    await waitFor(() => {
      expect(screen.getByText("Failed to load image")).toBeInTheDocument();
    });
  });

  it("shows canvas when loaded", async () => {
    render(<GifPlayer src="/test.gif" showFrameCounter={true} />);

    await waitFor(() => {
      expect(document.querySelector("canvas")).toBeInTheDocument();
    });
  });

  it("hides frame counter when showFrameCounter is false", async () => {
    render(<GifPlayer src="/test.gif" showFrameCounter={false} />);

    await waitFor(() => {
      expect(document.querySelector("canvas")).toBeInTheDocument();
    });

    // No frame counter should be visible (single frame anyway)
    expect(screen.queryByText(/\d+ \/ \d+/)).not.toBeInTheDocument();
  });

  it("applies custom className", async () => {
    const { container } = render(<GifPlayer src="/test.gif" className="custom-class" />);

    await waitFor(() => {
      expect(screen.queryByText("Loading animation...")).not.toBeInTheDocument();
    });

    expect(container.firstChild).toHaveClass("custom-class");
  });

  it("calls onFrameChange callback when frame changes", async () => {
    const onFrameChange = vi.fn();
    render(<GifPlayer src="/test.gif" onFrameChange={onFrameChange} />);

    await waitFor(() => {
      expect(onFrameChange).toHaveBeenCalled();
    });
  });

  it("respects width and height props", async () => {
    const { container } = render(<GifPlayer src="/test.gif" width={500} height={400} />);

    await waitFor(() => {
      expect(screen.queryByText("Loading animation...")).not.toBeInTheDocument();
    });

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.style.width).toBe("500px");
  });

  it("handles string width values", async () => {
    const { container } = render(<GifPlayer src="/test.gif" width="100%" />);

    await waitFor(() => {
      expect(screen.queryByText("Loading animation...")).not.toBeInTheDocument();
    });

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.style.width).toBe("100%");
  });
});
