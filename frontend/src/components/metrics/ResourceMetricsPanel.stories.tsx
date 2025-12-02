/**
 * ResourceMetricsPanel Stories
 */

import type { Meta, StoryObj } from "@storybook/react";
import { ResourceMetricsPanel } from "./ResourceMetricsPanel";
import type { ResourceMetricsDetailed } from "../../types/prometheus";

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

const meta: Meta<typeof ResourceMetricsPanel> = {
  title: "Metrics/ResourceMetricsPanel",
  component: ResourceMetricsPanel,
  parameters: {
    layout: "padded",
  },
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof meta>;

const healthyResources: ResourceMetricsDetailed = {
  cpu: {
    id: "cpu",
    name: "CPU",
    description: "CPU usage",
    unit: "%",
    current: 35,
    trend: "stable",
    trendPercent: 2,
    status: "healthy",
    history: generateHistory(35, 15),
  },
  memory: {
    id: "memory",
    name: "Memory",
    description: "Memory usage",
    unit: "bytes",
    current: 8e9,
    total: 32e9,
    trend: "stable",
    trendPercent: 1,
    status: "healthy",
    history: generateHistory(8e9, 1e9),
  },
  diskIO: {
    id: "disk-io",
    name: "Disk I/O",
    description: "Disk throughput",
    unit: "bytes",
    current: 50e6,
    trend: "down",
    trendPercent: 5,
    status: "healthy",
    history: generateHistory(50e6, 20e6),
  },
  network: {
    id: "network",
    name: "Network I/O",
    description: "Network throughput",
    unit: "bytes",
    current: 25e6,
    trend: "stable",
    trendPercent: 3,
    status: "healthy",
    history: generateHistory(25e6, 10e6),
  },
};

export const Default: Story = {
  args: {
    metrics: healthyResources,
  },
};

export const HighCPU: Story = {
  args: {
    metrics: {
      ...healthyResources,
      cpu: {
        ...healthyResources.cpu,
        current: 92,
        status: "critical",
        trend: "up",
        trendPercent: 15,
        history: generateHistory(85, 10),
      },
    },
  },
};

export const HighMemory: Story = {
  args: {
    metrics: {
      ...healthyResources,
      memory: {
        ...healthyResources.memory,
        current: 28e9,
        status: "warning",
        trend: "up",
        trendPercent: 8,
        history: generateHistory(26e9, 2e9),
      },
    },
  },
};

export const HighDiskIO: Story = {
  args: {
    metrics: {
      ...healthyResources,
      diskIO: {
        ...healthyResources.diskIO,
        current: 500e6,
        status: "warning",
        history: generateHistory(450e6, 100e6),
      },
    },
  },
};

export const WithoutCharts: Story = {
  args: {
    metrics: healthyResources,
    showCharts: false,
  },
};

export const AllCritical: Story = {
  args: {
    metrics: {
      cpu: {
        ...healthyResources.cpu,
        current: 98,
        status: "critical",
        history: generateHistory(95, 5),
      },
      memory: {
        ...healthyResources.memory,
        current: 30e9,
        status: "critical",
        history: generateHistory(29e9, 1e9),
      },
      diskIO: {
        ...healthyResources.diskIO,
        current: 800e6,
        status: "critical",
        history: generateHistory(750e6, 100e6),
      },
      network: {
        ...healthyResources.network,
        current: 900e6,
        status: "critical",
        history: generateHistory(850e6, 100e6),
      },
    },
  },
};
