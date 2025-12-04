/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import QARatingsPage from "./QARatingsPage";

// Mock the ratings API hooks
const mockStatsData = {
  total_ratings: 1250,
  sources_rated: 450,
  images_rated: 800,
  average_rating: 3.7,
  ratings_today: 25,
  ratings_this_week: 180,
  top_raters: [
    { user_id: "user1", username: "Alice", rating_count: 150 },
    { user_id: "user2", username: "Bob", rating_count: 120 },
    { user_id: "user3", username: "Charlie", rating_count: 95 },
  ],
  flag_distribution: {
    good: 800,
    uncertain: 250,
    bad: 100,
    needs_review: 100,
  },
};

const mockQueueData = [
  {
    target_type: "source" as const,
    target_id: "src-001",
    name: "J1234+5678",
    priority: "high" as const,
    reason: "Unusual morphology detected",
    created_at: "2024-01-15T10:00:00Z",
  },
  {
    target_type: "image" as const,
    target_id: "img-002",
    name: "Image 20240115_103000",
    priority: "medium" as const,
    reason: "Calibration flagged",
    created_at: "2024-01-15T11:00:00Z",
  },
  {
    target_type: "source" as const,
    target_id: "src-003",
    name: "J2345+6789",
    priority: "low" as const,
    reason: "New detection",
    created_at: "2024-01-15T12:00:00Z",
  },
];

const mockUserRatings = [
  {
    id: "rating1",
    target_type: "source" as const,
    target_id: "src-100",
    user_id: "me",
    username: "TestUser",
    category: "overall" as const,
    value: 4,
    flag: "good" as const,
    comment: "Good quality source",
    created_at: "2024-01-14T10:00:00Z",
    updated_at: "2024-01-14T10:00:00Z",
  },
  {
    id: "rating2",
    target_type: "image" as const,
    target_id: "img-200",
    user_id: "me",
    username: "TestUser",
    category: "calibration" as const,
    value: 3,
    flag: "uncertain" as const,
    created_at: "2024-01-13T10:00:00Z",
    updated_at: "2024-01-13T10:00:00Z",
  },
];

// Mock API module
vi.mock("../api/ratings", () => ({
  useRatingStats: vi.fn(),
  useRatingQueue: vi.fn(),
  useUserRatings: vi.fn(),
  useSubmitRating: vi.fn(),
  useRemoveFromQueue: vi.fn(),
}));

import {
  useRatingStats,
  useRatingQueue,
  useUserRatings,
  useSubmitRating,
  useRemoveFromQueue,
} from "../api/ratings";

const mockUseRatingStats = useRatingStats as ReturnType<typeof vi.fn>;
const mockUseRatingQueue = useRatingQueue as ReturnType<typeof vi.fn>;
const mockUseUserRatings = useUserRatings as ReturnType<typeof vi.fn>;
const mockUseSubmitRating = useSubmitRating as ReturnType<typeof vi.fn>;
const mockUseRemoveFromQueue = useRemoveFromQueue as ReturnType<typeof vi.fn>;

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

