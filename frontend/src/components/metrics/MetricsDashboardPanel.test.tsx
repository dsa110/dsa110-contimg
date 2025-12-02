/**
 * MetricsDashboardPanel Tests
 */

import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MetricsDashboardPanel } from "./MetricsDashboardPanel";
import type { MetricsDashboard } from "../../types/prometheus";

const mockDashboard: MetricsDashboard = {
  resources: {
    cpu_percent: 45,
    memory_percent: 60,
    disk_io_mbps: 100,
    network_io_mbps: 50,
  },
  pipeline: {
    jobs_per_hour: 12,
    avg_job_duration_sec: 30,
    success_rate_percent: 98,
    queue_depth: 5,
    active_workers: 4,
    total_workers: 6,
  },
  metrics: [
    {
      id: "cpu",
      name: "CPU Usage",
      description: "CPU utilization",
      unit: "%",
      current: 45,
      trend: "stable",
      trendPercent: 2,
      status: "healthy",
      history: [
        { timestamp: 1700000000, value: 44 },
        { timestamp: 1700000060, value: 45 },
      ],
    },
    {
      id: "memory",
      name: "Memory Usage",
      description: "RAM utilization",
      unit: "%",
      current: 60,
      trend: "up",
      trendPercent: 5,
      status: "healthy",
      history: [
        { timestamp: 1700000000, value: 58 },
        { timestamp: 1700000060, value: 60 },
      ],
    },
  ],
  updated_at: "2024-01-01T12:00:00Z",
};

describe("MetricsDashboardPanel", () => {
  it("renders panel header", () => {
    render(<MetricsDashboardPanel data={mockDashboard} />);

    expect(screen.getByText("Prometheus Metrics")).toBeInTheDocument();
    expect(
      screen.getByText("Real-time system and pipeline monitoring")
    ).toBeInTheDocument();
  });

  it("shows live indicator when data is present", () => {
    render(<MetricsDashboardPanel data={mockDashboard} />);

    expect(screen.getByText("Live")).toBeInTheDocument();
  });

  it("displays loading skeleton when loading", () => {
    const { container } = render(
      <MetricsDashboardPanel data={undefined} isLoading />
    );

    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("displays error message when error occurs", () => {
    const error = new Error("Failed to fetch metrics");
    render(<MetricsDashboardPanel data={undefined} error={error} />);

    expect(screen.getByText("Failed to load metrics")).toBeInTheDocument();
    expect(screen.getByText("Failed to fetch metrics")).toBeInTheDocument();
  });

  it("displays empty state when no data", () => {
    render(<MetricsDashboardPanel data={undefined} />);

    expect(screen.getByText("No metrics data available")).toBeInTheDocument();
  });

  it("renders tabs", () => {
    render(<MetricsDashboardPanel data={mockDashboard} />);

    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Resources")).toBeInTheDocument();
    expect(screen.getByText("Pipeline")).toBeInTheDocument();
    expect(screen.getByText("Custom Metrics")).toBeInTheDocument();
  });

  it("shows overview tab by default", () => {
    render(<MetricsDashboardPanel data={mockDashboard} />);

    // Overview should show quick stats - CPU and Memory appear in multiple places
    expect(screen.getAllByText(/45\.0%/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/60\.0%/).length).toBeGreaterThan(0);
  });

  it("switches to Resources tab when clicked", () => {
    render(<MetricsDashboardPanel data={mockDashboard} />);

    fireEvent.click(screen.getByText("Resources"));

    expect(screen.getByText("System Resources")).toBeInTheDocument();
  });

  it("switches to Pipeline tab when clicked", () => {
    render(<MetricsDashboardPanel data={mockDashboard} />);

    fireEvent.click(screen.getByText("Pipeline"));

    expect(screen.getByText("Pipeline Performance")).toBeInTheDocument();
  });

  it("displays last updated timestamp", () => {
    render(<MetricsDashboardPanel data={mockDashboard} />);

    // Should show formatted date
    expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <MetricsDashboardPanel data={mockDashboard} className="custom-class" />
    );

    expect(container.firstChild).toHaveClass("custom-class");
  });
});
