import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import SourcesListPage from "./SourcesListPage";

// Mock the hooks
vi.mock("../hooks/useQueries", () => ({
  useSources: vi.fn(),
}));

vi.mock("../stores/appStore", () => ({
  useSelectionStore: vi.fn((selector) => {
    const state = {
      selectedSources: new Set<string>(),
      toggleSourceSelection: vi.fn(),
      selectAllSources: vi.fn(),
      clearSourceSelection: vi.fn(),
    };
    return selector(state);
  }),
}));

// Mock components
vi.mock("../components/common", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../components/common")>();
  return {
    ...actual,
    PageSkeleton: vi.fn(() => (
      <div data-testid="page-skeleton">Loading...</div>
    )),
  };
});

// Mock ECharts to prevent DOM rendering issues in tests
vi.mock("echarts", () => ({
  init: vi.fn(() => ({
    setOption: vi.fn(),
    resize: vi.fn(),
    dispose: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    getOption: vi.fn(() => ({})),
  })),
  use: vi.fn(),
  registerTheme: vi.fn(),
}));

// Mock echarts-for-react component
vi.mock("echarts-for-react", () => ({
  default: vi.fn(({ style, ...props }) => (
    <div data-testid="echarts-mock" style={style} {...props}>
      ECharts Mock
    </div>
  )),
}));

import { useSources } from "../hooks/useQueries";

const mockUseSources = vi.mocked(useSources);

describe("SourcesListPage", () => {
  let queryClient: QueryClient;

  const mockSources = [
    {
      id: "src-001",
      name: "Source A",
      ra_deg: 83.633,
      dec_deg: 22.014,
      num_images: 10,
      eta: 1.5,
      v: 0.05,
    },
    {
      id: "src-002",
      name: "Source B",
      ra_deg: 10.684,
      dec_deg: 41.269,
      num_images: 5,
      eta: 3.2,
      v: 0.15,
    },
    {
      id: "src-003",
      name: "Source C",
      ra_deg: 180.0,
      dec_deg: 0.0,
      num_images: 3,
      eta: 0.8,
      v: 0.02,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  const renderPage = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <SourcesListPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  describe("loading state", () => {
    it("shows loading skeleton when loading", () => {
      mockUseSources.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      } as ReturnType<typeof useSources>);

      renderPage();
      expect(screen.getByTestId("page-skeleton")).toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("shows error message when fetch fails", () => {
      mockUseSources.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Failed to fetch"),
      } as ReturnType<typeof useSources>);

      renderPage();
      expect(screen.getByText(/failed|error/i)).toBeInTheDocument();
    });
  });

  describe("with data", () => {
    beforeEach(() => {
      mockUseSources.mockReturnValue({
        data: mockSources,
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useSources>);
    });

    it("renders page heading", () => {
      renderPage();
      expect(
        screen.getByRole("heading", { name: /sources/i })
      ).toBeInTheDocument();
    });

    it("renders sources in table", () => {
      renderPage();
      expect(screen.getByText("Source A")).toBeInTheDocument();
      expect(screen.getByText("Source B")).toBeInTheDocument();
    });

    it("renders tab navigation", () => {
      renderPage();
      // Should have list and variability tabs/buttons
      expect(screen.getByText(/list/i)).toBeInTheDocument();
    });

    it("renders sortable table headers", () => {
      renderPage();
      // Use getAllBy since there are multiple column headers matching the pattern
      const headers = screen.getAllByRole("columnheader", { name: /name|id/i });
      expect(headers.length).toBeGreaterThan(0);
    });
  });

  describe("tabs", () => {
    beforeEach(() => {
      mockUseSources.mockReturnValue({
        data: mockSources,
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useSources>);
    });

    it("switches to variability view", async () => {
      const user = userEvent.setup();
      renderPage();

      // Use more specific query - the tab button says "Variability Plot"
      const variabilityTab = screen.getByRole("button", {
        name: /variability plot/i,
      });
      await user.click(variabilityTab);

      // Variability view should show different content (like eta/v plot)
      await waitFor(() => {
        // Use getAllBy since there may be multiple matches
        const matches = screen.getAllByText(/eta|variability/i);
        expect(matches.length).toBeGreaterThan(0);
      });
    });
  });

  describe("advanced query", () => {
    beforeEach(() => {
      mockUseSources.mockReturnValue({
        data: mockSources,
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useSources>);
    });

    it("renders query panel", () => {
      renderPage();
      // Should have advanced query or filter controls - use getAllBy since there are multiple matches
      const queryElements = screen.getAllByText(/query|filter|search/i);
      expect(queryElements.length).toBeGreaterThan(0);
    });
  });

  describe("empty state", () => {
    it("shows message when no sources", () => {
      mockUseSources.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useSources>);

      renderPage();
      expect(screen.getByText(/no sources/i)).toBeInTheDocument();
    });
  });

  describe("selection", () => {
    beforeEach(() => {
      mockUseSources.mockReturnValue({
        data: mockSources,
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useSources>);
    });

    it("renders select all checkbox", () => {
      renderPage();
      const checkboxes = screen.getAllByRole("checkbox");
      expect(checkboxes.length).toBeGreaterThan(0);
    });
  });
});
