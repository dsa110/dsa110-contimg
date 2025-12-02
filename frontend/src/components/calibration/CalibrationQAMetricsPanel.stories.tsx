import type { Meta, StoryObj } from "@storybook/react-vite";
import { CalibrationQAMetricsPanel } from "./CalibrationQAMetricsPanel";
import type { CalibrationQAMetrics } from "../../types/calibration";

const meta: Meta<typeof CalibrationQAMetricsPanel> = {
  title: "Calibration/CalibrationQAMetricsPanel",
  component: CalibrationQAMetricsPanel,
  parameters: {
    layout: "padded",
  },
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof CalibrationQAMetricsPanel>;

const excellentMetrics: CalibrationQAMetrics = {
  cal_set_name: "cal_2024_001",
  calibrator_name: "3C286",
  cal_mjd: 60345.5,
  cal_timestamp: "2024-01-15T12:00:00Z",
  snr: 180,
  flagging_percent: 3.2,
  phase_rms_deg: 5.5,
  amp_rms: 0.015,
  quality_grade: "excellent",
  quality_score: 98,
  issues: [],
  recommendations: [],
};

const goodMetrics: CalibrationQAMetrics = {
  cal_set_name: "cal_2024_002",
  calibrator_name: "3C48",
  cal_mjd: 60346.5,
  cal_timestamp: "2024-01-16T12:00:00Z",
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
  recommendations: ["Monitor antenna health during next observation"],
};

const poorMetrics: CalibrationQAMetrics = {
  cal_set_name: "cal_2024_003",
  calibrator_name: "3C147",
  cal_mjd: 60347.5,
  cal_timestamp: "2024-01-17T12:00:00Z",
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
      affected_antennas: ["ant3", "ant7", "ant12", "ant15"],
    },
    {
      severity: "critical",
      category: "phase",
      message: "Phase RMS significantly exceeds threshold",
    },
    {
      severity: "warning",
      category: "snr",
      message: "Low signal-to-noise ratio",
    },
  ],
  recommendations: [
    "Re-observe calibrator if possible",
    "Check antenna pointing and focus",
    "Review RFI environment",
    "Consider manual flagging before re-calibration",
  ],
};

export const Excellent: Story = {
  args: {
    metrics: excellentMetrics,
  },
};

export const Good: Story = {
  args: {
    metrics: goodMetrics,
  },
};

export const Poor: Story = {
  args: {
    metrics: poorMetrics,
  },
};

export const CompactView: Story = {
  args: {
    metrics: poorMetrics,
    showDetails: false,
  },
};
