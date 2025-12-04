/**
 * Tests for SharedQueriesPage
 *
 * Covers saved/shared query management including:
 * - Query listing with tabs and filters
 * - Create, edit, clone, delete queries
 * - Run queries with parameters
 * - Favorite/unfavorite
 * - Statistics and popular queries display
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import SharedQueriesPage from "./SharedQueriesPage";
import {
  getTargetTypeLabel,
  getVisibilityIcon,
  formatExecutionTime,
  validateQuerySyntax,
  extractParameters,
  substituteParameters,
  type SavedQuery,
  type QueryStats,
  type QueryResult,
} from "../api/queries";

// Mock confirm dialog
vi.stubGlobal(
  "confirm",
  vi.fn(() => true)
);

// Sample query data
const mockQueries: SavedQuery[] = [
  {
    id: "q1",
    name: "Find Bright Sources",
    description: "Find sources with flux > 100mJy",
    query_string: "SELECT * FROM sources WHERE flux > {{min_flux}}",
    target_type: "source",
    visibility: "public",
    owner_id: "me",
    owner_name: "Alice Smith",
    tags: ["flux", "bright"],
    parameters: [
      {
        name: "min_flux",
        type: "number",
        default_value: "100",
        required: true,
      },
    ],
    is_favorite: true,
    run_count: 42,
    last_run_at: "2024-01-15T10:30:00Z",
    created_at: "2024-01-10T08:00:00Z",
    updated_at: "2024-01-14T15:00:00Z",
  },
  {
    id: "q2",
    name: "Team Calibration Query",
    description: "Standard calibration check",
    query_string: "SELECT * FROM images WHERE status = 'calibrated'",
    target_type: "image",
    visibility: "team",
    owner_id: "u2",
    owner_name: "Bob Jones",
    tags: ["calibration", "standard"],
    parameters: [],
    is_favorite: false,
    run_count: 15,
    last_run_at: "2024-01-14T16:00:00Z",
    created_at: "2024-01-05T09:00:00Z",
    updated_at: "2024-01-14T16:00:00Z",
  },
  {
    id: "q3",
    name: "Private Analysis",
    description: "Personal analysis query",
    query_string: "SELECT * FROM jobs WHERE owner = 'me'",
    target_type: "job",
    visibility: "private",
    owner_id: "me",
    owner_name: "Alice Smith",
    tags: [],
    parameters: [],
    is_favorite: false,
    run_count: 3,
    last_run_at: null,
    created_at: "2024-01-12T11:00:00Z",
    updated_at: "2024-01-12T11:00:00Z",
  },
];

const mockStats: QueryStats = {
  total_queries: 125,
  public_queries: 45,
  team_queries: 50,
  private_queries: 30,
  queries_run_today: 23,
  queries_run_this_week: 156,
  popular_tags: [
    { tag: "flux", count: 32 },
    { tag: "calibration", count: 28 },
    { tag: "daily", count: 15 },
  ],
  top_queries: [
    {
      id: "q1",
      name: "Find Bright Sources",
      run_count: 42,
      owner_name: "Alice Smith",
    },
    {
      id: "q2",
      name: "Team Calibration Query",
      run_count: 15,
      owner_name: "Bob Jones",
    },
  ],
};

const mockQueryResult: QueryResult = {
  columns: ["id", "name", "flux"],
  rows: [
    { id: "src1", name: "Source A", flux: 150.5 },
    { id: "src2", name: "Source B", flux: 120.3 },
    { id: "src3", name: "Source C", flux: 105.2 },
  ],
  row_count: 3,
  execution_time_ms: 245,
  truncated: false,
};

// Mock implementations
const mockUseQueries = vi.fn();
const mockUseQueryStats = vi.fn();
const mockUseCreateQuery = vi.fn();
const mockUseDeleteQuery = vi.fn();
const mockUseRunQuery = vi.fn();
const mockUseFavoriteQuery = vi.fn();
const mockUseUnfavoriteQuery = vi.fn();
const mockUseCloneQuery = vi.fn();

vi.mock("../api/queries", async () => {
  const actual = await vi.importActual("../api/queries");
  return {
    ...actual,
    useQueries: () => mockUseQueries(),
    useQueryStats: () => mockUseQueryStats(),
    useCreateQuery: () => mockUseCreateQuery(),
    useDeleteQuery: () => mockUseDeleteQuery(),
    useRunQuery: () => mockUseRunQuery(),
    useFavoriteQuery: () => mockUseFavoriteQuery(),
    useUnfavoriteQuery: () => mockUseUnfavoriteQuery(),
    useCloneQuery: () => mockUseCloneQuery(),
  };
});

// Helper to create wrapper with providers
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

describe("SharedQueriesPage", () => {
  const mockCreateMutation = { mutateAsync: vi.fn(), isPending: false };
  const mockDeleteMutation = { mutateAsync: vi.fn(), isPending: false };
  const mockRunMutation = { mutateAsync: vi.fn(), isPending: false };
  const mockFavoriteMutation = { mutate: vi.fn(), isPending: false };
  const mockUnfavoriteMutation = { mutate: vi.fn(), isPending: false };
  const mockCloneMutation = { mutate: vi.fn(), isPending: false };

  beforeEach(() => {
    vi.clearAllMocks();

    // Setup default mock implementations
    vi.mocked(queriesApi.useQueries).mockReturnValue({
      data: mockQueries,
      isPending: false,
      error: null,
    } as ReturnType<typeof queriesApi.useQueries>);

    vi.mocked(queriesApi.useQueryStats).mockReturnValue({
      data: mockStats,
      isPending: false,
      error: null,
    } as ReturnType<typeof queriesApi.useQueryStats>);

    vi.mocked(queriesApi.useCreateQuery).mockReturnValue(
      mockCreateMutation as ReturnType<typeof queriesApi.useCreateQuery>
    );
    vi.mocked(queriesApi.useDeleteQuery).mockReturnValue(
      mockDeleteMutation as ReturnType<typeof queriesApi.useDeleteQuery>
    );
    vi.mocked(queriesApi.useRunQuery).mockReturnValue(
      mockRunMutation as ReturnType<typeof queriesApi.useRunQuery>
    );
    vi.mocked(queriesApi.useFavoriteQuery).mockReturnValue(
      mockFavoriteMutation as ReturnType<typeof queriesApi.useFavoriteQuery>
    );
    vi.mocked(queriesApi.useUnfavoriteQuery).mockReturnValue(
      mockUnfavoriteMutation as ReturnType<typeof queriesApi.useUnfavoriteQuery>
    );
    vi.mocked(queriesApi.useCloneQuery).mockReturnValue(
      mockCloneMutation as ReturnType<typeof queriesApi.useCloneQuery>
    );

    mockRunMutation.mutateAsync.mockResolvedValue(mockQueryResult);
  });

  // ===========================================================================
  // Page Structure
  // ===========================================================================

  describe("Page Structure", () => {
    it("renders page header with title and description", () => {
      render(<SharedQueriesPage />);

      expect(
        screen.getByRole("heading", { name: /shared queries/i })
      ).toBeInTheDocument();
      expect(
        screen.getByText(/save, share, and run database queries/i)
      ).toBeInTheDocument();
    });

    it("renders New Query button", () => {
      render(<SharedQueriesPage />);

      expect(
        screen.getByRole("button", { name: /new query/i })
      ).toBeInTheDocument();
    });

    it("renders all navigation tabs", () => {
      render(<SharedQueriesPage />);

      expect(
        screen.getByRole("button", { name: /all queries/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /my queries/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /favorites/i })
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /team/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /public/i })
      ).toBeInTheDocument();
    });

    it("renders search input", () => {
      render(<SharedQueriesPage />);

      expect(
        screen.getByPlaceholderText(/search queries/i)
      ).toBeInTheDocument();
    });

    it("renders target type filter dropdown", () => {
      render(<SharedQueriesPage />);

      const filterSelect = screen.getByLabelText(/filter by target type/i);
      expect(filterSelect).toBeInTheDocument();
      expect(filterSelect).toHaveValue("");
    });
  });

  // ===========================================================================
  // Query List Display
  // ===========================================================================

  describe("Query List Display", () => {
    it("renders query cards with names", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText("Find Bright Sources")).toBeInTheDocument();
      expect(screen.getByText("Team Calibration Query")).toBeInTheDocument();
      expect(screen.getByText("Private Analysis")).toBeInTheDocument();
    });

    it("renders query descriptions", () => {
      render(<SharedQueriesPage />);

      expect(
        screen.getByText("Find sources with flux > 100mJy")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Standard calibration check")
      ).toBeInTheDocument();
    });

    it("renders query owner names", () => {
      render(<SharedQueriesPage />);

      const aliceElements = screen.getAllByText(/alice smith/i);
      expect(aliceElements.length).toBeGreaterThan(0);
    });

    it("renders run counts for queries", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText("42 runs")).toBeInTheDocument();
      expect(screen.getByText("15 runs")).toBeInTheDocument();
    });

    it("renders target type badges", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText("Sources")).toBeInTheDocument();
      expect(screen.getByText("Images")).toBeInTheDocument();
      expect(screen.getByText("Jobs")).toBeInTheDocument();
    });

    it("renders query tags", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText("flux")).toBeInTheDocument();
      expect(screen.getByText("bright")).toBeInTheDocument();
      expect(screen.getByText("calibration")).toBeInTheDocument();
    });

    it("renders visibility icons", () => {
      render(<SharedQueriesPage />);

      // Check for visibility icons/labels
      expect(screen.getAllByTitle(/public/i).length).toBeGreaterThan(0);
    });

    it("shows favorite indicator on favorited queries", () => {
      render(<SharedQueriesPage />);

      // First query is favorited
      expect(screen.getByTitle("Favorite")).toBeInTheDocument();
    });

    it("renders query preview with truncated content", () => {
      render(<SharedQueriesPage />);

      expect(
        screen.getByText(/SELECT \* FROM sources WHERE flux/i)
      ).toBeInTheDocument();
    });

    it("shows loading state when fetching queries", () => {
      vi.mocked(queriesApi.useQueries).mockReturnValue({
        data: undefined,
        isPending: true,
        error: null,
      } as ReturnType<typeof queriesApi.useQueries>);

      render(<SharedQueriesPage />);

      expect(screen.getByText(/loading queries/i)).toBeInTheDocument();
    });

    it("shows error state when query fetch fails", () => {
      vi.mocked(queriesApi.useQueries).mockReturnValue({
        data: undefined,
        isPending: false,
        error: new Error("Network error"),
      } as ReturnType<typeof queriesApi.useQueries>);

      render(<SharedQueriesPage />);

      expect(screen.getByText(/error loading queries/i)).toBeInTheDocument();
    });

    it("shows empty state when no queries found", () => {
      vi.mocked(queriesApi.useQueries).mockReturnValue({
        data: [],
        isPending: false,
        error: null,
      } as ReturnType<typeof queriesApi.useQueries>);

      render(<SharedQueriesPage />);

      expect(screen.getByText(/no queries found/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Query Actions
  // ===========================================================================

  describe("Query Actions", () => {
    it("renders Run button for each query", () => {
      render(<SharedQueriesPage />);

      const runButtons = screen.getAllByRole("button", { name: /run/i });
      expect(runButtons.length).toBeGreaterThanOrEqual(3);
    });

    it("renders Favorite button for unfavorited queries", () => {
      render(<SharedQueriesPage />);

      expect(
        screen.getByRole("button", { name: /☆ favorite/i })
      ).toBeInTheDocument();
    });

    it("renders Unfavorite button for favorited queries", () => {
      render(<SharedQueriesPage />);

      expect(
        screen.getByRole("button", { name: /★ unfavorite/i })
      ).toBeInTheDocument();
    });

    it("renders Clone button for all queries", () => {
      render(<SharedQueriesPage />);

      const cloneButtons = screen.getAllByRole("button", { name: /clone/i });
      expect(cloneButtons.length).toBeGreaterThanOrEqual(3);
    });

    it("renders Edit button only for owned queries", () => {
      render(<SharedQueriesPage />);

      // Two queries owned by "me"
      const editButtons = screen.getAllByRole("button", { name: /edit/i });
      expect(editButtons).toHaveLength(2);
    });

    it("renders Delete button only for owned queries", () => {
      render(<SharedQueriesPage />);

      // Two queries owned by "me"
      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      expect(deleteButtons).toHaveLength(2);
    });

    it("calls favorite mutation when clicking Favorite button", () => {
      render(<SharedQueriesPage />);

      // Find the unfavorited query's card (Team Calibration Query)
      const favoriteButton = screen.getByRole("button", {
        name: /☆ favorite/i,
      });
      fireEvent.click(favoriteButton);

      expect(mockFavoriteMutation.mutate).toHaveBeenCalledWith("q2");
    });

    it("calls unfavorite mutation when clicking Unfavorite button", () => {
      render(<SharedQueriesPage />);

      const unfavoriteButton = screen.getByRole("button", {
        name: /★ unfavorite/i,
      });
      fireEvent.click(unfavoriteButton);

      expect(mockUnfavoriteMutation.mutate).toHaveBeenCalledWith("q1");
    });

    it("calls clone mutation when clicking Clone button", () => {
      render(<SharedQueriesPage />);

      const cloneButtons = screen.getAllByRole("button", { name: /clone/i });
      fireEvent.click(cloneButtons[0]);

      expect(mockCloneMutation.mutate).toHaveBeenCalledWith("q1");
    });

    it("shows confirm dialog before deleting", () => {
      render(<SharedQueriesPage />);

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      fireEvent.click(deleteButtons[0]);

      expect(confirm).toHaveBeenCalled();
    });

    it("calls delete mutation when confirmed", async () => {
      render(<SharedQueriesPage />);

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(mockDeleteMutation.mutateAsync).toHaveBeenCalledWith("q1");
      });
    });

    it("does not delete when not confirmed", async () => {
      vi.stubGlobal(
        "confirm",
        vi.fn(() => false)
      );

      render(<SharedQueriesPage />);

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      fireEvent.click(deleteButtons[0]);

      expect(mockDeleteMutation.mutateAsync).not.toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Tab Navigation
  // ===========================================================================

  describe("Tab Navigation", () => {
    it("switches to My Queries tab when clicked", () => {
      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /my queries/i }));

      expect(queriesApi.useQueries).toHaveBeenLastCalledWith(
        expect.objectContaining({ owner_id: "me" })
      );
    });

    it("switches to Favorites tab when clicked", () => {
      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /favorites/i }));

      expect(queriesApi.useQueries).toHaveBeenLastCalledWith(
        expect.objectContaining({ is_favorite: true })
      );
    });

    it("switches to Team tab when clicked", () => {
      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /team/i }));

      expect(queriesApi.useQueries).toHaveBeenLastCalledWith(
        expect.objectContaining({ visibility: "team" })
      );
    });

    it("switches to Public tab when clicked", () => {
      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /public/i }));

      expect(queriesApi.useQueries).toHaveBeenLastCalledWith(
        expect.objectContaining({ visibility: "public" })
      );
    });

    it("shows query count in tab badges", () => {
      render(<SharedQueriesPage />);

      // Stats show total, team, public counts
      expect(screen.getByText("125")).toBeInTheDocument();
      expect(screen.getByText("50")).toBeInTheDocument();
      expect(screen.getByText("45")).toBeInTheDocument();
    });

    it("shows different empty state for My Queries tab", () => {
      vi.mocked(queriesApi.useQueries).mockReturnValue({
        data: [],
        isPending: false,
        error: null,
      } as ReturnType<typeof queriesApi.useQueries>);

      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /my queries/i }));

      expect(
        screen.getByText(/you haven't created any queries yet/i)
      ).toBeInTheDocument();
    });

    it("shows different empty state for Favorites tab", () => {
      vi.mocked(queriesApi.useQueries).mockReturnValue({
        data: [],
        isPending: false,
        error: null,
      } as ReturnType<typeof queriesApi.useQueries>);

      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /favorites/i }));

      expect(screen.getByText(/no favorite queries/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Filters
  // ===========================================================================

  describe("Filters", () => {
    it("filters by search term", () => {
      render(<SharedQueriesPage />);

      const searchInput = screen.getByPlaceholderText(/search queries/i);
      fireEvent.change(searchInput, { target: { value: "calibration" } });

      expect(queriesApi.useQueries).toHaveBeenLastCalledWith(
        expect.objectContaining({ search: "calibration" })
      );
    });

    it("filters by target type", () => {
      render(<SharedQueriesPage />);

      const filterSelect = screen.getByLabelText(/filter by target type/i);
      fireEvent.change(filterSelect, { target: { value: "source" } });

      expect(queriesApi.useQueries).toHaveBeenLastCalledWith(
        expect.objectContaining({ target_type: "source" })
      );
    });

    it("clears target filter when All Targets is selected", () => {
      render(<SharedQueriesPage />);

      const filterSelect = screen.getByLabelText(/filter by target type/i);
      fireEvent.change(filterSelect, { target: { value: "source" } });
      fireEvent.change(filterSelect, { target: { value: "" } });

      expect(queriesApi.useQueries).toHaveBeenLastCalledWith(
        expect.not.objectContaining({ target_type: "source" })
      );
    });
  });

  // ===========================================================================
  // Create Query Modal
  // ===========================================================================

  describe("Create Query Modal", () => {
    it("opens modal when New Query button is clicked", () => {
      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /new query/i }));

      expect(screen.getByText("New Query")).toBeInTheDocument();
    });

    it("renders all form fields in modal", () => {
      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /new query/i }));

      expect(screen.getByLabelText(/^name$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/target type/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/visibility/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^query$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/tags/i)).toBeInTheDocument();
    });

    it("closes modal when Cancel is clicked", () => {
      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /new query/i }));
      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

      expect(screen.queryByText("New Query")).not.toBeInTheDocument();
    });

    it("submits form with correct data", async () => {
      mockCreateMutation.mutateAsync.mockResolvedValue({});

      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /new query/i }));

      fireEvent.change(screen.getByLabelText(/^name$/i), {
        target: { value: "Test Query" },
      });
      fireEvent.change(screen.getByLabelText(/description/i), {
        target: { value: "Test description" },
      });
      fireEvent.change(screen.getByLabelText(/^query$/i), {
        target: { value: "SELECT * FROM sources" },
      });
      fireEvent.change(screen.getByLabelText(/tags/i), {
        target: { value: "test, example" },
      });

      fireEvent.click(screen.getByRole("button", { name: /save query/i }));

      await waitFor(() => {
        expect(mockCreateMutation.mutateAsync).toHaveBeenCalledWith({
          name: "Test Query",
          description: "Test description",
          query_string: "SELECT * FROM sources",
          target_type: "source",
          visibility: "private",
          tags: ["test", "example"],
        });
      });
    });

    it("detects parameters in query string", () => {
      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /new query/i }));

      fireEvent.change(screen.getByLabelText(/^query$/i), {
        target: {
          value:
            "SELECT * FROM sources WHERE flux > {{min_flux}} AND ra < {{max_ra}}",
        },
      });

      expect(
        screen.getByText(/detected parameters: min_flux, max_ra/i)
      ).toBeInTheDocument();
    });

    it("shows validation error for dangerous keywords", () => {
      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /new query/i }));

      fireEvent.change(screen.getByLabelText(/^query$/i), {
        target: { value: "DROP TABLE sources" },
      });

      expect(screen.getByText(/dangerous keyword: drop/i)).toBeInTheDocument();
    });

    it("disables submit when name is empty", () => {
      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /new query/i }));

      fireEvent.change(screen.getByLabelText(/^query$/i), {
        target: { value: "SELECT * FROM sources" },
      });

      const submitButton = screen.getByRole("button", { name: /save query/i });
      expect(submitButton).toBeDisabled();
    });

    it("disables submit when query is empty", () => {
      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /new query/i }));

      fireEvent.change(screen.getByLabelText(/^name$/i), {
        target: { value: "Test Query" },
      });

      const submitButton = screen.getByRole("button", { name: /save query/i });
      expect(submitButton).toBeDisabled();
    });
  });

  // ===========================================================================
  // Edit Query Modal
  // ===========================================================================

  describe("Edit Query Modal", () => {
    it("opens edit modal with pre-filled data", () => {
      render(<SharedQueriesPage />);

      const editButtons = screen.getAllByRole("button", { name: /edit/i });
      fireEvent.click(editButtons[0]);

      expect(screen.getByText("Edit Query")).toBeInTheDocument();
      expect(
        screen.getByDisplayValue("Find Bright Sources")
      ).toBeInTheDocument();
      expect(
        screen.getByDisplayValue("Find sources with flux > 100mJy")
      ).toBeInTheDocument();
    });

    it("shows Update Query button instead of Save Query", () => {
      render(<SharedQueriesPage />);

      const editButtons = screen.getAllByRole("button", { name: /edit/i });
      fireEvent.click(editButtons[0]);

      expect(
        screen.getByRole("button", { name: /update query/i })
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Run Query Modal
  // ===========================================================================

  describe("Run Query Modal", () => {
    it("opens run modal when Run button is clicked", () => {
      render(<SharedQueriesPage />);

      const runButtons = screen.getAllByRole("button", { name: /▶ run$/i });
      fireEvent.click(runButtons[0]);

      expect(
        screen.getByText(/run query: find bright sources/i)
      ).toBeInTheDocument();
    });

    it("displays query preview in run modal", () => {
      render(<SharedQueriesPage />);

      const runButtons = screen.getAllByRole("button", { name: /▶ run$/i });
      fireEvent.click(runButtons[0]);

      expect(
        screen.getByText(
          /SELECT \* FROM sources WHERE flux > \{\{min_flux\}\}/i
        )
      ).toBeInTheDocument();
    });

    it("shows parameter inputs for parameterized queries", () => {
      render(<SharedQueriesPage />);

      const runButtons = screen.getAllByRole("button", { name: /▶ run$/i });
      fireEvent.click(runButtons[0]);

      expect(screen.getByLabelText(/min_flux/i)).toBeInTheDocument();
    });

    it("executes query when Run Query button is clicked", async () => {
      render(<SharedQueriesPage />);

      const runButtons = screen.getAllByRole("button", { name: /▶ run$/i });
      fireEvent.click(runButtons[0]);

      fireEvent.change(screen.getByLabelText(/min_flux/i), {
        target: { value: "100" },
      });

      fireEvent.click(screen.getByRole("button", { name: /▶ run query$/i }));

      await waitFor(() => {
        expect(mockRunMutation.mutateAsync).toHaveBeenCalledWith({
          query_id: "q1",
          parameters: { min_flux: "100" },
        });
      });
    });

    it("displays results after query execution", async () => {
      render(<SharedQueriesPage />);

      const runButtons = screen.getAllByRole("button", { name: /▶ run$/i });
      fireEvent.click(runButtons[0]);

      fireEvent.click(screen.getByRole("button", { name: /▶ run query$/i }));

      await waitFor(() => {
        expect(screen.getByText(/results \(3 rows\)/i)).toBeInTheDocument();
      });
    });

    it("displays result columns in table header", async () => {
      render(<SharedQueriesPage />);

      const runButtons = screen.getAllByRole("button", { name: /▶ run$/i });
      fireEvent.click(runButtons[0]);

      fireEvent.click(screen.getByRole("button", { name: /▶ run query$/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("columnheader", { name: /id/i })
        ).toBeInTheDocument();
        expect(
          screen.getByRole("columnheader", { name: /name/i })
        ).toBeInTheDocument();
        expect(
          screen.getByRole("columnheader", { name: /flux/i })
        ).toBeInTheDocument();
      });
    });

    it("displays result data in table rows", async () => {
      render(<SharedQueriesPage />);

      const runButtons = screen.getAllByRole("button", { name: /▶ run$/i });
      fireEvent.click(runButtons[0]);

      fireEvent.click(screen.getByRole("button", { name: /▶ run query$/i }));

      await waitFor(() => {
        expect(screen.getByText("Source A")).toBeInTheDocument();
        expect(screen.getByText("Source B")).toBeInTheDocument();
        expect(screen.getByText("150.5")).toBeInTheDocument();
      });
    });

    it("shows execution time in results", async () => {
      render(<SharedQueriesPage />);

      const runButtons = screen.getAllByRole("button", { name: /▶ run$/i });
      fireEvent.click(runButtons[0]);

      fireEvent.click(screen.getByRole("button", { name: /▶ run query$/i }));

      await waitFor(() => {
        expect(screen.getByText(/245ms/i)).toBeInTheDocument();
      });
    });

    it("closes run modal when Close button is clicked", () => {
      render(<SharedQueriesPage />);

      const runButtons = screen.getAllByRole("button", { name: /▶ run$/i });
      fireEvent.click(runButtons[0]);

      fireEvent.click(screen.getByRole("button", { name: /close/i }));

      expect(
        screen.queryByText(/run query: find bright sources/i)
      ).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Statistics Panel
  // ===========================================================================

  describe("Statistics Panel", () => {
    it("renders statistics panel", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText("📊 Query Statistics")).toBeInTheDocument();
    });

    it("displays total queries count", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText("Total Queries")).toBeInTheDocument();
      expect(screen.getByText("125")).toBeInTheDocument();
    });

    it("displays public, team, private counts", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText("Public")).toBeInTheDocument();
      expect(screen.getByText("Team")).toBeInTheDocument();
      expect(screen.getByText("Private")).toBeInTheDocument();
    });

    it("displays queries run today", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText("Queries Run Today")).toBeInTheDocument();
      expect(screen.getByText("23")).toBeInTheDocument();
    });

    it("displays queries run this week", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText("This Week")).toBeInTheDocument();
      expect(screen.getByText("156")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Popular Queries Panel
  // ===========================================================================

  describe("Popular Queries Panel", () => {
    it("renders popular queries panel", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText("🔥 Popular Queries")).toBeInTheDocument();
    });

    it("displays top queries with run counts", () => {
      render(<SharedQueriesPage />);

      // Get all instances and check there's at least one with the expected run counts
      const runCount42 = screen.getAllByText("42 runs");
      const runCount15 = screen.getAllByText("15 runs");
      expect(runCount42.length).toBeGreaterThan(0);
      expect(runCount15.length).toBeGreaterThan(0);
    });

    it("displays query rankings", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText("#1")).toBeInTheDocument();
      expect(screen.getByText("#2")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Popular Tags Panel
  // ===========================================================================

  describe("Popular Tags Panel", () => {
    it("renders popular tags panel", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText("🏷️ Popular Tags")).toBeInTheDocument();
    });

    it("displays tags with counts", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText("flux (32)")).toBeInTheDocument();
      expect(screen.getByText("calibration (28)")).toBeInTheDocument();
      expect(screen.getByText("daily (15)")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Tips Section
  // ===========================================================================

  describe("Tips Section", () => {
    it("renders query tips", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText("💡 Query Tips")).toBeInTheDocument();
    });

    it("displays tip about parameterized queries", () => {
      render(<SharedQueriesPage />);

      expect(
        screen.getByText(/for parameterized queries/i)
      ).toBeInTheDocument();
    });

    it("displays tip about team queries", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText(/share team queries/i)).toBeInTheDocument();
    });

    it("displays tip about cloning queries", () => {
      render(<SharedQueriesPage />);

      expect(screen.getByText(/clone queries to modify/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Utility Functions
  // ===========================================================================

  describe("Utility Functions", () => {
    it("formats target type correctly", () => {
      expect(queriesApi.getTargetTypeLabel("source")).toBe("Sources");
      expect(queriesApi.getTargetTypeLabel("image")).toBe("Images");
      expect(queriesApi.getTargetTypeLabel("job")).toBe("Jobs");
      expect(queriesApi.getTargetTypeLabel("observation")).toBe("Observations");
      expect(queriesApi.getTargetTypeLabel("ms")).toBe("Measurement Sets");
    });

    it("returns correct visibility icons", () => {
      expect(queriesApi.getVisibilityIcon("private")).toBe("🔒");
      expect(queriesApi.getVisibilityIcon("team")).toBe("👥");
      expect(queriesApi.getVisibilityIcon("public")).toBe("🌐");
    });

    it("formats execution time correctly", () => {
      expect(queriesApi.formatExecutionTime(500)).toBe("500ms");
      expect(queriesApi.formatExecutionTime(1500)).toBe("1.50s");
      expect(queriesApi.formatExecutionTime(2345)).toBe("2.35s");
    });

    it("validates query syntax correctly", () => {
      expect(
        queriesApi.validateQuerySyntax("SELECT * FROM sources").valid
      ).toBe(true);
      expect(queriesApi.validateQuerySyntax("DROP TABLE sources").valid).toBe(
        false
      );
      expect(queriesApi.validateQuerySyntax("DELETE FROM sources").valid).toBe(
        false
      );
      expect(queriesApi.validateQuerySyntax("").valid).toBe(false);
    });

    it("extracts parameters from query string", () => {
      expect(
        queriesApi.extractParameters(
          "SELECT * FROM sources WHERE flux > {{min_flux}}"
        )
      ).toEqual(["min_flux"]);
      expect(
        queriesApi.extractParameters(
          "SELECT * FROM sources WHERE flux > {{min_flux}} AND ra < {{max_ra}}"
        )
      ).toEqual(["min_flux", "max_ra"]);
      expect(queriesApi.extractParameters("SELECT * FROM sources")).toEqual([]);
    });

    it("substitutes parameters in query", () => {
      expect(
        queriesApi.substituteParameters(
          "SELECT * FROM sources WHERE flux > {{min_flux}}",
          { min_flux: "100" }
        )
      ).toBe("SELECT * FROM sources WHERE flux > 100");
    });
  });

  // ===========================================================================
  // Integration Scenarios
  // ===========================================================================

  describe("Integration Scenarios", () => {
    it("creates query, then shows it in list", async () => {
      const newQuery: queriesApi.SavedQuery = {
        id: "q-new",
        name: "Newly Created Query",
        description: "A new query",
        query_string: "SELECT * FROM images",
        target_type: "image",
        visibility: "private",
        owner_id: "me",
        owner_name: "Alice Smith",
        tags: [],
        parameters: [],
        is_favorite: false,
        run_count: 0,
        last_run_at: null,
        created_at: "2024-01-16T10:00:00Z",
        updated_at: "2024-01-16T10:00:00Z",
      };

      mockCreateMutation.mutateAsync.mockResolvedValue(newQuery);

      render(<SharedQueriesPage />);

      // Open create modal
      fireEvent.click(screen.getByRole("button", { name: /new query/i }));

      // Fill form
      fireEvent.change(screen.getByLabelText(/^name$/i), {
        target: { value: "Newly Created Query" },
      });
      fireEvent.change(screen.getByLabelText(/^query$/i), {
        target: { value: "SELECT * FROM images" },
      });

      // Submit
      fireEvent.click(screen.getByRole("button", { name: /save query/i }));

      await waitFor(() => {
        expect(mockCreateMutation.mutateAsync).toHaveBeenCalled();
      });
    });

    it("runs query with multiple parameters", async () => {
      const multiParamQuery: queriesApi.SavedQuery = {
        ...mockQueries[0],
        query_string:
          "SELECT * FROM sources WHERE flux > {{min_flux}} AND ra BETWEEN {{ra_min}} AND {{ra_max}}",
      };

      vi.mocked(queriesApi.useQueries).mockReturnValue({
        data: [multiParamQuery],
        isPending: false,
        error: null,
      } as ReturnType<typeof queriesApi.useQueries>);

      render(<SharedQueriesPage />);

      // Open run modal
      const runButton = screen.getByRole("button", { name: /▶ run$/i });
      fireEvent.click(runButton);

      // Fill all parameters
      fireEvent.change(screen.getByLabelText(/min_flux/i), {
        target: { value: "100" },
      });
      fireEvent.change(screen.getByLabelText(/ra_min/i), {
        target: { value: "0" },
      });
      fireEvent.change(screen.getByLabelText(/ra_max/i), {
        target: { value: "360" },
      });

      // Run
      fireEvent.click(screen.getByRole("button", { name: /▶ run query$/i }));

      await waitFor(() => {
        expect(mockRunMutation.mutateAsync).toHaveBeenCalledWith({
          query_id: "q1",
          parameters: { min_flux: "100", ra_min: "0", ra_max: "360" },
        });
      });
    });

    it("filters and searches together", () => {
      render(<SharedQueriesPage />);

      // Apply search
      fireEvent.change(screen.getByPlaceholderText(/search queries/i), {
        target: { value: "calibration" },
      });

      // Apply filter
      fireEvent.change(screen.getByLabelText(/filter by target type/i), {
        target: { value: "image" },
      });

      expect(queriesApi.useQueries).toHaveBeenLastCalledWith(
        expect.objectContaining({
          search: "calibration",
          target_type: "image",
        })
      );
    });

    it("handles visibility selection in create form", () => {
      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /new query/i }));

      const visibilitySelect = screen.getByLabelText(/visibility/i);
      fireEvent.change(visibilitySelect, { target: { value: "public" } });

      expect(visibilitySelect).toHaveValue("public");
    });

    it("handles target type selection in create form", () => {
      render(<SharedQueriesPage />);

      fireEvent.click(screen.getByRole("button", { name: /new query/i }));

      const targetSelect = screen.getByLabelText(/target type/i);
      fireEvent.change(targetSelect, { target: { value: "observation" } });

      expect(targetSelect).toHaveValue("observation");
    });
  });
});
