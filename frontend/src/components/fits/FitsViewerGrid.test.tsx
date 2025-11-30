import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import FitsViewerGrid from "./FitsViewerGrid";

// Mock the FitsViewer component
vi.mock("./FitsViewer", () => ({
  default: vi.fn(({ fitsUrl, displayId, width, height, onLoad, onCoordinateClick, ...rest }) => (
    <div
      data-testid={`fits-viewer-${displayId}`}
      data-url={fitsUrl}
      data-width={width}
      data-height={height}
      data-extra-props={JSON.stringify(rest)}
    >
      <button onClick={onLoad}>Load</button>
      {onCoordinateClick && (
        <button onClick={() => onCoordinateClick(10.5, -20.3)}>Click Coords</button>
      )}
    </div>
  )),
}));

// Mock window.JS9
const mockJS9 = {
  SetZoom: vi.fn(),
  SetPan: vi.fn(),
  SetColormap: vi.fn(),
  GetZoom: vi.fn().mockReturnValue(2),
  GetPan: vi.fn().mockReturnValue({ x: 100, y: 100 }),
  SetCallback: vi.fn(),
  RemoveCallback: vi.fn(),
};

describe("FitsViewerGrid", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (window as any).JS9 = mockJS9;
  });

  it("renders empty state when no FITS URLs provided", () => {
    render(<FitsViewerGrid fitsUrls={[]} />);
    expect(screen.getByText("No FITS files to display")).toBeInTheDocument();
  });

  it("renders correct number of viewers for given URLs", () => {
    const urls = ["/fits/image1.fits", "/fits/image2.fits", "/fits/image3.fits"];
    render(<FitsViewerGrid fitsUrls={urls} />);

    expect(screen.getByTestId("fits-viewer-JS9Grid_0")).toBeInTheDocument();
    expect(screen.getByTestId("fits-viewer-JS9Grid_1")).toBeInTheDocument();
    expect(screen.getByTestId("fits-viewer-JS9Grid_2")).toBeInTheDocument();
  });

  it("displays labels when provided", () => {
    const urls = ["/fits/image1.fits", "/fits/image2.fits"];
    const labels = ["Epoch 1", "Epoch 2"];
    render(<FitsViewerGrid fitsUrls={urls} labels={labels} />);

    expect(screen.getByText("Epoch 1")).toBeInTheDocument();
    expect(screen.getByText("Epoch 2")).toBeInTheDocument();
  });

  it("shows correct loaded count", () => {
    const urls = ["/fits/image1.fits", "/fits/image2.fits"];
    render(<FitsViewerGrid fitsUrls={urls} />);

    // Initially 0 loaded
    expect(screen.getByText("0/2 images loaded")).toBeInTheDocument();

    // Simulate loading first image
    const loadButtons = screen.getAllByText("Load");
    fireEvent.click(loadButtons[0]);

    expect(screen.getByText("1/2 images loaded")).toBeInTheDocument();
  });

  it("has sync toggle checkbox", () => {
    const urls = ["/fits/image1.fits", "/fits/image2.fits"];
    render(<FitsViewerGrid fitsUrls={urls} />);

    const syncCheckbox = screen.getByRole("checkbox");
    expect(syncCheckbox).toBeInTheDocument();
    expect(syncCheckbox).toBeChecked(); // Default is true
  });

  it("respects syncViews prop for initial state", () => {
    const urls = ["/fits/image1.fits", "/fits/image2.fits"];
    render(<FitsViewerGrid fitsUrls={urls} syncViews={false} />);

    const syncCheckbox = screen.getByRole("checkbox");
    expect(syncCheckbox).not.toBeChecked();
  });

  it("toggles sync state when checkbox clicked", () => {
    const urls = ["/fits/image1.fits", "/fits/image2.fits"];
    render(<FitsViewerGrid fitsUrls={urls} />);

    const syncCheckbox = screen.getByRole("checkbox");
    expect(syncCheckbox).toBeChecked();

    fireEvent.click(syncCheckbox);
    expect(syncCheckbox).not.toBeChecked();
  });

  it("passes viewerProps to FitsViewer components", () => {
    const urls = ["/fits/image1.fits"];
    const viewerProps = {
      initialCenter: { ra: 180, dec: 45 },
      initialFov: 10,
      className: "custom-viewer",
    };

    render(<FitsViewerGrid fitsUrls={urls} viewerProps={viewerProps} />);

    const viewer = screen.getByTestId("fits-viewer-JS9Grid_0");
    const extraProps = JSON.parse(viewer.getAttribute("data-extra-props") || "{}");

    expect(extraProps.initialCenter).toEqual({ ra: 180, dec: 45 });
    expect(extraProps.initialFov).toBe(10);
    expect(extraProps.className).toBe("custom-viewer");
  });

  it("calls onCoordinateClick with panel index", () => {
    const urls = ["/fits/image1.fits", "/fits/image2.fits"];
    const onCoordinateClick = vi.fn();

    render(<FitsViewerGrid fitsUrls={urls} onCoordinateClick={onCoordinateClick} />);

    const coordButtons = screen.getAllByText("Click Coords");
    fireEvent.click(coordButtons[1]); // Click second viewer

    expect(onCoordinateClick).toHaveBeenCalledWith(10.5, -20.3, 1);
  });

  it("applies correct grid classes for different column counts", () => {
    const urls = ["/fits/image1.fits", "/fits/image2.fits"];

    const { rerender, container } = render(<FitsViewerGrid fitsUrls={urls} columns={1} />);
    expect(container.querySelector(".grid-cols-1")).toBeInTheDocument();

    rerender(<FitsViewerGrid fitsUrls={urls} columns={2} />);
    expect(container.querySelector(".grid-cols-2")).toBeInTheDocument();

    rerender(<FitsViewerGrid fitsUrls={urls} columns={3} />);
    expect(container.querySelector(".grid-cols-3")).toBeInTheDocument();

    rerender(<FitsViewerGrid fitsUrls={urls} columns={4} />);
    expect(container.querySelector(".grid-cols-4")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const urls = ["/fits/image1.fits"];
    const { container } = render(<FitsViewerGrid fitsUrls={urls} className="my-custom-grid" />);

    expect(container.firstChild).toHaveClass("my-custom-grid");
  });

  it("passes viewerSize to FitsViewer components", () => {
    const urls = ["/fits/image1.fits"];
    render(<FitsViewerGrid fitsUrls={urls} viewerSize={400} />);

    const viewer = screen.getByTestId("fits-viewer-JS9Grid_0");
    expect(viewer.getAttribute("data-width")).toBe("400");
    expect(viewer.getAttribute("data-height")).toBe("400");
  });

  it("renders grid control buttons", () => {
    const urls = ["/fits/image1.fits"];
    render(<FitsViewerGrid fitsUrls={urls} />);

    expect(screen.getByText("Fit All")).toBeInTheDocument();
    expect(screen.getByText("Zoom In All")).toBeInTheDocument();
    expect(screen.getByText("Zoom Out All")).toBeInTheDocument();
    expect(screen.getByText("Grid Controls:")).toBeInTheDocument();
  });

  it("calls JS9.SetZoom for all viewers when Fit All clicked", () => {
    const urls = ["/fits/image1.fits", "/fits/image2.fits"];
    render(<FitsViewerGrid fitsUrls={urls} />);

    fireEvent.click(screen.getByText("Fit All"));

    expect(mockJS9.SetZoom).toHaveBeenCalledWith("tofit", { display: "JS9Grid_0" });
    expect(mockJS9.SetZoom).toHaveBeenCalledWith("tofit", { display: "JS9Grid_1" });
  });

  it("calls JS9.SetZoom for all viewers when Zoom In All clicked", () => {
    const urls = ["/fits/image1.fits", "/fits/image2.fits"];
    render(<FitsViewerGrid fitsUrls={urls} />);

    fireEvent.click(screen.getByText("Zoom In All"));

    expect(mockJS9.SetZoom).toHaveBeenCalledWith("in", { display: "JS9Grid_0" });
    expect(mockJS9.SetZoom).toHaveBeenCalledWith("in", { display: "JS9Grid_1" });
  });

  it("calls JS9.SetColormap when colormap selection changes", () => {
    const urls = ["/fits/image1.fits"];
    render(<FitsViewerGrid fitsUrls={urls} />);

    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "heat" } });

    expect(mockJS9.SetColormap).toHaveBeenCalledWith("heat", { display: "JS9Grid_0" });
  });
});
