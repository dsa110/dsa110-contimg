/**
 * Tests for SavedQueriesPanel component
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SavedQueriesPanel } from "./SavedQueriesPanel";
import type { SavedQuery } from "../../api/savedQueries";

// Mock saved queries data
const mockQueries: SavedQuery[] = [
  {
    id: "query-1",
    name: "Bright Sources",
    description: "Sources with flux > 1 Jy",
    visibility: "private",
    context: "sources",
    filters: { minFlux: 1 },
    owner_id: "user-1",
    owner_username: "alice",
    use_count: 5,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-15T00:00:00Z",
    can_edit: true,
  },
  {
    id: "query-2",
    name: "M31 Region",
    description: "Sources near M31",
    visibility: "shared",
    context: "sources",
    filters: { ra: 10.68, dec: 41.27, radius: 2 },
    owner_id: "user-2",
    owner_username: "bob",
    use_count: 12,
    created_at: "2025-01-05T00:00:00Z",
    updated_at: "2025-01-10T00:00:00Z",
    can_edit: false,
  },
];

// Mock hooks
const mockDeleteMutate = vi.fn();
const mockRecordUsageMutate = vi.fn();

vi.mock("../../api/savedQueries", async () => {
  const actual = await vi.importActual("../../api/savedQueries");
  return {
    ...actual,
    useSavedQueries: vi.fn(() => ({
      data: {
        queries: mockQueries,
        pagination: { page: 1, per_page: 20, total: 2, total_pages: 1 },
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })),
    useDeleteSavedQuery: () => ({
      mutateAsync: mockDeleteMutate,
      isPending: false,
    }),
    useRecordQueryUsage: () => ({
      mutate: mockRecordUsageMutate,
    }),
  };
});

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("SavedQueriesPanel", () => {
  const onApply = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders query list", () => {
    render(<SavedQueriesPanel onApply={onApply} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Bright Sources")).toBeInTheDocument();
    expect(screen.getByText("M31 Region")).toBeInTheDocument();
  });

  it("displays filter summaries", () => {
    render(<SavedQueriesPanel onApply={onApply} />, {
      wrapper: createWrapper(),
    });

    // Check for flux filter in first query
    expect(screen.getByText(/Flux:/)).toBeInTheDocument();
    // Check for cone search in second query
    expect(screen.getByText(/Cone:/)).toBeInTheDocument();
  });

  it("displays visibility icons", () => {
    render(<SavedQueriesPanel onApply={onApply} />, {
      wrapper: createWrapper(),
    });

    // Private icon
    expect(screen.getByText("🔒")).toBeInTheDocument();
    // Shared icon
    expect(screen.getByText("👥")).toBeInTheDocument();
  });

  it("shows owner and use count", () => {
    render(<SavedQueriesPanel onApply={onApply} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText(/by alice/)).toBeInTheDocument();
    expect(screen.getByText(/Used 5 times/)).toBeInTheDocument();
    expect(screen.getByText(/by bob/)).toBeInTheDocument();
    expect(screen.getByText(/Used 12 times/)).toBeInTheDocument();
  });

  it("calls onApply with filters when Apply button is clicked", async () => {
    const user = userEvent.setup();
    render(<SavedQueriesPanel onApply={onApply} />, {
      wrapper: createWrapper(),
    });

    // Click first "Apply Filters" button
    const applyButtons = screen.getAllByRole("button", {
      name: /apply filters/i,
    });
    await user.click(applyButtons[0]);

    expect(mockRecordUsageMutate).toHaveBeenCalledWith("query-1");
    expect(onApply).toHaveBeenCalledWith({ minFlux: 1 });
  });

  it("calls onEdit when edit button is clicked for owned queries", async () => {
    const onEdit = vi.fn();
    const user = userEvent.setup();
    render(<SavedQueriesPanel onApply={onApply} onEdit={onEdit} />, {
      wrapper: createWrapper(),
    });

    // Find and click the first edit button (first query is editable)
    const editButtons = screen.getAllByTitle("Edit query");
    expect(editButtons.length).toBeGreaterThan(0);
    await user.click(editButtons[0]);

    expect(onEdit).toHaveBeenCalledWith(mockQueries[0]);
  });

  it("shows delete button only for editable queries", () => {
    render(<SavedQueriesPanel onApply={onApply} />, {
      wrapper: createWrapper(),
    });

    // First query is editable, second is not
    const deleteButtons = screen.getAllByTitle("Delete query");
    expect(deleteButtons).toHaveLength(1);
  });

  it("confirms before deleting", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<SavedQueriesPanel onApply={onApply} />, {
      wrapper: createWrapper(),
    });

    const deleteButton = screen.getByTitle("Delete query");
    await user.click(deleteButton);

    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining("Bright Sources")
    );
    expect(mockDeleteMutate).not.toHaveBeenCalled();

    confirmSpy.mockRestore();
  });

  it("deletes query when confirmed", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    mockDeleteMutate.mockResolvedValue(undefined);

    render(<SavedQueriesPanel onApply={onApply} />, {
      wrapper: createWrapper(),
    });

    const deleteButton = screen.getByTitle("Delete query");
    await user.click(deleteButton);

    await waitFor(() => {
      expect(mockDeleteMutate).toHaveBeenCalledWith("query-1");
    });

    confirmSpy.mockRestore();
  });

  it("renders search input", () => {
    render(<SavedQueriesPanel onApply={onApply} />, {
      wrapper: createWrapper(),
    });

    expect(
      screen.getByPlaceholderText(/search saved queries/i)
    ).toBeInTheDocument();
  });

  it("renders filter buttons", () => {
    render(<SavedQueriesPanel onApply={onApply} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mine" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Others" })).toBeInTheDocument();
  });

  it("renders compact mode with simplified UI", async () => {
    const user = userEvent.setup();
    render(<SavedQueriesPanel onApply={onApply} compact />, {
      wrapper: createWrapper(),
    });

    // In compact mode, query names are clickable buttons
    const queryButton = screen.getByRole("button", {
      name: /bright sources/i,
    });
    await user.click(queryButton);

    expect(onApply).toHaveBeenCalledWith({ minFlux: 1 });
  });

  it("shows copy link button", async () => {
    const user = userEvent.setup();

    // Mock clipboard
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      writable: true,
    });

    render(<SavedQueriesPanel onApply={onApply} />, {
      wrapper: createWrapper(),
    });

    const copyButtons = screen.getAllByTitle("Copy shareable link");
    expect(copyButtons).toHaveLength(2);

    await user.click(copyButtons[0]);

    expect(writeText).toHaveBeenCalledWith(
      expect.stringContaining("savedQuery=query-1")
    );
  });
});

describe("SavedQueriesPanel loading state", () => {
  it("shows loading skeleton", async () => {
    // Override mock for this test
    const { useSavedQueries } = await import("../../api/savedQueries");
    (useSavedQueries as ReturnType<typeof vi.fn>).mockReturnValueOnce({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    render(<SavedQueriesPanel onApply={vi.fn()} />, {
      wrapper: createWrapper(),
    });

    // Check for loading skeleton animation class
    const container = document.querySelector(".animate-pulse");
    expect(container).toBeInTheDocument();
  });
});

describe("SavedQueriesPanel error state", () => {
  it("shows error message", async () => {
    // Override mock for this test
    const { useSavedQueries } = await import("../../api/savedQueries");
    (useSavedQueries as ReturnType<typeof vi.fn>).mockReturnValueOnce({
      data: undefined,
      isLoading: false,
      error: new Error("Network error"),
      refetch: vi.fn(),
    });

    render(<SavedQueriesPanel onApply={vi.fn()} />, {
      wrapper: createWrapper(),
    });

    expect(
      screen.getByText(/failed to load saved queries/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });
});

describe("SavedQueriesPanel empty state", () => {
  it("shows empty message when no queries exist", async () => {
    // Override mock for this test
    const { useSavedQueries } = await import("../../api/savedQueries");
    (useSavedQueries as ReturnType<typeof vi.fn>).mockReturnValueOnce({
      data: {
        queries: [],
        pagination: { page: 1, per_page: 20, total: 0, total_pages: 0 },
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<SavedQueriesPanel onApply={vi.fn()} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText(/no saved queries yet/i)).toBeInTheDocument();
  });
});
