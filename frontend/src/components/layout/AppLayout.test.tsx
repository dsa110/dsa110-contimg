import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AppLayout from "./AppLayout";

// Create a test QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

// Helper to render with router and query client
const renderWithRouter = (path = "/") => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<div>Home Content</div>} />
            <Route path="images" element={<div>Images Content</div>} />
            <Route path="sources" element={<div>Sources Content</div>} />
            <Route path="jobs" element={<div>Jobs Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe("AppLayout", () => {
  describe("header", () => {
    it("renders application title link", () => {
      renderWithRouter();
      const title = screen.getByRole("link", { name: /dsa-110 pipeline/i });
      expect(title).toBeInTheDocument();
      expect(title).toHaveAttribute("href", "/");
    });

    it("renders all navigation links", () => {
      renderWithRouter();
      expect(screen.getByRole("link", { name: "Home" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Images" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Sources" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Jobs" })).toBeInTheDocument();
    });

    it("has correct href for navigation links", () => {
      renderWithRouter();
      expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("href", "/");
      expect(screen.getByRole("link", { name: "Images" })).toHaveAttribute("href", "/images");
      expect(screen.getByRole("link", { name: "Sources" })).toHaveAttribute("href", "/sources");
      expect(screen.getByRole("link", { name: "Jobs" })).toHaveAttribute("href", "/jobs");
    });
  });

  describe("active navigation styling", () => {
    it("highlights Home when at root", () => {
      renderWithRouter("/");
      const homeLink = screen.getByRole("link", { name: "Home" });
      expect(homeLink).toHaveClass("bg-slate-700");
    });

    it("highlights Images when on images path", () => {
      renderWithRouter("/images");
      const imagesLink = screen.getByRole("link", { name: "Images" });
      expect(imagesLink).toHaveClass("bg-slate-700");
    });

    it("highlights Sources when on sources path", () => {
      renderWithRouter("/sources");
      const sourcesLink = screen.getByRole("link", { name: "Sources" });
      expect(sourcesLink).toHaveClass("bg-slate-700");
    });

    it("highlights Jobs when on jobs path", () => {
      renderWithRouter("/jobs");
      const jobsLink = screen.getByRole("link", { name: "Jobs" });
      expect(jobsLink).toHaveClass("bg-slate-700");
    });
  });

  describe("content outlet", () => {
    it("renders Home content at root", () => {
      renderWithRouter("/");
      expect(screen.getByText("Home Content")).toBeInTheDocument();
    });

    it("renders Images content at /images", () => {
      renderWithRouter("/images");
      expect(screen.getByText("Images Content")).toBeInTheDocument();
    });

    it("renders Sources content at /sources", () => {
      renderWithRouter("/sources");
      expect(screen.getByText("Sources Content")).toBeInTheDocument();
    });

    it("renders Jobs content at /jobs", () => {
      renderWithRouter("/jobs");
      expect(screen.getByText("Jobs Content")).toBeInTheDocument();
    });
  });

  describe("footer", () => {
    it("renders footer text", () => {
      renderWithRouter();
      expect(screen.getByText(/deep synoptic array/i)).toBeInTheDocument();
    });
  });

  describe("layout structure", () => {
    it("has header, main, and footer elements", () => {
      renderWithRouter();
      expect(document.querySelector("header")).toBeInTheDocument();
      expect(document.querySelector("main")).toBeInTheDocument();
      expect(document.querySelector("footer")).toBeInTheDocument();
    });
  });
});
