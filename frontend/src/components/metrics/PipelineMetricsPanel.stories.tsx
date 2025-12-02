/**
 * PipelineMetricsPanel Stories
 */

import type { Meta, StoryObj } from "@storybook/react";
import { PipelineMetricsPanel } from "./PipelineMetricsPanel";
import type { PipelineMetrics } from "../../types/prometheus";

const meta: Meta<typeof PipelineMetricsPanel> = {
  title: "Metrics/PipelineMetricsPanel",
  component: PipelineMetricsPanel,
  parameters: {
    layout: "padded",
  },
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof meta>;

const healthyMetrics: PipelineMetrics = {
  jobs_per_hour: 15.5,
  avg_job_duration_sec: 28,
  success_rate_percent: 99.2,
  queue_depth: 3,
  active_workers: 5,
  total_workers: 6,
};

export const Default: Story = {
  args: {
    metrics: healthyMetrics,
  },
};

export const HighLoad: Story = {
  args: {
    metrics: {
      jobs_per_hour: 45.2,
      avg_job_duration_sec: 120,
      success_rate_percent: 95.5,
      queue_depth: 85,
      active_workers: 6,
      total_workers: 6,
    },
  },
};

export const LowSuccessRate: Story = {
  args: {
    metrics: {
      ...healthyMetrics,
      success_rate_percent: 87.3,
    },
  },
};

export const QueueBacklog: Story = {
  args: {
    metrics: {
      ...healthyMetrics,
      queue_depth: 150,
    },
  },
};

export const LowWorkerCapacity: Story = {
  args: {
    metrics: {
      ...healthyMetrics,
      active_workers: 2,
      total_workers: 8,
    },
  },
};

export const IdlePipeline: Story = {
  args: {
    metrics: {
      jobs_per_hour: 0.5,
      avg_job_duration_sec: 15,
      success_rate_percent: 100,
      queue_depth: 0,
      active_workers: 1,
      total_workers: 6,
    },
  },
};

export const WithoutCharts: Story = {
  args: {
    metrics: healthyMetrics,
    showCharts: false,
  },
};
