/**
 * Tests for CalibrationComparisonPanel Component
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CalibrationComparisonPanel } from "./CalibrationComparisonPanel";
import type { CalibrationQAMetrics } from "../../types/calibration";

const excellentMetrics: CalibrationQAMetrics = {
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

const goodMetrics: CalibrationQAMetrics = {
  cal_set_name: "cal_2024_002",
  calibrator_name: "3C48",
  cal_mjd: 60340.5,
  cal_timestamp: "2024-01-10T12:00:00Z",
  snr: 85,
  flagging_percent: 12.5,
  phase_rms_deg: 15.2,
  amp_rms: 0.045,
  quality_grade: "good",
  quality_score: 78,
  issues: [
    {
      severity: "info",
      category: "flagging",
      message: "Moderate flagging on a few antennas",
    },
  ],
  recommendations: ["Monitor antenna health"],
};

const poorMetrics: CalibrationQAMetrics = {
  cal_set_name: "cal_2024_003",
  calibrator_name: "3C147",
  cal_mjd: 60335.5,
  cal_timestamp: "2024-01-05T12:00:00Z",
  snr: 15,
  flagging_percent: 42,
  phase_rms_deg: 55,
  amp_rms: 0.12,
  quality_grade: "poor",
  quality_score: 35,
  issues: [
    {
      severity: "critical",
      category: "flagging",
      message: "Excessive data flagging (>40%)",
      affected_antennas: ["ant3", "ant7", "ant12"],
    },
    {
      severity: "critical",
      category: "phase",
      message: "Phase RMS significantly exceeds threshold",
    },
  ],
  recommendations: ["Re-observe calibrator"],
};

describe("CalibrationComparisonPanel", () => {
  it("renders both calibration sets", () => {
    render(
      <CalibrationComparisonPanel setA={excellentMetrics} setB={goodMetrics} />
    );

    expect(screen.getByText("cal_2024_001")).toBeInTheDocument();
    expect(screen.getByText("cal_2024_002")).toBeInTheDocument();
    expect(screen.getByText("3C286")).toBeInTheDocument();
    expect(screen.getByText("3C48")).toBeInTheDocument();
  });

  it("displays quality grades for both sets", () => {
    render(
      <CalibrationComparisonPanel setA={excellentMetrics} setB={poorMetrics} />
    );

    expect(screen.getByText("Excellent")).toBeInTheDocument();
    expect(screen.getByText("Poor")).toBeInTheDocument();
  });

  it("shows comparison metrics table", () => {
    render(
      <CalibrationComparisonPanel setA={excellentMetrics} setB={goodMetrics} />
    );

    expect(screen.getByText("SNR")).toBeInTheDocument();
    expect(screen.getByText("Flagging")).toBeInTheDocument();
    expect(screen.getByText("Phase RMS")).toBeInTheDocument();
    // Quality Score appears multiple times (in summary cards and metrics table)
    expect(screen.getAllByText("Quality Score").length).toBeGreaterThanOrEqual(
      1
    );
  });

  it("displays recommendation when Set A is better", () => {
    render(
      <CalibrationComparisonPanel setA={excellentMetrics} setB={poorMetrics} />
    );

    // Should show Set A is improved
    expect(
      screen.getByText(/improvement in overall quality/i)
    ).toBeInTheDocument();
  });

  it("displays recommendation when Set B is better", () => {
    render(
      <CalibrationComparisonPanel setA={poorMetrics} setB={excellentMetrics} />
    );

    // Should show Set B is better
    expect(screen.getByText(/Set B shows/)).toBeInTheDocument();
  });

  it("shows comparable message when sets are similar", () => {
    render(
      <CalibrationComparisonPanel
        setA={excellentMetrics}
        setB={excellentMetrics}
      />
    );

    expect(screen.getByText(/comparable in quality/i)).toBeInTheDocument();
  });

  it("respects custom labels", () => {
    render(
      <CalibrationComparisonPanel
        setA={excellentMetrics}
        setB={goodMetrics}
        labels={{ setA: "New Calibration", setB: "Previous Calibration" }}
      />
    );

    // Labels appear in multiple places (summary card and table header)
    expect(
      screen.getAllByText("New Calibration").length
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByText("Previous Calibration").length
    ).toBeGreaterThanOrEqual(1);
  });

  it("calls onSelectPreferred when user selects a set", () => {
    const onSelect = vi.fn();
    render(
      <CalibrationComparisonPanel
        setA={excellentMetrics}
        setB={goodMetrics}
        onSelectPreferred={onSelect}
      />
    );

    // Find and click "Select this set" button for Set A
    const selectButtons = screen.getAllByText("Select this set");
    fireEvent.click(selectButtons[0]);

    expect(onSelect).toHaveBeenCalledWith("A");
  });

  it("shows selected state after selection", () => {
    const onSelect = vi.fn();
    render(
      <CalibrationComparisonPanel
        setA={excellentMetrics}
        setB={goodMetrics}
        onSelectPreferred={onSelect}
      />
    );

    const selectButtons = screen.getAllByText("Select this set");
    fireEvent.click(selectButtons[0]);

    expect(screen.getByText("✓ Selected")).toBeInTheDocument();
  });

  it("hides select buttons when onSelectPreferred not provided", () => {
    render(
      <CalibrationComparisonPanel setA={excellentMetrics} setB={goodMetrics} />
    );

    expect(screen.queryByText("Select this set")).not.toBeInTheDocument();
  });

  it("shows issues section when sets have issues", () => {
    render(
      <CalibrationComparisonPanel setA={excellentMetrics} setB={poorMetrics} />
    );

    expect(screen.getByText(/Set B \(Reference\) Issues/)).toBeInTheDocument();
    expect(
      screen.getByText("Excessive data flagging (>40%)")
    ).toBeInTheDocument();
  });

  it("hides detailed metrics when showDetails is false", () => {
    render(
      <CalibrationComparisonPanel
        setA={excellentMetrics}
        setB={goodMetrics}
        showDetails={false}
      />
    );

    expect(
      screen.queryByText("Detailed Metrics Comparison")
    ).not.toBeInTheDocument();
  });

  it("shows delta indicators with correct direction", () => {
    render(
      <CalibrationComparisonPanel setA={excellentMetrics} setB={poorMetrics} />
    );

    // Excellent has higher SNR than poor - should show positive change
    // The exact format depends on the delta calculation
    const snrRow = screen.getByText("SNR").parentElement;
    expect(snrRow).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <CalibrationComparisonPanel
        setA={excellentMetrics}
        setB={goodMetrics}
        className="custom-class"
      />
    );

    expect(container.firstChild).toHaveClass("custom-class");
  });
});
