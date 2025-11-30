import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import StatCard, { StatCardProps } from "./StatCard";

const renderWithRouter = (props: StatCardProps) => {
  return render(
    <MemoryRouter>
      <StatCard {...props} />
    </MemoryRouter>
  );
};

describe("StatCard", () => {
  const defaultProps: StatCardProps = {
    label: "Total Images",
    value: 1234,
  };

  describe("rendering", () => {
    it("renders the label", () => {
      renderWithRouter(defaultProps);
      expect(screen.getByText("Total Images")).toBeInTheDocument();
    });

    it("renders the value", () => {
      renderWithRouter(defaultProps);
      expect(screen.getByText("1234")).toBeInTheDocument();
    });

    it("renders subtitle when provided", () => {
      renderWithRouter({ ...defaultProps, subtitle: "Last 7 days" });
      expect(screen.getByText("Last 7 days")).toBeInTheDocument();
    });

    it("renders icon when provided", () => {
      renderWithRouter({ ...defaultProps, icon: "📊" });
      expect(screen.getByText("📊")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = renderWithRouter({ ...defaultProps, className: "custom-class" });
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("number formatting", () => {
    it("formats number with commas when formatNumber is true", () => {
      renderWithRouter({ ...defaultProps, value: 1234567, formatNumber: true });
      expect(screen.getByText("1,234,567")).toBeInTheDocument();
    });

    it("uses compact format when compactFormat is true", () => {
      renderWithRouter({ ...defaultProps, value: 1500, compactFormat: true });
      expect(screen.getByText("1.5K")).toBeInTheDocument();
    });

    it("formats millions correctly", () => {
      renderWithRouter({ ...defaultProps, value: 2500000, compactFormat: true });
      expect(screen.getByText("2.5M")).toBeInTheDocument();
    });

    it("formats billions correctly", () => {
      renderWithRouter({ ...defaultProps, value: 1500000000, compactFormat: true });
      expect(screen.getByText("1.5B")).toBeInTheDocument();
    });
  });

  describe("variants", () => {
    it("applies primary variant classes", () => {
      const { container } = renderWithRouter({ ...defaultProps, variant: "primary" });
      expect(container.firstChild).toHaveClass("border-l-blue-500");
    });

    it("applies success variant classes", () => {
      const { container } = renderWithRouter({ ...defaultProps, variant: "success" });
      expect(container.firstChild).toHaveClass("border-l-green-500");
    });

    it("applies warning variant classes", () => {
      const { container } = renderWithRouter({ ...defaultProps, variant: "warning" });
      expect(container.firstChild).toHaveClass("border-l-yellow-500");
    });

    it("applies danger variant classes", () => {
      const { container } = renderWithRouter({ ...defaultProps, variant: "danger" });
      expect(container.firstChild).toHaveClass("border-l-red-500");
    });
  });

  describe("navigation", () => {
    it("renders as link when href is provided", () => {
      renderWithRouter({ ...defaultProps, href: "/images" });
      expect(screen.getByRole("link")).toHaveAttribute("href", "/images");
    });

    it("renders as button when onClick is provided", () => {
      const onClick = vi.fn();
      renderWithRouter({ ...defaultProps, onClick });
      expect(screen.getByRole("button")).toBeInTheDocument();
    });

    it("calls onClick when clicked", async () => {
      const onClick = vi.fn();
      renderWithRouter({ ...defaultProps, onClick });
      await userEvent.click(screen.getByRole("button"));
      expect(onClick).toHaveBeenCalled();
    });
  });

  describe("loading state", () => {
    it("shows loading skeleton when isLoading is true", () => {
      renderWithRouter({ ...defaultProps, isLoading: true });
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("hides value when loading", () => {
      renderWithRouter({ ...defaultProps, isLoading: true });
      expect(screen.queryByText("1234")).not.toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("shows error message when error is provided", () => {
      renderWithRouter({ ...defaultProps, error: "Failed to load" });
      expect(screen.getByText("Failed to load")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("uses aria-label when provided", () => {
      renderWithRouter({ ...defaultProps, ariaLabel: "Total number of images processed" });
      expect(screen.getByLabelText("Total number of images processed")).toBeInTheDocument();
    });
  });
});
