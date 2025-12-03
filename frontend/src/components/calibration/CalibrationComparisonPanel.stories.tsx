/**
 * Storybook stories for CalibrationComparisonPanel
 */

import type { Meta, StoryObj } from "@storybook/react";
import { CalibrationComparisonPanel } from "./CalibrationComparisonPanel";
import type { CalibrationQAMetrics } from "../../types/calibration";

const excellentMetrics: CalibrationQAMetrics = {
  cal_set_name: "cal_2024_jan_15_3c286",
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
  cal_set_name: "cal_2024_jan_10_3c48",
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
  recommendations: ["Monitor antenna health during next observation"],
};

const poorMetrics: CalibrationQAMetrics = {
  cal_set_name: "cal_2024_jan_05_3c147",
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
  ],
};

const acceptableMetrics: CalibrationQAMetrics = {
  cal_set_name: "cal_2024_jan_08_3c286",
  calibrator_name: "3C286",
  cal_mjd: 60338.5,
  cal_timestamp: "2024-01-08T12:00:00Z",
  snr: 55,
  flagging_percent: 22,
  phase_rms_deg: 25,
  amp_rms: 0.065,
  quality_grade: "acceptable",
  quality_score: 60,
  issues: [
    {
      severity: "warning",
      category: "flagging",
      message: "Elevated flagging levels",
    },
    {
      severity: "warning",
      category: "phase",
      message: "Phase RMS near threshold",
    },
  ],
  recommendations: ["Consider re-observation during better conditions"],
};

const meta: Meta<typeof CalibrationComparisonPanel> = {
  title: "Calibration/CalibrationComparisonPanel",
  component: CalibrationComparisonPanel,
  parameters: {
    layout: "padded",
    docs: {
      description: {
        component: `
The CalibrationComparisonPanel allows astronomers to compare two calibration sets
side-by-side. It shows:

- Summary cards for each calibration set with key metrics
- A recommendation banner indicating which set is preferred
- Detailed metrics comparison table with delta indicators
- Issues section for each set

This is useful for:
- Comparing new vs. reference calibrations
- Evaluating different calibrator sources
- Quality assurance before applying calibration
        `,
      },
    },
  },
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof CalibrationComparisonPanel>;

export const ExcellentVsGood: Story = {
  name: "Excellent vs Good",
  args: {
    setA: excellentMetrics,
    setB: goodMetrics,
    labels: {
      setA: "New Calibration",
      setB: "Previous Calibration",
    },
  },
  parameters: {
    docs: {
      description: {
        story:
          "Comparing an excellent calibration against a good one. Clear improvement visible.",
      },
    },
  },
};

export const GoodVsPoor: Story = {
  name: "Good vs Poor",
  args: {
    setA: goodMetrics,
    setB: poorMetrics,
    labels: {
      setA: "Current",
      setB: "Problematic",
    },
  },
  parameters: {
    docs: {
      description: {
        story:
          "Comparing a good calibration against a poor one with multiple issues.",
      },
    },
  },
};

export const PoorVsExcellent: Story = {
  name: "Poor vs Excellent (B is Better)",
  args: {
    setA: poorMetrics,
    setB: excellentMetrics,
    labels: {
      setA: "Today's Calibration",
      setB: "Reference Standard",
    },
  },
  parameters: {
    docs: {
      description: {
        story:
          "When Set B is significantly better, the recommendation reflects this.",
      },
    },
  },
};

export const SimilarQuality: Story = {
  name: "Similar Quality",
  args: {
    setA: { ...goodMetrics, quality_score: 79 },
    setB: { ...goodMetrics, cal_set_name: "cal_2024_002_alt" },
  },
  parameters: {
    docs: {
      description: {
        story:
          "When both calibrations are very similar, shows 'comparable' message.",
      },
    },
  },
};

export const WithSelection: Story = {
  name: "With Selection Capability",
  args: {
    setA: excellentMetrics,
    setB: acceptableMetrics,
    onSelectPreferred: (selected) => console.log(`Selected: ${selected}`),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Shows selection buttons when onSelectPreferred callback is provided.",
      },
    },
  },
};

export const MinimalDetails: Story = {
  name: "Without Detailed Metrics",
  args: {
    setA: excellentMetrics,
    setB: goodMetrics,
    showDetails: false,
  },
  parameters: {
    docs: {
      description: {
        story: "Compact view without the detailed metrics comparison table.",
      },
    },
  },
};

export const BothHaveIssues: Story = {
  name: "Both Sets Have Issues",
  args: {
    setA: acceptableMetrics,
    setB: poorMetrics,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Both calibration sets have issues, showing side-by-side issue lists.",
      },
    },
  },
};

export const SameCalibrator: Story = {
  name: "Same Calibrator Different Times",
  args: {
    setA: excellentMetrics,
    setB: {
      ...excellentMetrics,
      cal_set_name: "cal_2024_jan_01_3c286",
      cal_mjd: 60330.5,
      cal_timestamp: "2024-01-01T12:00:00Z",
      snr: 120,
      flagging_percent: 8.5,
      phase_rms_deg: 12.0,
      quality_score: 88,
      quality_grade: "good",
    },
    labels: {
      setA: "Jan 15 (Latest)",
      setB: "Jan 1 (Earlier)",
    },
  },
  parameters: {
    docs: {
      description: {
        story:
          "Comparing the same calibrator source observed at different times.",
      },
    },
  },
};
