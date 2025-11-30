import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import StatCardGrid, { StatCardGridProps } from "./StatCardGrid";

const renderWithRouter = (props: StatCardGridProps) => {
  return render(
    <MemoryRouter>
      <StatCardGrid {...props} />
    </MemoryRouter>
  );
};

describe("StatCardGrid", () => {
  const mockCards = [
    { label: "Images", value: 100 },
    { label: "Sources", value: 500 },
    { label: "Jobs", value: 50 },
    { label: "Candidates", value: 25 },
  ];

  describe("rendering", () => {
    it("renders all cards", () => {
      renderWithRouter({ cards: mockCards });
      expect(screen.getByText("Images")).toBeInTheDocument();
      expect(screen.getByText("Sources")).toBeInTheDocument();
      expect(screen.getByText("Jobs")).toBeInTheDocument();
      expect(screen.getByText("Candidates")).toBeInTheDocument();
    });

    it("renders card values", () => {
      renderWithRouter({ cards: mockCards });
      expect(screen.getByText("100")).toBeInTheDocument();
      expect(screen.getByText("500")).toBeInTheDocument();
      expect(screen.getByText("50")).toBeInTheDocument();
      expect(screen.getByText("25")).toBeInTheDocument();
    });
  });

  describe("column layouts", () => {
    it("applies 2-column grid classes", () => {
      const { container } = renderWithRouter({ cards: mockCards, columns: 2 });
      expect(container.firstChild).toHaveClass("sm:grid-cols-2");
    });

    it("applies 3-column grid classes", () => {
      const { container } = renderWithRouter({ cards: mockCards, columns: 3 });
      expect(container.firstChild).toHaveClass("lg:grid-cols-3");
    });

    it("applies 4-column grid classes by default", () => {
      const { container } = renderWithRouter({ cards: mockCards });
      expect(container.firstChild).toHaveClass("lg:grid-cols-4");
    });
  });

  describe("loading state", () => {
    it("passes isLoading to all cards", () => {
      renderWithRouter({ cards: mockCards, isLoading: true });
      const loadingIndicators = screen.getAllByRole("status");
      expect(loadingIndicators.length).toBe(4);
    });
  });

  describe("custom className", () => {
    it("applies custom className", () => {
      const { container } = renderWithRouter({ cards: mockCards, className: "custom-class" });
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("empty state", () => {
    it("renders empty grid when no cards provided", () => {
      const { container } = renderWithRouter({ cards: [] });
      expect(container.firstChild).toBeEmptyDOMElement();
    });
  });
});
