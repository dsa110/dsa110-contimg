import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TagFilter, { TagFilterProps } from "./TagFilter";

describe("TagFilter", () => {
  const mockOnIncludeChange = vi.fn();
  const mockOnExcludeChange = vi.fn();

  const defaultProps: TagFilterProps = {
    availableTags: ["galaxy", "star", "pulsar", "agn", "transient", "variable"],
    includeTags: [],
    excludeTags: [],
    onIncludeChange: mockOnIncludeChange,
    onExcludeChange: mockOnExcludeChange,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders include tags section", () => {
      render(<TagFilter {...defaultProps} />);
      expect(screen.getByText("Include Tags")).toBeInTheDocument();
    });

    it("renders exclude tags section", () => {
      render(<TagFilter {...defaultProps} />);
      expect(screen.getByText("Exclude Tags")).toBeInTheDocument();
    });

    it("renders input fields", () => {
      render(<TagFilter {...defaultProps} />);
      const inputs = screen.getAllByRole("textbox");
      expect(inputs).toHaveLength(2);
    });

    it("applies custom className", () => {
      const { container } = render(<TagFilter {...defaultProps} className="custom-class" />);
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("displaying selected tags", () => {
    it("displays included tags as badges", () => {
      render(<TagFilter {...defaultProps} includeTags={["galaxy", "star"]} />);
      expect(screen.getByText("galaxy")).toBeInTheDocument();
      expect(screen.getByText("star")).toBeInTheDocument();
    });

    it("displays excluded tags as badges", () => {
      render(<TagFilter {...defaultProps} excludeTags={["pulsar"]} />);
      expect(screen.getByText("pulsar")).toBeInTheDocument();
    });
  });

  describe("adding tags", () => {
    it("shows suggestions when typing", async () => {
      render(<TagFilter {...defaultProps} />);
      const inputs = screen.getAllByRole("textbox");
      await userEvent.type(inputs[0], "gal");
      expect(screen.getByText("galaxy")).toBeInTheDocument();
    });

    it("filters suggestions based on input", async () => {
      render(<TagFilter {...defaultProps} />);
      const inputs = screen.getAllByRole("textbox");
      await userEvent.type(inputs[0], "pul");
      expect(screen.getByText("pulsar")).toBeInTheDocument();
      expect(screen.queryByText("galaxy")).not.toBeInTheDocument();
    });

    it("adds tag when suggestion clicked", async () => {
      render(<TagFilter {...defaultProps} />);
      const inputs = screen.getAllByRole("textbox");
      await userEvent.type(inputs[0], "gal");
      await userEvent.click(screen.getByText("galaxy"));
      expect(mockOnIncludeChange).toHaveBeenCalledWith(["galaxy"]);
    });

    it("excludes already selected tags from suggestions", async () => {
      render(<TagFilter {...defaultProps} includeTags={["galaxy"]} />);
      const inputs = screen.getAllByRole("textbox");
      await userEvent.type(inputs[0], "gal");
      // "galaxy" should not appear in suggestions since it's already included
      expect(screen.queryAllByText("galaxy")).toHaveLength(1); // Only the badge
    });
  });

  describe("removing tags", () => {
    it("removes include tag when x clicked", async () => {
      render(<TagFilter {...defaultProps} includeTags={["galaxy", "star"]} />);
      const removeButtons = screen.getAllByText("×");
      await userEvent.click(removeButtons[0]);
      expect(mockOnIncludeChange).toHaveBeenCalledWith(["star"]);
    });

    it("removes exclude tag when x clicked", async () => {
      render(<TagFilter {...defaultProps} excludeTags={["pulsar", "agn"]} />);
      const removeButtons = screen.getAllByText("×");
      await userEvent.click(removeButtons[0]);
      expect(mockOnExcludeChange).toHaveBeenCalledWith(["agn"]);
    });
  });

  describe("keyboard interaction", () => {
    it("clears input after adding tag", async () => {
      render(<TagFilter {...defaultProps} />);
      const inputs = screen.getAllByRole("textbox");
      await userEvent.type(inputs[0], "gal");
      await userEvent.click(screen.getByText("galaxy"));
      expect(inputs[0]).toHaveValue("");
    });
  });

  describe("tooltips", () => {
    it("shows tooltip for include tags", () => {
      render(<TagFilter {...defaultProps} />);
      const tooltips = document.querySelectorAll("span[title]");
      expect(tooltips.length).toBeGreaterThan(0);
    });
  });
});
