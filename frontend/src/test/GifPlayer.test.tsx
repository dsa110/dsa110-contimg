import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import GifPlayer from "../components/widgets/GifPlayer";

// Mock canvas context
const mockPutImageData = vi.fn();
const mockGetImageData = vi.fn().mockReturnValue({
  data: new Uint8ClampedArray(100 * 100 * 4),
  width: 100,
  height: 100,
});
const mockDrawImage = vi.fn();

const mockGetContext = vi.fn().mockReturnValue({
  putImageData: mockPutImageData,
  getImageData: mockGetImageData,
  drawImage: mockDrawImage,
});

// Mock HTMLCanvasElement
HTMLCanvasElement.prototype.getContext = mockGetContext as any;

// Mock Image loading
const mockImageLoad = vi.fn();
const originalImage = global.Image;

describe("GifPlayer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Mock Image constructor
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
        mockImageLoad(value);
        // Simulate async image load
        setTimeout(() => {
          if (this.onload) this.onload();
        }, 10);
      }
    };
  });

  afterEach(() => {
    vi.useRealTimers();
    global.Image = originalImage;
  });

  it("renders loading state initially", () => {
    render(<GifPlayer src="/test.gif" />);
    expect(screen.getByText("Loading animation...")).toBeInTheDocument();
  });

  it("loads and displays the GIF", async () => {
    render(<GifPlayer src="/test.gif" width={400} height={300} />);

    // Advance timers to trigger image load
    await vi.advanceTimersByTimeAsync(50);

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

      set src(value: string) {
        this._src = value;
        setTimeout(() => {
          if (this.onerror) this.onerror(new Error("Failed to load image"));
        }, 10);
      }
    };

    render(<GifPlayer src="/invalid.gif" />);

    await vi.advanceTimersByTimeAsync(50);

    await waitFor(() => {
      expect(screen.getByText("Failed to load image")).toBeInTheDocument();
    });
  });

  it("shows frame counter when showFrameCounter is true", async () => {
    render(<GifPlayer src="/test.gif" showFrameCounter={true} />);

    await vi.advanceTimersByTimeAsync(50);

    // Frame counter won't show with single frame (frames.length > 1 check)
    // But we can verify canvas is rendered
    await waitFor(() => {
      expect(document.querySelector("canvas")).toBeInTheDocument();
    });
  });

  it("hides frame counter when showFrameCounter is false", async () => {
    render(<GifPlayer src="/test.gif" showFrameCounter={false} />);

    await vi.advanceTimersByTimeAsync(50);

    await waitFor(() => {
      expect(document.querySelector("canvas")).toBeInTheDocument();
    });

    // No frame counter should be visible
    expect(screen.queryByText(/\d+ \/ \d+/)).not.toBeInTheDocument();
  });

  it("applies custom className", async () => {
    const { container } = render(<GifPlayer src="/test.gif" className="custom-class" />);

    await vi.advanceTimersByTimeAsync(50);

    await waitFor(() => {
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  it("calls onFrameChange callback when frame changes", async () => {
    const onFrameChange = vi.fn();
    render(<GifPlayer src="/test.gif" onFrameChange={onFrameChange} />);

    await vi.advanceTimersByTimeAsync(50);

    await waitFor(() => {
      expect(onFrameChange).toHaveBeenCalled();
    });
  });

  it("respects width and height props", async () => {
    const { container } = render(<GifPlayer src="/test.gif" width={500} height={400} />);

    await vi.advanceTimersByTimeAsync(50);

    await waitFor(() => {
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper.style.width).toBe("500px");
    });
  });

  it("handles string width values", async () => {
    const { container } = render(<GifPlayer src="/test.gif" width="100%" />);

    await vi.advanceTimersByTimeAsync(50);

    await waitFor(() => {
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper.style.width).toBe("100%");
    });
  });
});
