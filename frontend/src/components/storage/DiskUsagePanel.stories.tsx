import type { Meta, StoryObj } from "@storybook/react-vite";
import { DiskUsagePanel } from "./DiskUsagePanel";
import type { DiskPartition, StorageAlert } from "../../types/storage";

const meta: Meta<typeof DiskUsagePanel> = {
  title: "Storage/DiskUsagePanel",
  component: DiskUsagePanel,
  parameters: {
    layout: "padded",
  },
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof DiskUsagePanel>;

const healthyPartitions: DiskPartition[] = [
  {
    mount_point: "/data",
    device: "/dev/sda1",
    filesystem: "ext4",
    total_bytes: 2000000000000,
    used_bytes: 800000000000,
    free_bytes: 1200000000000,
    usage_percent: 40,
    total_formatted: "2.00 TB",
    used_formatted: "800.00 GB",
    free_formatted: "1.20 TB",
  },
  {
    mount_point: "/scratch",
    device: "/dev/sdb1",
    filesystem: "xfs",
    total_bytes: 1000000000000,
    used_bytes: 500000000000,
    free_bytes: 500000000000,
    usage_percent: 50,
    total_formatted: "1.00 TB",
    used_formatted: "500.00 GB",
    free_formatted: "500.00 GB",
  },
];

const warningPartitions: DiskPartition[] = [
  {
    mount_point: "/data",
    device: "/dev/sda1",
    filesystem: "ext4",
    total_bytes: 2000000000000,
    used_bytes: 1600000000000,
    free_bytes: 400000000000,
    usage_percent: 80,
    total_formatted: "2.00 TB",
    used_formatted: "1.60 TB",
    free_formatted: "400.00 GB",
  },
];

const criticalPartitions: DiskPartition[] = [
  {
    mount_point: "/data",
    device: "/dev/sda1",
    filesystem: "ext4",
    total_bytes: 2000000000000,
    used_bytes: 1900000000000,
    free_bytes: 100000000000,
    usage_percent: 95,
    total_formatted: "2.00 TB",
    used_formatted: "1.90 TB",
    free_formatted: "100.00 GB",
  },
];

const alerts: StorageAlert[] = [
  {
    severity: "critical",
    message: "/data is above 90% capacity - immediate action required",
    path: "/data",
    threshold_percent: 90,
    current_percent: 95,
  },
  {
    severity: "warning",
    message: "/scratch is approaching capacity threshold",
    path: "/scratch",
    threshold_percent: 80,
    current_percent: 82,
  },
];

export const Healthy: Story = {
  args: {
    partitions: healthyPartitions,
  },
};

export const Warning: Story = {
  args: {
    partitions: warningPartitions,
  },
};

export const Critical: Story = {
  args: {
    partitions: criticalPartitions,
    alerts: [alerts[0]],
  },
};

export const WithAlerts: Story = {
  args: {
    partitions: healthyPartitions,
    alerts: alerts,
  },
};

export const Empty: Story = {
  args: {
    partitions: [],
  },
};
