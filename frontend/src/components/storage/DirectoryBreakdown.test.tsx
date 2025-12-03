import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DirectoryBreakdown } from "./DirectoryBreakdown";
import type { DirectoryUsage } from "../../types/storage";

const mockDirectories: DirectoryUsage[] = [
  {
    path: "/data/hdf5",
    name: "HDF5 Data",
    size_bytes: 500000000000,
    size_formatted: "500.00 GB",
    file_count: 1500,
    category: "hdf5",
  },
  {
    path: "/data/ms",
    name: "Measurement Sets",
    size_bytes: 300000000000,
    size_formatted: "300.00 GB",
    file_count: 250,
    category: "ms",
  },
  {
    path: "/data/images",
    name: "Images",
    size_bytes: 100000000000,
    size_formatted: "100.00 GB",
    file_count: 5000,
    category: "images",
  },
];

describe("DirectoryBreakdown", () => {
  it("renders directory names and sizes", () => {
    render(<DirectoryBreakdown directories={mockDirectories} />);

    // Names appear in both list and legend
    expect(screen.getAllByText("HDF5 Data").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("500.00 GB")).toBeInTheDocument();
    expect(
      screen.getAllByText("Measurement Sets").length
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("300.00 GB")).toBeInTheDocument();
  });

  it("renders file counts", () => {
    render(<DirectoryBreakdown directories={mockDirectories} />);

    expect(screen.getByText("1,500 files")).toBeInTheDocument();
    expect(screen.getByText("250 files")).toBeInTheDocument();
  });

  it("renders directory paths", () => {
    render(<DirectoryBreakdown directories={mockDirectories} />);

    expect(screen.getByText("/data/hdf5")).toBeInTheDocument();
    expect(screen.getByText("/data/ms")).toBeInTheDocument();
  });

  it("renders total size when provided", () => {
    render(
      <DirectoryBreakdown directories={mockDirectories} totalSize="900.00 GB" />
    );

    expect(screen.getByText("Total: 900.00 GB")).toBeInTheDocument();
  });

  it("renders category legend", () => {
    render(<DirectoryBreakdown directories={mockDirectories} />);

    // Category labels should appear in the legend (may also appear in list)
    expect(screen.getAllByText("HDF5 Data").length).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByText("Measurement Sets").length
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Images").length).toBeGreaterThanOrEqual(1);
  });

  it("shows empty message when no directories", () => {
    render(<DirectoryBreakdown directories={[]} />);

    expect(
      screen.getByText("No directory information available")
    ).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <DirectoryBreakdown
        directories={mockDirectories}
        className="custom-class"
      />
    );

    expect(container.firstChild).toHaveClass("custom-class");
  });
});