describe("QARatingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementations
    mockUseRatingStats.mockReturnValue({
      data: mockStatsData,
      isPending: false,
      error: null,
    });

    mockUseRatingQueue.mockReturnValue({
      data: mockQueueData,
      isPending: false,
      error: null,
    });

    mockUseUserRatings.mockReturnValue({
      data: mockUserRatings,
      isPending: false,
      error: null,
    });

    mockUseSubmitRating.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
    });

    mockUseRemoveFromQueue.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
    });
  });

  describe("Page Header", () => {
    it("renders the page title", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("QA Ratings")).toBeInTheDocument();
    });

    it("renders the page description", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByText("Rate sources and images for quality assessment")
      ).toBeInTheDocument();
    });

    it("renders the star icon", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("⭐")).toBeInTheDocument();
    });

    it("renders the Submit Rating button", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("Submit Rating")).toBeInTheDocument();
    });
  });

  describe("Tabs", () => {
    it("renders Review Queue tab", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText(/Review Queue/)).toBeInTheDocument();
    });

    it("renders My Ratings tab", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText(/My Ratings/)).toBeInTheDocument();
    });

    it("renders All Activity tab", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("All Activity")).toBeInTheDocument();
    });

    it("shows queue count badge", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("shows my ratings count badge", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("2")).toBeInTheDocument();
    });

    it("switches to My Ratings tab when clicked", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText(/My Ratings/));
      expect(screen.getByText("Good quality source")).toBeInTheDocument();
    });

    it("switches to All Activity tab when clicked", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("All Activity"));
      expect(
        screen.getByText("All activity view coming soon...")
      ).toBeInTheDocument();
    });
  });

  describe("Review Queue", () => {
    it("displays queue items", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("J1234+5678")).toBeInTheDocument();
      expect(screen.getByText("Image 20240115_103000")).toBeInTheDocument();
      expect(screen.getByText("J2345+6789")).toBeInTheDocument();
    });

    it("displays queue item reasons", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByText("Unusual morphology detected")
      ).toBeInTheDocument();
      expect(screen.getByText("Calibration flagged")).toBeInTheDocument();
      expect(screen.getByText("New detection")).toBeInTheDocument();
    });

    it("displays priority badges", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("high")).toBeInTheDocument();
      expect(screen.getByText("medium")).toBeInTheDocument();
      expect(screen.getByText("low")).toBeInTheDocument();
    });

    it("displays Rate Now buttons for each queue item", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      const rateButtons = screen.getAllByText("Rate Now");
      expect(rateButtons).toHaveLength(3);
    });

    it("displays Remove buttons for each queue item", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      const removeButtons = screen.getAllByText("Remove");
      expect(removeButtons).toHaveLength(3);
    });

    it("shows loading state", () => {
      mockUseRatingQueue.mockReturnValue({
        data: undefined,
        isPending: true,
        error: null,
      });
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("Loading queue...")).toBeInTheDocument();
    });

    it("shows error state", () => {
      mockUseRatingQueue.mockReturnValue({
        data: undefined,
        isPending: false,
        error: new Error("Network error"),
      });
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("Error loading queue")).toBeInTheDocument();
    });

    it("shows empty state", () => {
      mockUseRatingQueue.mockReturnValue({
        data: [],
        isPending: false,
        error: null,
      });
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByText("No items in review queue. Great job! 🎉")
      ).toBeInTheDocument();
    });

    it("calls removeFromQueue when Remove is clicked", async () => {
      const mockRemove = vi.fn().mockResolvedValue({});
      mockUseRemoveFromQueue.mockReturnValue({
        mutateAsync: mockRemove,
        isPending: false,
      });

      render(<QARatingsPage />, { wrapper: createWrapper() });
      const removeButtons = screen.getAllByText("Remove");
      await userEvent.click(removeButtons[0]);

      expect(mockRemove).toHaveBeenCalledWith({
        targetType: "source",
        targetId: "src-001",
      });
    });
  });

  describe("My Ratings", () => {
    it("displays user ratings", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText(/My Ratings/));

      expect(screen.getByText("Good quality source")).toBeInTheDocument();
    });

    it("displays rating categories", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText(/My Ratings/));

      expect(screen.getByText(/overall/)).toBeInTheDocument();
      expect(screen.getByText(/calibration/)).toBeInTheDocument();
    });

    it("displays quality flags on ratings", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText(/My Ratings/));

      expect(screen.getByText("Good")).toBeInTheDocument();
      expect(screen.getByText("Uncertain")).toBeInTheDocument();
    });

    it("shows loading state for user ratings", async () => {
      mockUseUserRatings.mockReturnValue({
        data: undefined,
        isPending: true,
        error: null,
      });
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText(/My Ratings/));

      expect(screen.getByText("Loading your ratings...")).toBeInTheDocument();
    });

    it("shows error state for user ratings", async () => {
      mockUseUserRatings.mockReturnValue({
        data: undefined,
        isPending: false,
        error: new Error("Error"),
      });
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText(/My Ratings/));

      expect(screen.getByText("Error loading ratings")).toBeInTheDocument();
    });

    it("shows empty state for user ratings", async () => {
      mockUseUserRatings.mockReturnValue({
        data: [],
        isPending: false,
        error: null,
      });
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText(/My Ratings/));

      expect(
        screen.getByText("You haven't submitted any ratings yet.")
      ).toBeInTheDocument();
    });
  });

  describe("Statistics Panel", () => {
    it("displays total ratings", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("1250")).toBeInTheDocument();
      expect(screen.getByText("Total Ratings")).toBeInTheDocument();
    });

    it("displays average rating", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("3.7")).toBeInTheDocument();
      expect(screen.getByText("Average Rating")).toBeInTheDocument();
    });

    it("displays sources rated count", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("450")).toBeInTheDocument();
      expect(screen.getByText("Sources Rated")).toBeInTheDocument();
    });

    it("displays images rated count", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("800")).toBeInTheDocument();
      expect(screen.getByText("Images Rated")).toBeInTheDocument();
    });

    it("displays today's ratings", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("Today")).toBeInTheDocument();
      expect(screen.getByText("25 ratings")).toBeInTheDocument();
    });

    it("displays this week's ratings", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("This Week")).toBeInTheDocument();
      expect(screen.getByText("180 ratings")).toBeInTheDocument();
    });
  });

  describe("Top Raters Panel", () => {
    it("displays top raters title", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("🏆 Top Raters")).toBeInTheDocument();
    });

    it("displays top rater names", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("Alice")).toBeInTheDocument();
      expect(screen.getByText("Bob")).toBeInTheDocument();
      expect(screen.getByText("Charlie")).toBeInTheDocument();
    });

    it("displays top rater counts", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("150 ratings")).toBeInTheDocument();
      expect(screen.getByText("120 ratings")).toBeInTheDocument();
      expect(screen.getByText("95 ratings")).toBeInTheDocument();
    });

    it("displays ranking numbers", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("#1")).toBeInTheDocument();
      expect(screen.getByText("#2")).toBeInTheDocument();
      expect(screen.getByText("#3")).toBeInTheDocument();
    });
  });

  describe("Quality Distribution Panel", () => {
    it("displays quality distribution title", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("Quality Distribution")).toBeInTheDocument();
    });

    it("displays quality flag counts in distribution", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      // These are in the distribution panel
      expect(screen.getByText("800")).toBeInTheDocument(); // good
      expect(screen.getByText("250")).toBeInTheDocument(); // uncertain
      expect(screen.getByText("100")).toBeInTheDocument(); // bad (and needs_review)
    });
  });

  describe("Rating Tips Panel", () => {
    it("displays tips title", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("💡 Rating Tips")).toBeInTheDocument();
    });

    it("displays tip about overall quality", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByText("• Rate overall quality first, then specific aspects")
      ).toBeInTheDocument();
    });

    it("displays tip about flags", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByText("• Use flags to quickly mark data quality")
      ).toBeInTheDocument();
    });

    it("displays tip about comments", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByText("• Add comments for unusual cases")
      ).toBeInTheDocument();
    });

    it("displays tip about queue", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByText("• Check the queue regularly for priority items")
      ).toBeInTheDocument();
    });
  });

  describe("Submit Rating Modal", () => {
    it("opens modal when Submit Rating button is clicked", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("Submit Rating"));

      expect(
        screen.getByRole("heading", { name: "Submit Rating" })
      ).toBeInTheDocument();
    });

    it("shows Target Type dropdown in modal", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("Submit Rating"));

      expect(screen.getByLabelText("Target Type")).toBeInTheDocument();
    });

    it("shows Target ID input in modal", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("Submit Rating"));

      expect(screen.getByLabelText("Target ID")).toBeInTheDocument();
    });

    it("shows Category dropdown in modal", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("Submit Rating"));

      expect(screen.getByLabelText("Category")).toBeInTheDocument();
    });

    it("shows Quality Flag dropdown in modal", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("Submit Rating"));

      expect(screen.getByLabelText("Quality Flag")).toBeInTheDocument();
    });

    it("shows Comment textarea in modal", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("Submit Rating"));

      expect(screen.getByLabelText("Comment (optional)")).toBeInTheDocument();
    });

    it("shows Cancel button in modal", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("Submit Rating"));

      expect(screen.getByText("Cancel")).toBeInTheDocument();
    });

    it("closes modal when Cancel is clicked", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("Submit Rating"));
      await userEvent.click(screen.getByText("Cancel"));

      expect(screen.queryByLabelText("Target Type")).not.toBeInTheDocument();
    });

    it("closes modal when X is clicked", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("Submit Rating"));
      await userEvent.click(screen.getByText("✕"));

      expect(screen.queryByLabelText("Target Type")).not.toBeInTheDocument();
    });

    it("shows rating options with categories", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("Submit Rating"));

      const categorySelect = screen.getByLabelText("Category");
      expect(categorySelect).toContainHTML("Overall");
      expect(categorySelect).toContainHTML("Flux");
      expect(categorySelect).toContainHTML("Morphology");
      expect(categorySelect).toContainHTML("Position");
      expect(categorySelect).toContainHTML("Calibration");
    });

    it("shows quality flag options", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("Submit Rating"));

      const flagSelect = screen.getByLabelText("Quality Flag");
      expect(flagSelect).toContainHTML("Good");
      expect(flagSelect).toContainHTML("Uncertain");
      expect(flagSelect).toContainHTML("Bad");
      expect(flagSelect).toContainHTML("Needs Review");
    });

    it("shows disabled submit button when no rating selected", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("Submit Rating"));

      // The submit button shows "Submit Rating" text but is disabled
      const buttons = screen.getAllByText("Submit Rating");
      // The second one is in the modal
      const submitButton = buttons.find((btn) =>
        btn.closest("form")
      ) as HTMLButtonElement;
      expect(submitButton).toBeDisabled();
    });

    it("opens modal with pre-filled data when Rate Now is clicked", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      const rateButtons = screen.getAllByText("Rate Now");
      await userEvent.click(rateButtons[0]);

      expect(
        screen.getByText(/for J1234\+5678/, { selector: "span" })
      ).toBeInTheDocument();
    });

    it("calls submitRating when form is submitted", async () => {
      const mockSubmit = vi.fn().mockResolvedValue({});
      mockUseSubmitRating.mockReturnValue({
        mutateAsync: mockSubmit,
        isPending: false,
      });

      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("Submit Rating"));

      // Fill in the form
      await userEvent.type(screen.getByLabelText("Target ID"), "test-id-123");

      // Click star ratings
      const starButtons = screen.getAllByText("☆");
      await userEvent.click(starButtons[3]); // 4 stars

      // Submit the form
      const submitButtons = screen.getAllByText("Submit Rating");
      const formSubmitButton = submitButtons.find((btn) => btn.closest("form"));
      await userEvent.click(formSubmitButton!);

      await waitFor(() => {
        expect(mockSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            target_type: "source",
            target_id: "test-id-123",
            category: "overall",
            value: 4,
            flag: "good",
          })
        );
      });
    });
  });

  describe("Star Rating Component", () => {
    it("renders 5 stars", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      // Open modal to see interactive stars
      fireEvent.click(screen.getByText("Submit Rating"));

      const emptyStars = screen.getAllByText("☆");
      expect(emptyStars.length).toBeGreaterThanOrEqual(5);
    });

    it("shows filled stars based on value in ratings", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText(/My Ratings/));

      // User ratings have stars displayed
      const filledStars = screen.getAllByText("⭐");
      expect(filledStars.length).toBeGreaterThan(0);
    });
  });

  describe("Quality Flag Badge", () => {
    it("renders Good badge with correct color", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText(/My Ratings/));

      const goodBadge = screen.getByText("Good");
      expect(goodBadge).toHaveClass("text-green-600");
    });

    it("renders Uncertain badge with correct color", async () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText(/My Ratings/));

      const uncertainBadge = screen.getByText("Uncertain");
      expect(uncertainBadge).toHaveClass("text-yellow-600");
    });
  });

  describe("Rating Statistics Display", () => {
    it("renders Rating Statistics title", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("Rating Statistics")).toBeInTheDocument();
    });

    it("formats average rating to one decimal", () => {
      mockUseRatingStats.mockReturnValue({
        data: { ...mockStatsData, average_rating: 4.256 },
        isPending: false,
        error: null,
      });
      render(<QARatingsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("4.3")).toBeInTheDocument();
    });
  });

  describe("Queue Item Icons", () => {
    it("displays telescope icon for source type", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      const telescopeIcons = screen.getAllByText("🔭");
      expect(telescopeIcons.length).toBeGreaterThan(0);
    });

    it("displays image icon for image type", () => {
      render(<QARatingsPage />, { wrapper: createWrapper() });
      const imageIcons = screen.getAllByText("🖼️");
      expect(imageIcons.length).toBeGreaterThan(0);
    });
  });
});
