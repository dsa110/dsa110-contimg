/**
 * MetricsTimeSeriesChart Tests
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricsTimeSeriesChart } from "./MetricsTimeSeriesChart";
import type { SystemMetric } from "../../types/prometheus";

const mockMetric: SystemMetric = {
  id: "cpu",
  name: "CPU Usage",
  description: "Processor utilization",
  unit: "%",
  current: 45.5,
  trend: "up",
  trendPercent: 5.2,
  status: "healthy",
  history: [
    { timestamp: 1700000000, value: 40 },
    { timestamp: 1700000060, value: 42 },
    { timestamp: 1700000120, value: 45 },
    { timestamp: 1700000180, value: 45.5 },
  ],
};

describe("MetricsTimeSeriesChart", () => {
  it("renders metric name and description", () => {
    render(<MetricsTimeSeriesChart metric={mockMetric} />);

    expect(screen.getByText("CPU Usage")).toBeInTheDocument();
    expect(screen.getByText("Processor utilization")).toBeInTheDocument();
  });

  it("displays current value with unit", () => {
    render(<MetricsTimeSeriesChart metric={mockMetric} />);

    expect(screen.getByText("45.5%")).toBeInTheDocument();
  });

  it("shows trend indicator", () => {
    render(<MetricsTimeSeriesChart metric={mockMetric} />);

    expect(screen.getByText("↑")).toBeInTheDocument();
    expect(screen.getByText("5.2%")).toBeInTheDocument();
  });

  it("displays status when showLegend is true", () => {
    render(<MetricsTimeSeriesChart metric={mockMetric} showLegend />);

    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("healthy")).toBeInTheDocument();
  });

  it("shows insufficient data message when history is empty", () => {
    const emptyMetric = { ...mockMetric, history: [] };
    render(<MetricsTimeSeriesChart metric={emptyMetric} />);

    expect(screen.getByText("Insufficient data")).toBeInTheDocument();
  });

  it("renders SVG chart when history has data", () => {
    const { container } = render(
      <MetricsTimeSeriesChart metric={mockMetric} />
    );

    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("applies custom height", () => {
    const { container } = render(
      <MetricsTimeSeriesChart metric={mockMetric} height={200} />
    );

    const chartContainer = container.querySelector('[style*="height"]');
    expect(chartContainer).toBeInTheDocument();
  });

  it("renders with warning status styling", () => {
    const warningMetric = { ...mockMetric, status: "warning" as const };
    render(<MetricsTimeSeriesChart metric={warningMetric} showLegend />);

    expect(screen.getByText("warning")).toBeInTheDocument();
  });

  it("renders with critical status styling", () => {
    const criticalMetric = { ...mockMetric, status: "critical" as const };
    render(<MetricsTimeSeriesChart metric={criticalMetric} showLegend />);

    expect(screen.getByText("critical")).toBeInTheDocument();
  });

  it("formats bytes correctly", () => {
    const bytesMetric: SystemMetric = {
      ...mockMetric,
      unit: "bytes",
      current: 1.5e9,
    };
    render(<MetricsTimeSeriesChart metric={bytesMetric} />);

    expect(screen.getByText("1.5 GB")).toBeInTheDocument();
  });
});
