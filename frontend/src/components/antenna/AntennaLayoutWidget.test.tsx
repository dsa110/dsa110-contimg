import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AntennaLayoutWidget, {
  AntennaInfo,
  AntennaLayoutResponse,
} from "./AntennaLayoutWidget";

// Create a properly typed mock function
const mockGet = vi.fn();

// Mock the API client
vi.mock("../../api/client", () => ({
  default: {
    get: mockGet,
  },
}));

describe("AntennaLayoutWidget", () => {
  const msPath = "/data/test.ms";
  let queryClient: QueryClient;

  const mockAntennaData: AntennaLayoutResponse = {
    antennas: [
      {
        id: 0,
        name: "DSA-001",
        x_m: 0,
        y_m: 0,
        flagged_pct: 5.0,
        baseline_count: 109,
      },
      {
        id: 1,
        name: "DSA-002",
        x_m: 100,
        y_m: 0,
        flagged_pct: 25.0,
        baseline_count: 109,
      },
      {
        id: 2,
        name: "DSA-003",
        x_m: 0,
        y_m: 50,
        flagged_pct: 60.0,
        baseline_count: 109,
      },
    ],
    array_center_lon: -118.2817,
    array_center_lat: 37.2339,
    total_baselines: 3,
  };

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.clearAllMocks();
  });

  const renderComponent = (props = {}) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <AntennaLayoutWidget msPath={msPath} {...props} />
      </QueryClientProvider>
    );
  };

  it("renders loading state initially", () => {
    mockGet.mockImplementation(() => new Promise(() => {})); // Never resolves
    renderComponent();

    expect(screen.getByText(/loading antenna positions/i)).toBeInTheDocument();
  });

  it("renders antenna positions after loading", async () => {
    mockGet.mockResolvedValue({ data: mockAntennaData });
    renderComponent();

    await waitFor(() => {
      // Check for SVG element
      expect(screen.getByRole("img", { hidden: true })).toBeInTheDocument();
    });
  });

  it("renders correct number of antenna markers", async () => {
    mockGet.mockResolvedValue({ data: mockAntennaData });
    const { container } = renderComponent();

    await waitFor(() => {
      const circles = container.querySelectorAll("circle");
      expect(circles.length).toBe(3);
    });
  });

  it("shows legend when showLegend is true", async () => {
    mockGet.mockResolvedValue({ data: mockAntennaData });
    renderComponent({ showLegend: true });

    await waitFor(() => {
      expect(screen.getByText(/flagging status/i)).toBeInTheDocument();
      expect(screen.getByText(/good/i)).toBeInTheDocument();
      expect(screen.getByText(/moderate/i)).toBeInTheDocument();
      expect(screen.getByText(/severe/i)).toBeInTheDocument();
    });
  });

  it("hides legend when showLegend is false", async () => {
    mockGet.mockResolvedValue({ data: mockAntennaData });
    renderComponent({ showLegend: false });

    await waitFor(() => {
      expect(screen.queryByText(/flagging status/i)).not.toBeInTheDocument();
    });
  });

  it("displays summary statistics", async () => {
    mockGet.mockResolvedValue({ data: mockAntennaData });
    renderComponent({ showLegend: true });

    await waitFor(() => {
      expect(screen.getByText(/antennas/i)).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument(); // antenna count and baselines
    });
  });

  it("renders error state on API failure", async () => {
    mockGet.mockRejectedValue(new Error("API Error"));
    renderComponent();

    await waitFor(() => {
      expect(
        screen.getByText(/failed to load antenna data/i)
      ).toBeInTheDocument();
    });
  });

  it("renders empty state when no antennas", async () => {
    mockGet.mockResolvedValue({
      data: { ...mockAntennaData, antennas: [] },
    });
    renderComponent();

    await waitFor(() => {
      expect(
        screen.getByText(/no antenna data available/i)
      ).toBeInTheDocument();
    });
  });

  it("calls onAntennaClick when antenna is clicked", async () => {
    mockGet.mockResolvedValue({ data: mockAntennaData });
    const onAntennaClick = vi.fn();
    const { container } = renderComponent({ onAntennaClick });

    await waitFor(() => {
      const circles = container.querySelectorAll("circle");
      expect(circles.length).toBeGreaterThan(0);
    });

    // Click the first antenna marker
    const circles = container.querySelectorAll("circle");
    fireEvent.click(circles[0]);

    expect(onAntennaClick).toHaveBeenCalledWith(mockAntennaData.antennas[0]);
  });

  it("applies custom className", async () => {
    mockGet.mockResolvedValue({ data: mockAntennaData });
    const { container } = renderComponent({ className: "custom-class" });

    await waitFor(() => {
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  it("respects custom height prop", async () => {
    mockGet.mockResolvedValue({ data: mockAntennaData });
    const { container } = renderComponent({ height: 500 });

    await waitFor(() => {
      const svg = container.querySelector("svg");
      expect(svg).toHaveAttribute("height", "500");
    });
  });

  it("encodes MS path in API request", async () => {
    const pathWithSpaces = "/data/path with spaces/test.ms";
    mockGet.mockResolvedValue({ data: mockAntennaData });

    render(
      <QueryClientProvider client={queryClient}>
        <AntennaLayoutWidget msPath={pathWithSpaces} />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(
        expect.stringContaining(encodeURIComponent(pathWithSpaces))
      );
    });
  });

  it("shows antenna names for small arrays", async () => {
    // With only 3 antennas (< 30), names should be shown
    mockGet.mockResolvedValue({ data: mockAntennaData });
    const { container } = renderComponent();

    await waitFor(() => {
      // Look for text elements with antenna numbers (names without DSA- prefix)
      const textElements = container.querySelectorAll("text");
      const hasAntennaLabel = Array.from(textElements).some(
        (el) => el.textContent === "001" || el.textContent === "002"
      );
      expect(hasAntennaLabel).toBe(true);
    });
  });

  it("renders axis labels", async () => {
    mockGet.mockResolvedValue({ data: mockAntennaData });
    const { container } = renderComponent();

    await waitFor(() => {
      const textElements = container.querySelectorAll("text");
      const hasEastLabel = Array.from(textElements).some((el) =>
        el.textContent?.includes("East")
      );
      const hasNorthLabel = Array.from(textElements).some((el) =>
        el.textContent?.includes("North")
      );
      expect(hasEastLabel).toBe(true);
      expect(hasNorthLabel).toBe(true);
    });
  });

  it("calculates correct flagging counts", async () => {
    mockGet.mockResolvedValue({ data: mockAntennaData });
    renderComponent({ showLegend: true });

    await waitFor(() => {
      // From mock data: 1 good (<20%), 1 moderate (25%), 1 severe (60%)
      // Find the "Good" count
      const goodLabel = screen.getByText("1", {
        selector: "dd.text-green-600",
      });
      expect(goodLabel).toBeInTheDocument();

      // Find the "Flagged" count (severe)
      const flaggedLabel = screen.getByText("1", {
        selector: "dd.text-red-600",
      });
      expect(flaggedLabel).toBeInTheDocument();
    });
  });
});

describe("useAntennaPositions hook", () => {
  it("is disabled when msPath is undefined", async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });

    // The hook should not make an API call when path is undefined
    mockGet.mockResolvedValue({ data: {} });

    render(
      <QueryClientProvider client={queryClient}>
        <AntennaLayoutWidget msPath={undefined as unknown as string} />
      </QueryClientProvider>
    );

    // Wait a bit to ensure no API call is made
    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(mockGet).not.toHaveBeenCalled();
  });
});
