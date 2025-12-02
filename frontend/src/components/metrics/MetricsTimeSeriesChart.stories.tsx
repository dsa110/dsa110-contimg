/**
 * MetricsTimeSeriesChart Stories
 */

import type { Meta, StoryObj } from "@storybook/react";
import { MetricsTimeSeriesChart } from "./MetricsTimeSeriesChart";
import type { SystemMetric } from "../../types/prometheus";

// Generate mock history data
function generateHistory(
  baseValue: number,
  variance: number,
  points: number = 24
): { timestamp: number; value: number }[] {
  const now = Math.floor(Date.now() / 1000);
  return Array.from({ length: points }, (_, i) => ({
    timestamp: now - (points - i - 1) * 3600,
    value: baseValue + (Math.random() - 0.5) * variance,
  }));
}

const meta: Meta<typeof MetricsTimeSeriesChart> = {
  title: "Metrics/MetricsTimeSeriesChart",
  component: MetricsTimeSeriesChart,
  parameters: {
    layout: "centered",
  },
  tags: ["autodocs"],
  decorators: [
    (Story) => (
      <div style={{ width: "400px" }}>
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof meta>;

const cpuMetric: SystemMetric = {
  id: "cpu",
  name: "CPU Usage",
  description: "Processor utilization over time",
  unit: "%",
  current: 45.5,
  trend: "up",
  trendPercent: 5.2,
  status: "healthy",
  history: generateHistory(45, 20),
};

export const Default: Story = {
  args: {
    metric: cpuMetric,
  },
};

export const WarningStatus: Story = {
  args: {
    metric: {
      ...cpuMetric,
      current: 78.5,
      status: "warning",
      history: generateHistory(75, 10),
    },
  },
};

export const CriticalStatus: Story = {
  args: {
    metric: {
      ...cpuMetric,
      current: 95.2,
      status: "critical",
      history: generateHistory(92, 5),
    },
  },
};

export const MemoryBytes: Story = {
  args: {
    metric: {
      id: "memory",
      name: "Memory Usage",
      description: "RAM consumption in bytes",
      unit: "bytes",
      current: 8.5e9,
      trend: "stable",
      trendPercent: 0.5,
      status: "healthy",
      history: generateHistory(8e9, 1e9),
    },
  },
};

export const DownwardTrend: Story = {
  args: {
    metric: {
      ...cpuMetric,
      trend: "down",
      trendPercent: 12.3,
      history: [...generateHistory(60, 10, 12), ...generateHistory(40, 10, 12)],
    },
  },
};

export const StableTrend: Story = {
  args: {
    metric: {
      ...cpuMetric,
      trend: "stable",
      trendPercent: 0.1,
    },
  },
};

export const WithoutLegend: Story = {
  args: {
    metric: cpuMetric,
    showLegend: false,
  },
};

export const CustomHeight: Story = {
  args: {
    metric: cpuMetric,
    height: 200,
  },
};

export const InsufficientData: Story = {
  args: {
    metric: {
      ...cpuMetric,
      history: [],
    },
  },
};

export const LatencyMetric: Story = {
  args: {
    metric: {
      id: "latency",
      name: "API Latency",
      description: "Average response time",
      unit: "ms",
      current: 125,
      trend: "up",
      trendPercent: 15,
      status: "warning",
      history: generateHistory(100, 50),
    },
  },
};
