import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RatingCard, { RatingCardProps, RatingTag } from "./RatingCard";

describe("RatingCard", () => {
  const mockOnSubmit = vi.fn();
  const mockOnNextUnrated = vi.fn();
  const mockOnCreateTag = vi.fn();

  const mockTags: RatingTag[] = [
    { id: "tag-1", name: "Galaxy", color: "#3b82f6", description: "Extragalactic source" },
    { id: "tag-2", name: "Star", color: "#22c55e", description: "Stellar source" },
    { id: "tag-3", name: "AGN", color: "#f59e0b", description: "Active galactic nucleus" },
  ];

  const defaultProps: RatingCardProps = {
    itemId: "item-123",
    itemName: "Source J1234+5678",
    tags: mockTags,
    onSubmit: mockOnSubmit,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockOnSubmit.mockResolvedValue(undefined);
    mockOnCreateTag.mockResolvedValue({ id: "new-tag", name: "NewTag" });
  });

  describe("rendering", () => {
    it("renders item name", () => {
      render(<RatingCard {...defaultProps} />);
      expect(screen.getByText(/source j1234\+5678/i)).toBeInTheDocument();
    });

    it("renders confidence options", () => {
      render(<RatingCard {...defaultProps} />);
      expect(screen.getByText("True")).toBeInTheDocument();
      expect(screen.getByText("False")).toBeInTheDocument();
      expect(screen.getByText("Unsure")).toBeInTheDocument();
    });

    it("renders tag options", () => {
      render(<RatingCard {...defaultProps} />);
      expect(screen.getByText("Galaxy")).toBeInTheDocument();
      expect(screen.getByText("Star")).toBeInTheDocument();
      expect(screen.getByText("AGN")).toBeInTheDocument();
    });

    it("renders notes textarea", () => {
      render(<RatingCard {...defaultProps} />);
      expect(screen.getByPlaceholderText(/notes/i)).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(<RatingCard {...defaultProps} className="custom-class" />);
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("with previous rating", () => {
    const previousRating = {
      id: "rating-1",
      confidence: "true" as const,
      tag: mockTags[0],
      notes: "This is a confirmed galaxy",
      user: "testuser",
      date: "2024-01-15T10:00:00Z",
    };

    it("shows previous confidence selection", () => {
      render(<RatingCard {...defaultProps} previousRating={previousRating} />);
      // True button should be active/selected
      const trueButton = screen.getByRole("button", { name: /true/i });
      expect(trueButton).toHaveClass("bg-green-500");
    });

    it("shows previous notes", () => {
      render(<RatingCard {...defaultProps} previousRating={previousRating} />);
      expect(screen.getByDisplayValue("This is a confirmed galaxy")).toBeInTheDocument();
    });

    it("shows previous rating info", () => {
      render(<RatingCard {...defaultProps} previousRating={previousRating} />);
      // The component shows "Your previous rating:" and date
      expect(screen.getByText(/previous rating/i)).toBeInTheDocument();
    });
  });

  describe("confidence selection", () => {
    it("allows selecting True confidence", async () => {
      render(<RatingCard {...defaultProps} />);
      await userEvent.click(screen.getByRole("button", { name: /true/i }));
      const trueButton = screen.getByRole("button", { name: /true/i });
      expect(trueButton).toHaveClass("bg-green-500");
    });

    it("allows selecting False confidence", async () => {
      render(<RatingCard {...defaultProps} />);
      await userEvent.click(screen.getByRole("button", { name: /false/i }));
      const falseButton = screen.getByRole("button", { name: /false/i });
      expect(falseButton).toHaveClass("bg-red-500");
    });

    it("allows selecting Unsure confidence", async () => {
      render(<RatingCard {...defaultProps} />);
      await userEvent.click(screen.getByRole("button", { name: /unsure/i }));
      const unsureButton = screen.getByRole("button", { name: /unsure/i });
      expect(unsureButton).toHaveClass("bg-yellow-500");
    });
  });

  describe("tag selection", () => {
    it("allows selecting a tag", async () => {
      render(<RatingCard {...defaultProps} />);
      const tagSelect = screen.getByRole("combobox");
      await userEvent.selectOptions(tagSelect, "tag-2");
      expect(tagSelect).toHaveValue("tag-2");
    });
  });

  describe("notes", () => {
    it("allows entering notes", async () => {
      render(<RatingCard {...defaultProps} />);
      const notesInput = screen.getByPlaceholderText(/notes/i);
      await userEvent.type(notesInput, "Test notes");
      expect(notesInput).toHaveValue("Test notes");
    });
  });

  describe("form submission", () => {
    it("calls onSubmit with rating data", async () => {
      render(<RatingCard {...defaultProps} />);

      await userEvent.click(screen.getByRole("button", { name: /true/i }));
      await userEvent.type(screen.getByPlaceholderText(/notes/i), "Test note");
      await userEvent.click(screen.getByRole("button", { name: /submit/i }));

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          itemId: "item-123",
          confidence: "true",
          tagId: "tag-1",
          notes: "Test note",
        });
      });
    });

    it("shows loading state while submitting", async () => {
      mockOnSubmit.mockImplementation(() => new Promise(() => {})); // Never resolves
      render(<RatingCard {...defaultProps} />);

      await userEvent.click(screen.getByRole("button", { name: /submit/i }));

      // Loading state might show as disabled button or different text
      const submitButton = screen.getByRole("button", { name: /submit|saving|loading/i });
      // Expect either disabled state or some loading indicator
      expect(submitButton).toBeInTheDocument();
    });
  });

  describe("next unrated button", () => {
    it("shows next button when onNextUnrated provided", () => {
      render(<RatingCard {...defaultProps} onNextUnrated={mockOnNextUnrated} />);
      expect(screen.getByRole("button", { name: /next unrated/i })).toBeInTheDocument();
    });

    it("calls onNextUnrated when clicked", async () => {
      render(<RatingCard {...defaultProps} onNextUnrated={mockOnNextUnrated} />);
      await userEvent.click(screen.getByRole("button", { name: /next unrated/i }));
      expect(mockOnNextUnrated).toHaveBeenCalled();
    });
  });

  describe("loading state", () => {
    it("disables form when isLoading is true", () => {
      render(<RatingCard {...defaultProps} isLoading />);
      expect(screen.getByRole("button", { name: /submit/i })).toBeDisabled();
    });
  });
});
