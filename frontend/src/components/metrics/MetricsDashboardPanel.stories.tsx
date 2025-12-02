/**
 * MetricsDashboardPanel Stories
 */

import type { Meta, StoryObj } from "@storybook/react";
import { MetricsDashboardPanel } from "./MetricsDashboardPanel";
import type { MetricsDashboard } from "../../types/prometheus";

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

const meta: Meta<typeof MetricsDashboardPanel> = {
  title: "Metrics/MetricsDashboardPanel",
  component: MetricsDashboardPanel,
  parameters: {
    layout: "padded",
  },
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof meta>;

const mockDashboard: MetricsDashboard = {
  resources: {
    cpu_percent: 42,
    memory_percent: 58,
    disk_io_mbps: 120,
    network_io_mbps: 45,
  },
  pipeline: {
    jobs_per_hour: 18.5,
    avg_job_duration_sec: 32,
    success_rate_percent: 98.7,
    queue_depth: 4,
    active_workers: 5,
    total_workers: 6,
  },
  metrics: [
    {
      id: "cpu",
      name: "CPU Usage",
      description: "Processor utilization",
      unit: "%",
      current: 42,
      trend: "stable",
      trendPercent: 3,
      status: "healthy",
      history: generateHistory(40, 15),
    },
    {
      id: "memory",
      name: "Memory Usage",
      description: "RAM utilization",
      unit: "%",
      current: 58,
      trend: "up",
      trendPercent: 5,
      status: "healthy",
      history: generateHistory(55, 10),
    },
    {
      id: "disk-io",
      name: "Disk I/O",
      description: "Disk throughput",
      unit: "bytes",
      current: 120e6,
      trend: "down",
      trendPercent: 8,
      status: "healthy",
      history: generateHistory(130e6, 30e6),
    },
    {
      id: "network",
      name: "Network I/O",
      description: "Network bandwidth",
      unit: "bytes",
      current: 45e6,
      trend: "stable",
      trendPercent: 2,
      status: "healthy",
      history: generateHistory(45e6, 15e6),
    },
    {
      id: "jobs-per-hour",
      name: "Jobs/Hour",
      description: "Pipeline throughput",
      unit: "",
      current: 18.5,
      trend: "up",
      trendPercent: 10,
      status: "healthy",
      history: generateHistory(15, 5),
    },
    {
      id: "success-rate",
      name: "Success Rate",
      description: "Job success percentage",
      unit: "%",
      current: 98.7,
      trend: "stable",
      trendPercent: 0.5,
      status: "healthy",
      history: generateHistory(98, 2),
    },
    {
      id: "queue-depth",
      name: "Queue Depth",
      description: "Jobs waiting",
      unit: "",
      current: 4,
      trend: "down",
      trendPercent: 20,
      status: "healthy",
      history: generateHistory(6, 4),
    },
    {
      id: "calibrator-flux",
      name: "Calibrator Flux",
      description: "Average calibrator flux density",
      unit: "Jy",
      current: 14.2,
      trend: "stable",
      trendPercent: 1,
      status: "healthy",
      history: generateHistory(14, 2),
    },
  ],
  updated_at: new Date().toISOString(),
};

export const Default: Story = {
  args: {
    data: mockDashboard,
  },
};

export const Loading: Story = {
  args: {
    data: undefined,
    isLoading: true,
  },
};

export const ErrorState: Story = {
  args: {
    data: undefined,
    error: new globalThis.Error(
      "Failed to connect to Prometheus server at localhost:9090"
    ),
  },
};

export const NoData: Story = {
  args: {
    data: undefined,
  },
};

export const HighLoad: Story = {
  args: {
    data: {
      ...mockDashboard,
      resources: {
        cpu_percent: 89,
        memory_percent: 92,
        disk_io_mbps: 450,
        network_io_mbps: 200,
      },
      pipeline: {
        jobs_per_hour: 45,
        avg_job_duration_sec: 180,
        success_rate_percent: 94.2,
        queue_depth: 78,
        active_workers: 6,
        total_workers: 6,
      },
      metrics: mockDashboard.metrics.map((m) => ({
        ...m,
        status: m.id === "cpu" || m.id === "memory" ? "warning" : m.status,
      })),
    },
  },
};

export const CriticalState: Story = {
  args: {
    data: {
      ...mockDashboard,
      resources: {
        cpu_percent: 98,
        memory_percent: 97,
        disk_io_mbps: 800,
        network_io_mbps: 950,
      },
      pipeline: {
        jobs_per_hour: 2,
        avg_job_duration_sec: 600,
        success_rate_percent: 72.5,
        queue_depth: 245,
        active_workers: 2,
        total_workers: 6,
      },
      metrics: mockDashboard.metrics.map((m) => ({
        ...m,
        status: "critical" as const,
      })),
    },
  },
};
