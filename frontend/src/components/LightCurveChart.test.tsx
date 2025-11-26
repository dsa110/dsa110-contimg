/**
 * Unit tests for LightCurveChart component
 *
 * Tests the interactive lightcurve visualization including:
 * - Loading states
 * - Error handling
 * - Empty data states
 * - Chart rendering with data
 * - Normalized flux toggle
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import { LightCurveChart, type LightCurveData } from "./LightCurveChart";

// Mock PlotlyLazy to avoid loading Plotly in tests
vi.mock("./PlotlyLazy", () => ({
  PlotlyLazy: ({ data, layout }: any) => (
    <div data-testid="plotly-chart" data-traces={data.length} data-title={layout?.title || ""}>
      Mock Plotly Chart
    </div>
  ),
}));

describe("LightCurveChart", () => {
  const mockLightCurveData: LightCurveData = {
    source_id: "J1234+5678",
    ra_deg: 123.456,
    dec_deg: 56.789,
    flux_points: [
      { mjd: 60000.0, time: "2023-01-01T00:00:00", flux_jy: 0.1, flux_err_jy: 0.01 },
      { mjd: 60001.0, time: "2023-01-02T00:00:00", flux_jy: 0.12, flux_err_jy: 0.015 },
      { mjd: 60002.0, time: "2023-01-03T00:00:00", flux_jy: 0.11, flux_err_jy: 0.012 },
      { mjd: 60003.0, time: "2023-01-04T00:00:00", flux_jy: 0.15, flux_err_jy: 0.02 },
    ],
  };

  const mockNormalizedData: LightCurveData = {
    ...mockLightCurveData,
    normalized_flux_points: [
      { mjd: 60000.0, time: "2023-01-01T00:00:00", flux_jy: 1.0, flux_err_jy: 0.1 },
      { mjd: 60001.0, time: "2023-01-02T00:00:00", flux_jy: 1.2, flux_err_jy: 0.15 },
      { mjd: 60002.0, time: "2023-01-03T00:00:00", flux_jy: 1.1, flux_err_jy: 0.12 },
      { mjd: 60003.0, time: "2023-01-04T00:00:00", flux_jy: 1.5, flux_err_jy: 0.2 },
    ],
  };

  describe("Loading State", () => {
    it("shows loading spinner when isLoading is true", () => {
      render(<LightCurveChart data={null} isLoading={true} />);
      expect(screen.getByText("Loading light curve data...")).toBeInTheDocument();
      expect(screen.getByRole("progressbar")).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("shows error message when error is provided", () => {
      const error = new Error("Failed to fetch data");
      render(<LightCurveChart data={null} error={error} />);
      expect(screen.getByText(/Failed to load light curve/)).toBeInTheDocument();
      expect(screen.getByText(/Failed to fetch data/)).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("shows message when data is null", () => {
      render(<LightCurveChart data={null} />);
      expect(
        screen.getByText("No photometry measurements available for this source")
      ).toBeInTheDocument();
    });

    it("shows message when flux_points is empty", () => {
      const emptyData: LightCurveData = {
        source_id: "test",
        ra_deg: 0,
        dec_deg: 0,
        flux_points: [],
      };
      render(<LightCurveChart data={emptyData} />);
      expect(
        screen.getByText("No photometry measurements available for this source")
      ).toBeInTheDocument();
    });
  });

  describe("Chart Rendering", () => {
    it("renders Plotly chart with data", () => {
      render(<LightCurveChart data={mockLightCurveData} />);
      const chart = screen.getByTestId("plotly-chart");
      expect(chart).toBeInTheDocument();
      // Should have 2 traces: data points + mean line
      expect(chart).toHaveAttribute("data-traces", "2");
    });

    it("does not show toggle when normalized data is absent", () => {
      render(<LightCurveChart data={mockLightCurveData} />);
      expect(screen.queryByRole("group")).not.toBeInTheDocument();
    });
  });

  describe("Normalized Flux Toggle", () => {
    it("shows toggle when normalized data is available", () => {
      render(<LightCurveChart data={mockNormalizedData} />);
      expect(screen.getByRole("button", { name: /Raw Flux/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Normalized/i })).toBeInTheDocument();
    });

    it("defaults to raw flux view", () => {
      render(<LightCurveChart data={mockNormalizedData} />);
      const rawButton = screen.getByRole("button", { name: /Raw Flux/i });
      expect(rawButton).toHaveAttribute("aria-pressed", "true");
    });

    it("switches to normalized view when clicked", () => {
      render(<LightCurveChart data={mockNormalizedData} />);
      const normalizedButton = screen.getByRole("button", { name: /Normalized/i });
      fireEvent.click(normalizedButton);
      expect(normalizedButton).toHaveAttribute("aria-pressed", "true");
    });
  });

  describe("Height Prop", () => {
    it("accepts numeric height", () => {
      render(<LightCurveChart data={mockLightCurveData} height={500} />);
      expect(screen.getByTestId("plotly-chart")).toBeInTheDocument();
    });

    it("accepts string height", () => {
      render(<LightCurveChart data={mockLightCurveData} height="50vh" />);
      expect(screen.getByTestId("plotly-chart")).toBeInTheDocument();
    });
  });
});
