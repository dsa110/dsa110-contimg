/**
 * ResourceMetricsPanel Tests
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ResourceMetricsPanel } from "./ResourceMetricsPanel";
import type { ResourceMetricsDetailed } from "../../types/prometheus";

const mockResourceMetrics: ResourceMetricsDetailed = {
  cpu: {
    id: "cpu",
    name: "CPU",
    description: "CPU usage",
    unit: "%",
    current: 65,
    trend: "up",
    trendPercent: 5,
    status: "healthy",
    history: [
      { timestamp: 1700000000, value: 60 },
      { timestamp: 1700000060, value: 62 },
      { timestamp: 1700000120, value: 65 },
    ],
  },
  memory: {
    id: "memory",
    name: "Memory",
    description: "Memory usage",
    unit: "bytes",
    current: 8e9,
    total: 16e9,
    trend: "stable",
    trendPercent: 0.5,
    status: "healthy",
    history: [
      { timestamp: 1700000000, value: 7.8e9 },
      { timestamp: 1700000060, value: 7.9e9 },
      { timestamp: 1700000120, value: 8e9 },
    ],
  },
  diskIO: {
    id: "disk-io",
    name: "Disk I/O",
    description: "Disk throughput",
    unit: "bytes",
    current: 100e6,
    trend: "down",
    trendPercent: 10,
    status: "healthy",
    history: [
      { timestamp: 1700000000, value: 110e6 },
      { timestamp: 1700000060, value: 105e6 },
      { timestamp: 1700000120, value: 100e6 },
    ],
  },
  network: {
    id: "network",
    name: "Network I/O",
    description: "Network throughput",
    unit: "bytes",
    current: 50e6,
    trend: "stable",
    trendPercent: 2,
    status: "healthy",
    history: [
      { timestamp: 1700000000, value: 48e6 },
      { timestamp: 1700000060, value: 49e6 },
      { timestamp: 1700000120, value: 50e6 },
    ],
  },
};

describe("ResourceMetricsPanel", () => {
  it("renders panel header", () => {
    render(<ResourceMetricsPanel metrics={mockResourceMetrics} />);

    expect(screen.getByText("System Resources")).toBeInTheDocument();
    expect(
      screen.getByText("Real-time system resource utilization")
    ).toBeInTheDocument();
  });

  it("displays CPU gauge", () => {
    render(<ResourceMetricsPanel metrics={mockResourceMetrics} />);

    // CPU appears in both gauge and chart, so use getAllBy
    expect(screen.getAllByText("CPU").length).toBeGreaterThan(0);
    expect(screen.getAllByText("65.0%").length).toBeGreaterThan(0);
  });

  it("displays Memory gauge with total", () => {
    render(<ResourceMetricsPanel metrics={mockResourceMetrics} />);

    expect(screen.getByText("Memory")).toBeInTheDocument();
    expect(screen.getByText("8.0 GB / 16.0 GB")).toBeInTheDocument();
  });

  it("displays Disk I/O gauge", () => {
    render(<ResourceMetricsPanel metrics={mockResourceMetrics} />);

    expect(screen.getAllByText("Disk I/O").length).toBeGreaterThan(0);
    expect(screen.getAllByText("100.0 MB").length).toBeGreaterThan(0);
  });

  it("displays Network gauge", () => {
    render(<ResourceMetricsPanel metrics={mockResourceMetrics} />);

    expect(screen.getAllByText("Network").length).toBeGreaterThan(0);
    expect(screen.getAllByText("50.0 MB").length).toBeGreaterThan(0);
  });

  it("renders charts when showCharts is true", () => {
    const { container } = render(
      <ResourceMetricsPanel metrics={mockResourceMetrics} showCharts />
    );

    // Should have 4 charts (one for each resource)
    const charts = container.querySelectorAll("svg");
    expect(charts.length).toBeGreaterThanOrEqual(4);
  });

  it("hides charts when showCharts is false", () => {
    render(
      <ResourceMetricsPanel metrics={mockResourceMetrics} showCharts={false} />
    );

    // Chart titles should not be in detailed section
    expect(screen.queryByText("CPU Usage")).not.toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <ResourceMetricsPanel
        metrics={mockResourceMetrics}
        className="custom-class"
      />
    );

    expect(container.firstChild).toHaveClass("custom-class");
  });

  it("handles warning status", () => {
    const warningMetrics = {
      ...mockResourceMetrics,
      cpu: { ...mockResourceMetrics.cpu, status: "warning" as const },
    };
    render(<ResourceMetricsPanel metrics={warningMetrics} />);

    // CPU value appears in multiple places with warning status
    expect(screen.getAllByText("65.0%").length).toBeGreaterThan(0);
  });

  it("handles critical status", () => {
    const criticalMetrics = {
      ...mockResourceMetrics,
      memory: { ...mockResourceMetrics.memory, status: "critical" as const },
    };
    render(<ResourceMetricsPanel metrics={criticalMetrics} />);

    expect(screen.getByText("8.0 GB / 16.0 GB")).toBeInTheDocument();
  });
});
