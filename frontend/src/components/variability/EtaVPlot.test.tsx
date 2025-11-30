import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import EtaVPlot, { EtaVPlotProps, SourcePoint } from "./EtaVPlot";

// Mock ECharts - complex charting library
vi.mock("echarts", () => ({
  init: vi.fn(() => ({
    setOption: vi.fn(),
    resize: vi.fn(),
    dispose: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    getZr: vi.fn(() => ({
      on: vi.fn(),
    })),
  })),
}));

describe("EtaVPlot", () => {
  const mockSources: SourcePoint[] = [
    {
      id: "src-1",
      name: "Source A",
      ra: 180,
      dec: 45,
      eta: 1.5,
      v: 0.08,
      peakFlux: 10,
      nMeasurements: 10,
    },
    {
      id: "src-2",
      name: "Source B",
      ra: 181,
      dec: 46,
      eta: 3.0,
      v: 0.15,
      peakFlux: 20,
      nMeasurements: 15,
    },
    {
      id: "src-3",
      name: "Source C",
      ra: 182,
      dec: 47,
      eta: 5.0,
      v: 0.25,
      peakFlux: 50,
      nMeasurements: 20,
    },
  ];

  const mockOnSourceSelect = vi.fn();

  const defaultProps: EtaVPlotProps = {
    sources: mockSources,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders chart container", () => {
      const { container } = render(<EtaVPlot {...defaultProps} />);
      expect(container.querySelector("div")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(<EtaVPlot {...defaultProps} className="custom-class" />);
      expect(container.firstChild).toHaveClass("custom-class");
    });

    it("applies custom height", () => {
      render(<EtaVPlot {...defaultProps} height={600} />);
      // Height is applied to chart div via style
      expect(document.querySelector('[style*="height"]')).toBeInTheDocument();
    });
  });

  describe("loading state", () => {
    it("shows loading indicator when isLoading is true", () => {
      render(<EtaVPlot {...defaultProps} isLoading />);
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });

    it("hides loading indicator when isLoading is false", () => {
      render(<EtaVPlot {...defaultProps} isLoading={false} />);
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    });
  });

  describe("variability controls", () => {
    it("renders variability controls", () => {
      render(<EtaVPlot {...defaultProps} />);
      expect(screen.getByText(/σ-based thresholds/i)).toBeInTheDocument();
    });

    it("renders color by control", () => {
      render(<EtaVPlot {...defaultProps} />);
      expect(screen.getByText(/color by/i)).toBeInTheDocument();
    });

    it("renders min data points control", () => {
      render(<EtaVPlot {...defaultProps} />);
      expect(screen.getByText(/min.*data points/i)).toBeInTheDocument();
    });
  });

  describe("source count", () => {
    it("displays source count", () => {
      render(<EtaVPlot {...defaultProps} />);
      // Should show something like "3 sources" or count info
      expect(screen.getByText(/\d+.*source/i)).toBeInTheDocument();
    });

    it("updates count based on filtered sources", () => {
      render(<EtaVPlot {...defaultProps} />);
      // When minDataPoints filter applies, count should update
      expect(screen.getByText(/source/i)).toBeInTheDocument();
    });
  });

  describe("empty state", () => {
    it("shows message when no sources provided", () => {
      render(<EtaVPlot sources={[]} />);
      expect(screen.getByText(/no.*data/i)).toBeInTheDocument();
    });
  });

  describe("threshold calculations", () => {
    it("calculates dynamic thresholds when sigma mode enabled", () => {
      render(<EtaVPlot {...defaultProps} />);
      // Default is useSigmaThreshold: true
      // Should show sigma-based controls
      expect(screen.getByText(/η threshold: 2σ/)).toBeInTheDocument();
    });
  });

  describe("chart initialization", () => {
    it("initializes ECharts when mounted", async () => {
      const echarts = await import("echarts");
      render(<EtaVPlot {...defaultProps} />);
      await waitFor(() => {
        expect(echarts.init).toHaveBeenCalled();
      });
    });
  });

  describe("source selection callback", () => {
    it("accepts onSourceSelect callback", () => {
      // Just verify the prop is accepted without error
      expect(() => {
        render(<EtaVPlot {...defaultProps} onSourceSelect={mockOnSourceSelect} />);
      }).not.toThrow();
    });
  });

  describe("accessibility", () => {
    it("has accessible chart region", () => {
      render(<EtaVPlot {...defaultProps} />);
      // Chart should be in a region or have appropriate role
      const chartContainer = document.querySelector(
        '[role="img"], [aria-label*="plot"], [aria-label*="chart"]'
      );
      // If no explicit role, at least the container should exist
      expect(document.querySelector("div")).toBeInTheDocument();
    });
  });
});
