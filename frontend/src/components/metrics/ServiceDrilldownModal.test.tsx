/**
 * ServiceDrilldownModal Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ServiceDrilldownModal } from "./ServiceDrilldownModal";
import type { ServiceMetricsData } from "./ServiceDrilldownModal";

const mockData: ServiceMetricsData = {
  service: "api-server",
  pod: "api-server-pod-1",
  metrics: [
    {
      id: "cpu",
      name: "CPU Usage",
      description: "CPU utilization",
      unit: "%",
      current: 65.5,
      trend: "up",
      trendPercent: 5.2,
      status: "healthy",
      history: [
        { timestamp: 1700000000, value: 60 },
        { timestamp: 1700000060, value: 62 },
        { timestamp: 1700000120, value: 65.5 },
      ],
    },
    {
      id: "memory",
      name: "Memory Usage",
      description: "Memory utilization",
      unit: "bytes",
      current: 8e9,
      trend: "stable",
      trendPercent: 0.5,
      status: "healthy",
      history: [
        { timestamp: 1700000000, value: 7.8e9 },
        { timestamp: 1700000060, value: 7.9e9 },
        { timestamp: 1700000120, value: 8e9 },
      ],
    },
  ],
  lastUpdated: "2024-01-01T12:00:00Z",
};

// Mock URL methods
const mockCreateObjectURL = vi.fn(() => "blob:mock-url");
const mockRevokeObjectURL = vi.fn();

describe("ServiceDrilldownModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.URL.createObjectURL = mockCreateObjectURL;
    global.URL.revokeObjectURL = mockRevokeObjectURL;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not render when closed", () => {
    const { container } = render(
      <ServiceDrilldownModal isOpen={false} onClose={() => {}} data={mockData} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders when open", async () => {
    render(
      <ServiceDrilldownModal isOpen={true} onClose={() => {}} data={mockData} />
    );
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });

  it("displays service name in title", async () => {
    render(
      <ServiceDrilldownModal isOpen={true} onClose={() => {}} data={mockData} />
    );
    await waitFor(() => {
      expect(screen.getByText("api-server Metrics")).toBeInTheDocument();
    });
  });

  it("displays pod name when provided", async () => {
    render(
      <ServiceDrilldownModal isOpen={true} onClose={() => {}} data={mockData} />
    );
    await waitFor(() => {
      expect(screen.getByText("Pod: api-server-pod-1")).toBeInTheDocument();
    });
  });

  it("displays empty state when no data", async () => {
    render(
      <ServiceDrilldownModal isOpen={true} onClose={() => {}} data={null} />
    );
    await waitFor(() => {
      expect(screen.getByText("No metrics data available")).toBeInTheDocument();
    });
  });

  it("renders export buttons", async () => {
    render(
      <ServiceDrilldownModal isOpen={true} onClose={() => {}} data={mockData} />
    );
    await waitFor(() => {
      expect(screen.getByTitle("Export as CSV")).toBeInTheDocument();
      expect(screen.getByTitle("Export as PNG")).toBeInTheDocument();
    });
  });

  it("renders time range buttons", async () => {
    render(
      <ServiceDrilldownModal isOpen={true} onClose={() => {}} data={mockData} />
    );
    await waitFor(() => {
      expect(screen.getByText("1h")).toBeInTheDocument();
      expect(screen.getByText("6h")).toBeInTheDocument();
      expect(screen.getByText("24h")).toBeInTheDocument();
    });
  });

  it("calls onClose when close button clicked", async () => {
    const onClose = vi.fn();
    render(
      <ServiceDrilldownModal isOpen={true} onClose={onClose} data={mockData} />
    );
    await waitFor(() => {
      expect(screen.getByLabelText("Close modal")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByLabelText("Close modal"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("has proper dialog accessibility attributes", async () => {
    render(
      <ServiceDrilldownModal isOpen={true} onClose={() => {}} data={mockData} />
    );
    await waitFor(() => {
      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });
  });

  it("displays formatted percentage values", async () => {
    render(
      <ServiceDrilldownModal isOpen={true} onClose={() => {}} data={mockData} />
    );
    await waitFor(() => {
      expect(screen.getByText("65.50%")).toBeInTheDocument();
    });
  });

  it("displays formatted bytes values", async () => {
    render(
      <ServiceDrilldownModal isOpen={true} onClose={() => {}} data={mockData} />
    );
    await waitFor(() => {
      expect(screen.getByText("8.00 GB")).toBeInTheDocument();
    });
  });

  it("defaults to 1h time range", async () => {
    render(
      <ServiceDrilldownModal isOpen={true} onClose={() => {}} data={mockData} />
    );
    await waitFor(() => {
      const button1h = screen.getByText("1h");
      expect(button1h).toHaveClass("bg-blue-500");
    });
  });

  it("changes time range when clicked", async () => {
    render(
      <ServiceDrilldownModal isOpen={true} onClose={() => {}} data={mockData} />
    );
    await waitFor(() => {
      expect(screen.getByText("6h")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("6h"));
    await waitFor(() => {
      expect(screen.getByText("6h")).toHaveClass("bg-blue-500");
    });
  });
});
