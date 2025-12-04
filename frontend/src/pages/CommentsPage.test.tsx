/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import CommentsPage from "./CommentsPage";

// Mock the comments API hooks
const mockStatsData = {
  total_comments: 850,
  pinned_comments: 25,
  resolved_comments: 320,
  active_threads: 45,
  comments_today: 15,
  comments_this_week: 120,
  top_commenters: [
    { user_id: "user1", username: "Alice", comment_count: 95 },
    { user_id: "user2", username: "Bob", comment_count: 75 },
    { user_id: "user3", username: "Charlie", comment_count: 60 },
  ],
  target_distribution: {
    source: 400,
    image: 250,
    observation: 100,
    job: 50,
    ms: 50,
  },
};

const mockComments = [
  {
    id: "comment1",
    target_type: "source" as const,
    target_id: "J1234+5678",
    user_id: "user1",
    username: "Alice",
    content: "This source shows interesting variability @Bob",
    is_pinned: true,
    is_resolved: false,
    parent_id: null,
    reply_count: 3,
    created_at: "2024-01-15T10:00:00Z",
    updated_at: "2024-01-15T10:00:00Z",
  },
  {
    id: "comment2",
    target_type: "image" as const,
    target_id: "img-20240115",
    user_id: "user2",
    username: "Bob",
    content: "Calibration looks good on this image",
    is_pinned: false,
    is_resolved: true,
    parent_id: null,
    reply_count: 0,
    created_at: "2024-01-14T09:00:00Z",
    updated_at: "2024-01-14T09:00:00Z",
  },
  {
    id: "comment3",
    target_type: "observation" as const,
    target_id: "obs-001",
    user_id: "me",
    username: "TestUser",
    content: "Need to recheck this observation",
    is_pinned: false,
    is_resolved: false,
    parent_id: null,
    reply_count: 1,
    created_at: "2024-01-13T08:00:00Z",
    updated_at: "2024-01-13T08:00:00Z",
  },
];

const mockMentionableUsers = [
  { user_id: "user1", username: "Alice" },
  { user_id: "user2", username: "Bob" },
  { user_id: "user3", username: "Charlie" },
];

// Mock implementations
const mockUseComments = vi.fn();
const mockUseCommentStats = vi.fn();
const mockUseCreateComment = vi.fn();
const mockUseDeleteComment = vi.fn();
const mockUsePinComment = vi.fn();
const mockUseUnpinComment = vi.fn();
const mockUseResolveComment = vi.fn();
const mockUseUnresolveComment = vi.fn();
const mockUseMentionableUsers = vi.fn();

vi.mock("../api/comments", () => ({
  useComments: () => mockUseComments(),
  useCommentStats: () => mockUseCommentStats(),
  useCreateComment: () => mockUseCreateComment(),
  useDeleteComment: () => mockUseDeleteComment(),
  usePinComment: () => mockUsePinComment(),
  useUnpinComment: () => mockUseUnpinComment(),
  useResolveComment: () => mockUseResolveComment(),
  useUnresolveComment: () => mockUseUnresolveComment(),
  useMentionableUsers: () => mockUseMentionableUsers(),
  formatCommentTime: (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date("2024-01-16T12:00:00Z");
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffDays < 1) return "Today";
    if (diffDays === 1) return "1d ago";
    return `${diffDays}d ago`;
  },
  getTargetTypeLabel: (type: string) => {
    const labels: Record<string, string> = {
      source: "Source",
      image: "Image",
      observation: "Observation",
      job: "Job",
      ms: "Measurement Set",
    };
    return labels[type] || type;
  },
  getTargetTypeEmoji: (type: string) => {
    const emojis: Record<string, string> = {
      source: "🔭",
      image: "🖼️",
      observation: "📡",
      job: "⚙️",
      ms: "📊",
    };
    return emojis[type] || "📝";
  },
}));

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

