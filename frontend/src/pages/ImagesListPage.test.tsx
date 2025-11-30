import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ImagesListPage from "./ImagesListPage";

// Mock the hooks
vi.mock("../hooks/useQueries", () => ({
  useImages: vi.fn(),
}));

vi.mock("../stores/appStore", () => ({
  useSelectionStore: vi.fn((selector) => {
    const state = {
      selectedImages: new Set<string>(),
      toggleImageSelection: vi.fn(),
      selectAllImages: vi.fn(),
      clearImageSelection: vi.fn(),
    };
    return selector(state);
  }),
}));

import { useImages } from "../hooks/useQueries";

const mockUseImages = vi.mocked(useImages);

describe("ImagesListPage", () => {
  let queryClient: QueryClient;

  const mockImages = [
    {
      id: "img-001",
      path: "/data/test1.fits",
      qa_grade: "good",
      created_at: "2024-01-15T10:00:00Z",
    },
    {
      id: "img-002",
      path: "/data/test2.fits",
      qa_grade: "warn",
      created_at: "2024-01-14T08:00:00Z",
    },
    {
      id: "img-003",
      path: "/data/test3.fits",
      qa_grade: "fail",
      created_at: "2024-01-13T16:00:00Z",
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
          <ImagesListPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  describe("loading state", () => {
    it("shows loading spinner when loading", () => {
      mockUseImages.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      } as ReturnType<typeof useImages>);

      renderPage();
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("shows error message when fetch fails", () => {
      mockUseImages.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Failed to fetch"),
      } as ReturnType<typeof useImages>);

      renderPage();
      expect(screen.getByText(/failed to load images/i)).toBeInTheDocument();
    });
  });

  describe("with data", () => {
    beforeEach(() => {
      mockUseImages.mockReturnValue({
        data: mockImages,
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useImages>);
    });

    it("renders page heading", () => {
      renderPage();
      expect(screen.getByRole("heading", { name: /images/i })).toBeInTheDocument();
    });

    it("renders images in table", () => {
      renderPage();
      expect(screen.getByText("img-001")).toBeInTheDocument();
      expect(screen.getByText("img-002")).toBeInTheDocument();
      expect(screen.getByText("img-003")).toBeInTheDocument();
    });

    it("renders QA grade filter", () => {
      renderPage();
      expect(screen.getByText(/qa grade/i)).toBeInTheDocument();
    });

    it("renders sortable table headers", () => {
      renderPage();
      // Table should have sortable columns
      expect(screen.getByRole("columnheader", { name: /id/i })).toBeInTheDocument();
    });
  });

  describe("filtering", () => {
    beforeEach(() => {
      mockUseImages.mockReturnValue({
        data: mockImages,
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useImages>);
    });

    it("filters by QA grade", async () => {
      const user = userEvent.setup();
      renderPage();

      // Find and use the QA grade filter
      const select = screen.getAllByRole("combobox")[0];
      await user.selectOptions(select, "good");

      // Only good images should show
      await waitFor(() => {
        expect(screen.getByText("img-001")).toBeInTheDocument();
        expect(screen.queryByText("img-002")).not.toBeInTheDocument();
      });
    });
  });

  describe("empty state", () => {
    it("shows message when no images", () => {
      mockUseImages.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useImages>);

      renderPage();
      expect(screen.getByText(/no images/i)).toBeInTheDocument();
    });
  });

  describe("selection", () => {
    beforeEach(() => {
      mockUseImages.mockReturnValue({
        data: mockImages,
        isLoading: false,
        error: null,
      } as unknown as ReturnType<typeof useImages>);
    });

    it("renders select all checkbox", () => {
      renderPage();
      const checkboxes = screen.getAllByRole("checkbox");
      expect(checkboxes.length).toBeGreaterThan(0);
    });
  });
});
