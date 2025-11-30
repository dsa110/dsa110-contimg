import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import NotFoundPage from "./NotFoundPage";

describe("NotFoundPage", () => {
  const renderPage = () => {
    return render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>
    );
  };

  describe("content", () => {
    it("renders 404 heading", () => {
      renderPage();
      expect(screen.getByText("404")).toBeInTheDocument();
    });

    it("renders Page Not Found message", () => {
      renderPage();
      expect(screen.getByText("Page Not Found")).toBeInTheDocument();
    });

    it("renders helpful description", () => {
      renderPage();
      expect(
        screen.getByText(/page you.*looking for.*doesn't exist|has been moved/i)
      ).toBeInTheDocument();
    });
  });

  describe("navigation", () => {
    it("renders link to home page", () => {
      renderPage();
      const homeLink = screen.getByRole("link", { name: /home/i });
      expect(homeLink).toBeInTheDocument();
      expect(homeLink).toHaveAttribute("href", "/");
    });

    it("link has button styling", () => {
      renderPage();
      const homeLink = screen.getByRole("link", { name: /home/i });
      expect(homeLink).toHaveClass("btn");
    });
  });

  describe("styling", () => {
    it("centers content vertically and horizontally", () => {
      const { container } = renderPage();
      const wrapper = container.firstChild;
      expect(wrapper).toHaveClass("flex", "flex-col", "items-center", "justify-center");
    });

    it("has padding for spacing", () => {
      const { container } = renderPage();
      const wrapper = container.firstChild;
      expect(wrapper).toHaveClass("py-20");
    });

    it("404 text is large and styled", () => {
      renderPage();
      const heading = screen.getByText("404");
      expect(heading).toHaveClass("text-8xl", "font-bold");
    });
  });
});
