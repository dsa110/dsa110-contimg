/**
 * PipelineMetricsPanel Tests
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PipelineMetricsPanel } from "./PipelineMetricsPanel";
import type { PipelineMetrics } from "../../types/prometheus";

const mockPipelineMetrics: PipelineMetrics = {
  jobs_per_hour: 12.5,
  avg_job_duration_sec: 45,
  success_rate_percent: 98.5,
  queue_depth: 5,
  active_workers: 4,
  total_workers: 6,
};

describe("PipelineMetricsPanel", () => {
  it("renders panel header", () => {
    render(<PipelineMetricsPanel metrics={mockPipelineMetrics} />);

    expect(screen.getByText("Pipeline Performance")).toBeInTheDocument();
    expect(
      screen.getByText("Job processing and queue metrics")
    ).toBeInTheDocument();
  });

  it("displays jobs per hour", () => {
    render(<PipelineMetricsPanel metrics={mockPipelineMetrics} />);

    expect(screen.getByText("Jobs/Hour")).toBeInTheDocument();
    expect(screen.getByText("12.5")).toBeInTheDocument();
  });

  it("displays average job duration", () => {
    render(<PipelineMetricsPanel metrics={mockPipelineMetrics} />);

    expect(screen.getByText("Avg duration: 45s")).toBeInTheDocument();
  });

  it("displays success rate", () => {
    render(<PipelineMetricsPanel metrics={mockPipelineMetrics} />);

    expect(screen.getByText("Success Rate")).toBeInTheDocument();
    expect(screen.getByText("98.5%")).toBeInTheDocument();
  });

  it("displays queue depth", () => {
    render(<PipelineMetricsPanel metrics={mockPipelineMetrics} />);

    expect(screen.getByText("Queue Depth")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("displays worker status", () => {
    render(<PipelineMetricsPanel metrics={mockPipelineMetrics} />);

    expect(screen.getByText("Active Workers")).toBeInTheDocument();
    expect(screen.getByText("4/6")).toBeInTheDocument();
    expect(screen.getByText("67% capacity")).toBeInTheDocument();
  });

  it("handles low success rate with warning styling", () => {
    const lowSuccessMetrics = {
      ...mockPipelineMetrics,
      success_rate_percent: 92,
    };
    render(<PipelineMetricsPanel metrics={lowSuccessMetrics} />);

    // Just verify it renders without errors
    expect(screen.getByText("92.0%")).toBeInTheDocument();
  });

  it("handles high queue depth", () => {
    const highQueueMetrics = { ...mockPipelineMetrics, queue_depth: 150 };
    render(<PipelineMetricsPanel metrics={highQueueMetrics} />);

    expect(screen.getByText("150")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <PipelineMetricsPanel
        metrics={mockPipelineMetrics}
        className="custom-class"
      />
    );

    expect(container.firstChild).toHaveClass("custom-class");
  });
});
