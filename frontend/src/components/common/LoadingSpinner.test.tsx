import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import LoadingSpinner from "./LoadingSpinner";

describe("LoadingSpinner", () => {
  describe("basic rendering", () => {
    it("renders spinner element", () => {
      render(<LoadingSpinner />);
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("has accessible label by default", () => {
      render(<LoadingSpinner />);
      expect(screen.getByRole("status")).toHaveAttribute("aria-label", "Loading");
    });
  });

  describe("size variants", () => {
    it("applies sm size classes", () => {
      render(<LoadingSpinner size="sm" />);
      const spinner = screen.getByRole("status");
      expect(spinner).toHaveClass("w-4", "h-4", "border-2");
    });

    it("applies md size classes by default", () => {
      render(<LoadingSpinner />);
      const spinner = screen.getByRole("status");
      expect(spinner).toHaveClass("w-8", "h-8");
    });

    it("applies lg size classes", () => {
      render(<LoadingSpinner size="lg" />);
      const spinner = screen.getByRole("status");
      expect(spinner).toHaveClass("w-12", "h-12", "border-4");
    });
  });

  describe("label", () => {
    it("shows label text when provided", () => {
      render(<LoadingSpinner label="Loading data..." />);
      expect(screen.getByText("Loading data...")).toBeInTheDocument();
    });

    it("does not show label when not provided", () => {
      render(<LoadingSpinner />);
      expect(screen.queryByText("Loading")).not.toBeInTheDocument();
    });

    it("uses label for aria-label when provided", () => {
      render(<LoadingSpinner label="Fetching results" />);
      expect(screen.getByRole("status")).toHaveAttribute("aria-label", "Fetching results");
    });
  });

  describe("centered mode", () => {
    it("is centered by default", () => {
      const { container } = render(<LoadingSpinner />);
      const wrapper = container.firstChild;
      expect(wrapper).toHaveClass("flex", "flex-col", "items-center", "justify-center");
    });

    it("applies vertical padding when centered", () => {
      const { container } = render(<LoadingSpinner centered />);
      expect(container.firstChild).toHaveClass("py-12");
    });

    it("uses inline layout when not centered", () => {
      const { container } = render(<LoadingSpinner centered={false} />);
      expect(container.firstChild).toHaveClass("inline-flex");
      expect(container.firstChild).not.toHaveClass("py-12");
    });
  });

  describe("styling", () => {
    it("has spin animation class", () => {
      render(<LoadingSpinner />);
      expect(screen.getByRole("status")).toHaveClass("animate-spin");
    });

    it("has rounded-full for circular shape", () => {
      render(<LoadingSpinner />);
      expect(screen.getByRole("status")).toHaveClass("rounded-full");
    });

    it("has blue border color", () => {
      render(<LoadingSpinner />);
      expect(screen.getByRole("status")).toHaveClass("border-blue-600");
    });

    it("has transparent top border for animation effect", () => {
      render(<LoadingSpinner />);
      expect(screen.getByRole("status")).toHaveClass("border-t-transparent");
    });
  });

  describe("with label styling", () => {
    it("shows label with gray text", () => {
      render(<LoadingSpinner label="Please wait..." />);
      const label = screen.getByText("Please wait...");
      expect(label).toHaveClass("text-gray-500");
    });

    it("shows label with small text size", () => {
      render(<LoadingSpinner label="Loading" />);
      const label = screen.getByText("Loading");
      expect(label).toHaveClass("text-sm");
    });

    it("label has gap from spinner when centered", () => {
      const { container } = render(<LoadingSpinner label="Loading" centered />);
      expect(container.firstChild).toHaveClass("gap-3");
    });

    it("label has gap from spinner when inline", () => {
      const { container } = render(<LoadingSpinner label="Loading" centered={false} />);
      expect(container.firstChild).toHaveClass("gap-2");
    });
  });

  describe("combinations", () => {
    it("renders small spinner with label, not centered", () => {
      const { container } = render(
        <LoadingSpinner size="sm" label="Saving..." centered={false} />
      );
      
      expect(screen.getByRole("status")).toHaveClass("w-4", "h-4");
      expect(screen.getByText("Saving...")).toBeInTheDocument();
      expect(container.firstChild).toHaveClass("inline-flex");
    });

    it("renders large spinner with label, centered", () => {
      const { container } = render(
        <LoadingSpinner size="lg" label="Processing large file..." />
      );
      
      expect(screen.getByRole("status")).toHaveClass("w-12", "h-12");
      expect(screen.getByText("Processing large file...")).toBeInTheDocument();
      expect(container.firstChild).toHaveClass("flex-col", "justify-center");
    });
  });
});
