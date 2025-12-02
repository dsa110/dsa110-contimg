import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DiskUsagePanel } from "./DiskUsagePanel";
import type { DiskPartition, StorageAlert } from "../../types/storage";

const mockPartitions: DiskPartition[] = [
  {
    mount_point: "/data",
    device: "/dev/sda1",
    filesystem: "ext4",
    total_bytes: 1000000000000,
    used_bytes: 750000000000,
    free_bytes: 250000000000,
    usage_percent: 75,
    total_formatted: "1.00 TB",
    used_formatted: "750.00 GB",
    free_formatted: "250.00 GB",
  },
  {
    mount_point: "/scratch",
    device: "/dev/sdb1",
    filesystem: "xfs",
    total_bytes: 500000000000,
    used_bytes: 450000000000,
    free_bytes: 50000000000,
    usage_percent: 90,
    total_formatted: "500.00 GB",
    used_formatted: "450.00 GB",
    free_formatted: "50.00 GB",
  },
];

const mockAlerts: StorageAlert[] = [
  {
    severity: "critical",
    message: "/scratch is above 90% capacity",
    path: "/scratch",
    threshold_percent: 90,
    current_percent: 90,
  },
];

describe("DiskUsagePanel", () => {
  it("renders partition information", () => {
    render(<DiskUsagePanel partitions={mockPartitions} />);

    expect(screen.getByText("/data")).toBeInTheDocument();
    expect(screen.getByText("/scratch")).toBeInTheDocument();
    expect(screen.getByText("75.0%")).toBeInTheDocument();
    expect(screen.getByText("90.0%")).toBeInTheDocument();
  });

  it("renders disk size details", () => {
    render(<DiskUsagePanel partitions={mockPartitions} />);

    expect(screen.getByText("Used: 750.00 GB")).toBeInTheDocument();
    expect(screen.getByText("Free: 250.00 GB")).toBeInTheDocument();
    expect(screen.getByText("Total: 1.00 TB")).toBeInTheDocument();
  });

  it("renders device and filesystem info", () => {
    render(<DiskUsagePanel partitions={mockPartitions} />);

    expect(screen.getByText("/dev/sda1 • ext4")).toBeInTheDocument();
    expect(screen.getByText("/dev/sdb1 • xfs")).toBeInTheDocument();
  });

  it("renders critical alerts", () => {
    render(<DiskUsagePanel partitions={mockPartitions} alerts={mockAlerts} />);

    expect(
      screen.getByText("/scratch is above 90% capacity")
    ).toBeInTheDocument();
  });

  it("shows empty message when no partitions", () => {
    render(<DiskUsagePanel partitions={[]} />);

    expect(
      screen.getByText("No disk information available")
    ).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <DiskUsagePanel partitions={mockPartitions} className="custom-class" />
    );

    expect(container.firstChild).toHaveClass("custom-class");
  });
});