describe("CommentsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementations
    mockUseComments.mockReturnValue({
      data: mockComments,
      isPending: false,
      error: null,
    });

    mockUseCommentStats.mockReturnValue({
      data: mockStatsData,
      isPending: false,
      error: null,
    });

    mockUseCreateComment.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
    });

    mockUseDeleteComment.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
    });

    mockUsePinComment.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });

    mockUseUnpinComment.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });

    mockUseResolveComment.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });

    mockUseUnresolveComment.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });

    mockUseMentionableUsers.mockReturnValue({
      data: mockMentionableUsers,
      isPending: false,
    });
  });

  describe("Page Header", () => {
    it("renders page title", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("💬 Comments")).toBeInTheDocument();
    });

    it("renders page description", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByText(
          "Discuss and annotate sources, images, and observations"
        )
      ).toBeInTheDocument();
    });

    it("renders New Comment button", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("New Comment")).toBeInTheDocument();
    });
  });

  describe("Tabs", () => {
    it("renders All Comments tab", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText(/All Comments/)).toBeInTheDocument();
    });

    it("renders My Comments tab", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText(/My Comments/)).toBeInTheDocument();
    });

    it("renders Pinned tab with count", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText(/📌 Pinned/)).toBeInTheDocument();
    });

    it("renders Unresolved tab", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText(/Unresolved/)).toBeInTheDocument();
    });

    it("switches to My Comments tab when clicked", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      const myCommentsTab = screen.getByText(/My Comments/);
      await userEvent.click(myCommentsTab);

      // Should have border-blue-600 class for active state
      expect(myCommentsTab).toHaveClass("border-blue-600");
    });

    it("shows total count badge on All Comments tab", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("850")).toBeInTheDocument();
    });

    it("shows pinned count badge on Pinned tab", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("25")).toBeInTheDocument();
    });
  });

  describe("Filters", () => {
    it("renders search input", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByPlaceholderText("Search comments...")
      ).toBeInTheDocument();
    });

    it("renders target type filter", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByLabelText("Filter by target type")
      ).toBeInTheDocument();
    });

    it("includes all target types in filter", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      const select = screen.getByLabelText("Filter by target type");
      expect(select).toContainHTML("All Types");
      expect(select).toContainHTML("Sources");
      expect(select).toContainHTML("Images");
      expect(select).toContainHTML("Observations");
      expect(select).toContainHTML("Jobs");
      expect(select).toContainHTML("Measurement Sets");
    });
  });

  describe("Comments List", () => {
    it("renders comment cards", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("Alice")).toBeInTheDocument();
      expect(screen.getByText("Bob")).toBeInTheDocument();
    });

    it("displays comment content", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByText("This source shows interesting variability @Bob")
      ).toBeInTheDocument();
    });

    it("displays target info on comments", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText(/on Source J1234\+5678/)).toBeInTheDocument();
    });

    it("displays pinned badge on pinned comments", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("📌 Pinned")).toBeInTheDocument();
    });

    it("displays resolved badge on resolved comments", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("✓ Resolved")).toBeInTheDocument();
    });

    it("displays reply count on comments with replies", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("💬 3 replies")).toBeInTheDocument();
    });

    it("shows loading state", () => {
      mockUseComments.mockReturnValue({
        data: undefined,
        isPending: true,
        error: null,
      });
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("Loading comments...")).toBeInTheDocument();
    });

    it("shows error state", () => {
      mockUseComments.mockReturnValue({
        data: undefined,
        isPending: false,
        error: new Error("Error"),
      });
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("Error loading comments")).toBeInTheDocument();
    });

    it("shows empty state for no comments", () => {
      mockUseComments.mockReturnValue({
        data: [],
        isPending: false,
        error: null,
      });
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("No comments found.")).toBeInTheDocument();
    });

    it("shows empty state for pinned tab", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });

      // Click pinned tab
      await userEvent.click(screen.getByText(/📌 Pinned/));

      mockUseComments.mockReturnValue({
        data: [],
        isPending: false,
        error: null,
      });

      // Re-render to see empty state
      const { rerender } = render(<CommentsPage />, {
        wrapper: createWrapper(),
      });
      await userEvent.click(screen.getByText(/📌 Pinned/));
    });
  });

  describe("Comment Actions", () => {
    it("shows Reply button on hover", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      const commentCard = screen.getByText("Alice").closest("div");

      // Trigger mouse enter on the card container
      if (commentCard?.parentElement?.parentElement?.parentElement) {
        fireEvent.mouseEnter(
          commentCard.parentElement.parentElement.parentElement
        );
      }

      await waitFor(() => {
        const replyButtons = screen.getAllByText("Reply");
        expect(replyButtons.length).toBeGreaterThan(0);
      });
    });

    it("shows Pin button on hover for unpinned comment", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });

      // Find an unpinned comment card (Bob's comment)
      const bobComment = screen.getByText(
        "Calibration looks good on this image"
      );
      const commentCard = bobComment.closest('[class*="rounded-lg shadow"]');

      if (commentCard) {
        fireEvent.mouseEnter(commentCard);
      }

      await waitFor(() => {
        const pinButtons = screen.getAllByText("Pin");
        expect(pinButtons.length).toBeGreaterThan(0);
      });
    });

    it("shows Unpin button on pinned comment", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });

      // Find the pinned comment card (Alice's comment)
      const pinnedComment = screen.getByText(
        "This source shows interesting variability @Bob"
      );
      const commentCard = pinnedComment.closest('[class*="rounded-lg shadow"]');

      if (commentCard) {
        fireEvent.mouseEnter(commentCard);
      }

      await waitFor(() => {
        expect(screen.getByText("Unpin")).toBeInTheDocument();
      });
    });

    it("shows Resolve button on unresolved comment", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });

      const unresolvedComment = screen.getByText(
        "This source shows interesting variability @Bob"
      );
      const commentCard = unresolvedComment.closest(
        '[class*="rounded-lg shadow"]'
      );

      if (commentCard) {
        fireEvent.mouseEnter(commentCard);
      }

      await waitFor(() => {
        expect(screen.getByText("Resolve")).toBeInTheDocument();
      });
    });

    it("shows Unresolve button on resolved comment", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });

      const resolvedComment = screen.getByText(
        "Calibration looks good on this image"
      );
      const commentCard = resolvedComment.closest(
        '[class*="rounded-lg shadow"]'
      );

      if (commentCard) {
        fireEvent.mouseEnter(commentCard);
      }

      await waitFor(() => {
        expect(screen.getByText("Unresolve")).toBeInTheDocument();
      });
    });
  });

  describe("Create Comment Modal", () => {
    it("opens modal when New Comment is clicked", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("New Comment"));

      expect(
        screen.getByRole("heading", { name: "New Comment" })
      ).toBeInTheDocument();
    });

    it("shows Target Type dropdown in modal", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("New Comment"));

      expect(screen.getByLabelText("Target Type")).toBeInTheDocument();
    });

    it("shows Target ID input in modal", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("New Comment"));

      expect(screen.getByLabelText("Target ID")).toBeInTheDocument();
    });

    it("shows Comment textarea in modal", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("New Comment"));

      expect(screen.getByLabelText("Comment")).toBeInTheDocument();
    });

    it("shows Cancel button in modal", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("New Comment"));

      expect(screen.getByText("Cancel")).toBeInTheDocument();
    });

    it("shows Post Comment button in modal", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("New Comment"));

      expect(screen.getByText("Post Comment")).toBeInTheDocument();
    });

    it("closes modal when Cancel is clicked", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("New Comment"));
      await userEvent.click(screen.getByText("Cancel"));

      expect(screen.queryByLabelText("Target Type")).not.toBeInTheDocument();
    });

    it("shows mention suggestions", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("New Comment"));

      expect(screen.getByText("@Alice")).toBeInTheDocument();
      expect(screen.getByText("@Bob")).toBeInTheDocument();
    });

    it("inserts mention when clicked", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("New Comment"));
      await userEvent.click(screen.getByText("@Alice"));

      const textarea = screen.getByLabelText("Comment") as HTMLTextAreaElement;
      expect(textarea.value).toContain("@Alice");
    });

    it("disables submit button when comment is empty", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("New Comment"));

      const submitButton = screen.getByText("Post Comment");
      expect(submitButton).toBeDisabled();
    });

    it("enables submit button when comment has content", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("New Comment"));
      await userEvent.type(screen.getByLabelText("Comment"), "Test comment");

      const submitButton = screen.getByText("Post Comment");
      expect(submitButton).not.toBeDisabled();
    });

    it("calls createComment when form is submitted", async () => {
      const mockSubmit = vi.fn().mockResolvedValue({});
      mockUseCreateComment.mockReturnValue({
        mutateAsync: mockSubmit,
        isPending: false,
      });

      render(<CommentsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("New Comment"));

      await userEvent.type(
        screen.getByLabelText("Target ID"),
        "test-source-id"
      );
      await userEvent.type(
        screen.getByLabelText("Comment"),
        "Test comment content"
      );

      await userEvent.click(screen.getByText("Post Comment"));

      await waitFor(() => {
        expect(mockSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            target_type: "source",
            target_id: "test-source-id",
            content: "Test comment content",
          })
        );
      });
    });
  });

  describe("Statistics Panel", () => {
    it("renders statistics title", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("📊 Comment Statistics")).toBeInTheDocument();
    });

    it("displays total comments", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      // 850 appears in stats panel and in tab badge
      const counts = screen.getAllByText("850");
      expect(counts.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Total Comments")).toBeInTheDocument();
    });

    it("displays active threads", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("45")).toBeInTheDocument();
      expect(screen.getByText("Active Threads")).toBeInTheDocument();
    });

    it("displays pinned count", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      // 25 appears in stats panel and in Pinned tab badge
      const counts = screen.getAllByText("25");
      expect(counts.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Pinned")).toBeInTheDocument();
    });

    it("displays resolved count", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("320")).toBeInTheDocument();
      expect(screen.getByText("Resolved")).toBeInTheDocument();
    });

    it("displays today's comment count", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("15 comments")).toBeInTheDocument();
    });

    it("displays this week's comment count", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("120 comments")).toBeInTheDocument();
    });
  });

  describe("Top Commenters Panel", () => {
    it("renders top commenters title", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("🏆 Top Commenters")).toBeInTheDocument();
    });

    it("displays top commenter names", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      // Names appear in both comments and leaderboard
      const aliceMatches = screen.getAllByText("Alice");
      expect(aliceMatches.length).toBeGreaterThanOrEqual(1);
      const bobMatches = screen.getAllByText("Bob");
      expect(bobMatches.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Charlie")).toBeInTheDocument();
    });

    it("displays comment counts", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("95 comments")).toBeInTheDocument();
      expect(screen.getByText("75 comments")).toBeInTheDocument();
      expect(screen.getByText("60 comments")).toBeInTheDocument();
    });

    it("displays ranking numbers", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("#1")).toBeInTheDocument();
      expect(screen.getByText("#2")).toBeInTheDocument();
      expect(screen.getByText("#3")).toBeInTheDocument();
    });
  });

  describe("Target Distribution Panel", () => {
    it("renders distribution title", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("📈 Comments by Target")).toBeInTheDocument();
    });

    it("displays source count", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("400")).toBeInTheDocument();
    });

    it("displays image count", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("250")).toBeInTheDocument();
    });

    it("displays observation count", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("100")).toBeInTheDocument();
    });

    it("displays target type labels", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      // These appear in the distribution panel
      expect(screen.getByText(/🔭 Source/)).toBeInTheDocument();
      expect(screen.getByText(/🖼️ Image/)).toBeInTheDocument();
      expect(screen.getByText(/📡 Observation/)).toBeInTheDocument();
    });
  });

  describe("Tips Panel", () => {
    it("renders tips title", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getByText("💡 Comment Tips")).toBeInTheDocument();
    });

    it("displays mention tip", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByText("• Use @username to mention team members")
      ).toBeInTheDocument();
    });

    it("displays pin tip", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByText("• Pin important comments for visibility")
      ).toBeInTheDocument();
    });

    it("displays resolve tip", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByText("• Mark resolved when discussion is complete")
      ).toBeInTheDocument();
    });

    it("displays reply tip", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(
        screen.getByText("• Reply to keep discussions organized")
      ).toBeInTheDocument();
    });
  });

  describe("Reply Modal", () => {
    it("opens with reply context when Reply is clicked", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });

      // Find the comment card and trigger hover
      const pinnedComment = screen.getByText(
        "This source shows interesting variability @Bob"
      );
      const commentCard = pinnedComment.closest('[class*="rounded-lg shadow"]');

      if (commentCard) {
        fireEvent.mouseEnter(commentCard);
      }

      await waitFor(async () => {
        const replyButtons = screen.getAllByText("Reply");
        await userEvent.click(replyButtons[0]);
      });

      // Modal should show reply context
      expect(screen.getByText(/Reply to Alice's comment/)).toBeInTheDocument();
    });

    it("shows Reply button instead of Post Comment for replies", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });

      const pinnedComment = screen.getByText(
        "This source shows interesting variability @Bob"
      );
      const commentCard = pinnedComment.closest('[class*="rounded-lg shadow"]');

      if (commentCard) {
        fireEvent.mouseEnter(commentCard);
      }

      await waitFor(async () => {
        const replyButtons = screen.getAllByText("Reply");
        await userEvent.click(replyButtons[0]);
      });

      // Button text should be "Reply" for reply modal
      expect(screen.getByRole("button", { name: "Reply" })).toBeInTheDocument();
    });

    it("does not show Target Type/ID fields for replies", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });

      const pinnedComment = screen.getByText(
        "This source shows interesting variability @Bob"
      );
      const commentCard = pinnedComment.closest('[class*="rounded-lg shadow"]');

      if (commentCard) {
        fireEvent.mouseEnter(commentCard);
      }

      await waitFor(async () => {
        const replyButtons = screen.getAllByText("Reply");
        await userEvent.click(replyButtons[0]);
      });

      // Target fields should not be in reply modal
      expect(screen.queryByLabelText("Target Type")).not.toBeInTheDocument();
      expect(screen.queryByLabelText("Target ID")).not.toBeInTheDocument();
    });
  });

  describe("Search Functionality", () => {
    it("updates search term on input", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      const searchInput = screen.getByPlaceholderText("Search comments...");

      await userEvent.type(searchInput, "variability");

      expect(searchInput).toHaveValue("variability");
    });

    it("filters comments by target type", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      const filterSelect = screen.getByLabelText("Filter by target type");

      await userEvent.selectOptions(filterSelect, "source");

      expect(filterSelect).toHaveValue("source");
    });
  });

  describe("Emoji and Icons", () => {
    it("displays source emoji", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getAllByText("🔭").length).toBeGreaterThan(0);
    });

    it("displays image emoji", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getAllByText("🖼️").length).toBeGreaterThan(0);
    });

    it("displays observation emoji", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      expect(screen.getAllByText("📡").length).toBeGreaterThan(0);
    });
  });

  describe("Accessibility", () => {
    it("has accessible search input", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      const searchInput = screen.getByPlaceholderText("Search comments...");
      expect(searchInput).toBeInTheDocument();
    });

    it("has accessible filter select", () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      const filterSelect = screen.getByLabelText("Filter by target type");
      expect(filterSelect).toBeInTheDocument();
    });

    it("modal form elements have labels", async () => {
      render(<CommentsPage />, { wrapper: createWrapper() });
      await userEvent.click(screen.getByText("New Comment"));

      expect(screen.getByLabelText("Target Type")).toBeInTheDocument();
      expect(screen.getByLabelText("Target ID")).toBeInTheDocument();
      expect(screen.getByLabelText("Comment")).toBeInTheDocument();
    });
  });
});
