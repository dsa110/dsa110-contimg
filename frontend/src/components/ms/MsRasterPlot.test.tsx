import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MsRasterPlot from "./MsRasterPlot";

// Mock the config module
vi.mock("../../config", () => ({
  config: {
    api: {
      baseUrl: "/api",
    },
  },
}));

describe("MsRasterPlot", () => {
  const msPath = "/data/test.ms";
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
  });

  const renderComponent = (props = {}) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MsRasterPlot msPath={msPath} {...props} />
      </QueryClientProvider>
    );
  };

  it("renders loading state initially", () => {
    renderComponent();

    expect(screen.getByText(/generating plot/i)).toBeInTheDocument();
  });

  it("renders axis selectors", () => {
    renderComponent();

    expect(screen.getByLabelText(/x-axis/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/component/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/colormap/i)).toBeInTheDocument();
  });

  it("renders refresh button", () => {
    renderComponent();

    expect(screen.getByRole("button", { name: /refresh/i })).toBeInTheDocument();
  });

  it("builds correct image URL with default params", () => {
    renderComponent();

    const img = screen.getByRole("img");
    const src = img.getAttribute("src");

    expect(src).toContain("/api/ms/");
    expect(src).toContain("xaxis=time");
    expect(src).toContain("yaxis=amp");
    expect(src).toContain("colormap=viridis");
    expect(src).toContain("width=800");
    expect(src).toContain("height=600");
  });

  it("uses custom initial values", () => {
    renderComponent({
      initialXAxis: "frequency",
      initialYAxis: "phase",
      initialColormap: "plasma",
      width: 1000,
      height: 800,
    });

    const img = screen.getByRole("img");
    const src = img.getAttribute("src");

    expect(src).toContain("xaxis=frequency");
    expect(src).toContain("yaxis=phase");
    expect(src).toContain("colormap=plasma");
    expect(src).toContain("width=1000");
    expect(src).toContain("height=800");
  });

  it("updates URL when xaxis is changed", async () => {
    renderComponent();

    const xaxisSelect = screen.getByLabelText(/x-axis/i);
    fireEvent.change(xaxisSelect, { target: { value: "baseline" } });

    await waitFor(() => {
      const img = screen.getByRole("img");
      expect(img.getAttribute("src")).toContain("xaxis=baseline");
    });
  });

  it("updates URL when yaxis is changed", async () => {
    renderComponent();

    const yaxisSelect = screen.getByLabelText(/component/i);
    fireEvent.change(yaxisSelect, { target: { value: "phase" } });

    await waitFor(() => {
      const img = screen.getByRole("img");
      expect(img.getAttribute("src")).toContain("yaxis=phase");
    });
  });

  it("updates URL when colormap is changed", async () => {
    renderComponent();

    const colormapSelect = screen.getByLabelText(/colormap/i);
    fireEvent.change(colormapSelect, { target: { value: "plasma" } });

    await waitFor(() => {
      const img = screen.getByRole("img");
      expect(img.getAttribute("src")).toContain("colormap=plasma");
    });
  });

  it("shows loading state when refresh is clicked", async () => {
    renderComponent();

    // Simulate image load completion
    const img = screen.getByRole("img");
    fireEvent.load(img);

    // Click refresh
    const refreshButton = screen.getByRole("button", { name: /refresh/i });
    fireEvent.click(refreshButton);

    expect(screen.getByText(/generating plot/i)).toBeInTheDocument();
  });

  it("shows error state on image load failure", async () => {
    renderComponent();

    const img = screen.getByRole("img");
    fireEvent.error(img);

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });

  it("hides error and shows loading when retry is clicked after error", async () => {
    renderComponent();

    // Trigger error
    const img = screen.getByRole("img");
    fireEvent.error(img);

    await waitFor(() => {
      expect(screen.getByText(/try again/i)).toBeInTheDocument();
    });

    // Click retry
    fireEvent.click(screen.getByText(/try again/i));

    expect(screen.getByText(/generating plot/i)).toBeInTheDocument();
  });

  it("encodes MS path in URL", () => {
    renderComponent({ msPath: "/data/path with spaces/test.ms" });

    const img = screen.getByRole("img");
    const src = img.getAttribute("src");

    expect(src).toContain(encodeURIComponent("/data/path with spaces/test.ms"));
  });

  it("renders description text", () => {
    renderComponent();

    expect(screen.getByText(/amplitude/i)).toBeInTheDocument();
    expect(screen.getByText(/averaged over polarizations/i)).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = renderComponent({ className: "custom-class" });

    expect(container.firstChild).toHaveClass("custom-class");
  });

  it("has accessible select elements", () => {
    renderComponent();

    const xaxisSelect = screen.getByLabelText(/x-axis/i);
    const yaxisSelect = screen.getByLabelText(/component/i);
    const colormapSelect = screen.getByLabelText(/colormap/i);

    expect(xaxisSelect).toHaveAttribute("id", "xaxis-select");
    expect(yaxisSelect).toHaveAttribute("id", "yaxis-select");
    expect(colormapSelect).toHaveAttribute("id", "colormap-select");
  });

  it("disables refresh button while loading", () => {
    renderComponent();

    const refreshButton = screen.getByRole("button", { name: /refresh/i });
    expect(refreshButton).toBeDisabled();
  });

  it("enables refresh button after load", async () => {
    renderComponent();

    const img = screen.getByRole("img");
    fireEvent.load(img);

    await waitFor(() => {
      const refreshButton = screen.getByRole("button", { name: /refresh/i });
      expect(refreshButton).not.toBeDisabled();
    });
  });
});
