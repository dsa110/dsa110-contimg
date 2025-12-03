import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CalibrationQAMetricsPanel } from "./CalibrationQAMetricsPanel";
import type { CalibrationQAMetrics } from "../../types/calibration";

const mockMetrics: CalibrationQAMetrics = {
  cal_set_name: "cal_2024_001",
  calibrator_name: "3C286",
  cal_mjd: 60345.5,
  cal_timestamp: "2024-01-15T12:00:00Z",
  snr: 150,
  flagging_percent: 5.2,
  phase_rms_deg: 8.5,
  amp_rms: 0.02,
  quality_grade: "excellent",
  quality_score: 95,
  issues: [],
  recommendations: [],
};

const mockMetricsWithIssues: CalibrationQAMetrics = {
  ...mockMetrics,
  snr: 12,
  flagging_percent: 35,
  phase_rms_deg: 45,
  quality_grade: "poor",
  quality_score: 45,
  issues: [
    {
      severity: "critical",
      category: "flagging",
      message: "High flagging percentage detected",
      affected_antennas: ["ant1", "ant5", "ant12"],
    },
    {
      severity: "warning",
      category: "phase",
      message: "Phase RMS exceeds recommended threshold",
    },
  ],
  recommendations: [
    "Consider re-observing calibrator",
    "Check antenna flagging status",
  ],
};

describe("CalibrationQAMetricsPanel", () => {
  it("renders calibrator name and timestamp", () => {
    render(<CalibrationQAMetricsPanel metrics={mockMetrics} />);

    // Use regex for partial match since calibrator and timestamp are in same element
    expect(screen.getByText(/3C286/)).toBeInTheDocument();
    expect(screen.getByText(/2024/)).toBeInTheDocument();
  });

  it("renders quality grade badge", () => {
    render(<CalibrationQAMetricsPanel metrics={mockMetrics} />);

    expect(screen.getByText("Excellent")).toBeInTheDocument();
    expect(screen.getByText("Score: 95/100")).toBeInTheDocument();
  });

  it("renders metric values", () => {
    render(<CalibrationQAMetricsPanel metrics={mockMetrics} />);

    expect(screen.getByText("SNR")).toBeInTheDocument();
    expect(screen.getByText("Flagging")).toBeInTheDocument();
    expect(screen.getByText("Phase RMS")).toBeInTheDocument();
    expect(screen.getByText("Amp RMS")).toBeInTheDocument();
  });

  it("renders issues when present", () => {
    render(<CalibrationQAMetricsPanel metrics={mockMetricsWithIssues} />);

    expect(screen.getByText("Issues Detected")).toBeInTheDocument();
    expect(
      screen.getByText("High flagging percentage detected")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Phase RMS exceeds recommended threshold/)
    ).toBeInTheDocument();
  });

  it("renders recommendations when present", () => {
    render(<CalibrationQAMetricsPanel metrics={mockMetricsWithIssues} />);

    expect(screen.getByText("Recommendations")).toBeInTheDocument();
    expect(
      screen.getByText("Consider re-observing calibrator")
    ).toBeInTheDocument();
  });

  it("hides details when showDetails is false", () => {
    render(
      <CalibrationQAMetricsPanel
        metrics={mockMetricsWithIssues}
        showDetails={false}
      />
    );

    expect(screen.queryByText("Issues Detected")).not.toBeInTheDocument();
    expect(screen.queryByText("Recommendations")).not.toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <CalibrationQAMetricsPanel
        metrics={mockMetrics}
        className="custom-class"
      />
    );

    expect(container.firstChild).toHaveClass("custom-class");
  });
});
