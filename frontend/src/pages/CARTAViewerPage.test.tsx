/**
 * @vitest-environment jsdom
 */

import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import CARTAViewerPage from "./CARTAViewerPage";

// Mock the carta API module
vi.mock("../api/carta", () => ({
  useCARTAStatus: vi.fn(),
  useCARTASessions: vi.fn(() => ({ data: [], isLoading: false })),
  getCARTAViewerUrl: vi.fn(
    (filePath: string, baseUrl?: string) =>
      `${baseUrl || "/carta"}?file=${encodeURIComponent(filePath)}`
  ),
}));

// Mock the config module
vi.mock("../config", () => ({
  config: {
    carta: {
      baseUrl: "/carta",
    },
  },
}));

import { useCARTAStatus } from "../api/carta";

const mockUseCARTAStatus = vi.mocked(useCARTAStatus);

describe("CARTAViewerPage", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  const renderPage = (route = "/viewer/carta") => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>
          <Routes>
            <Route path="/viewer/carta" element={<CARTAViewerPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  describe("loading state", () => {
    it("shows loading message while checking CARTA status", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: undefined,
        isLoading: true,
        isSuccess: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta?ms=/data/test.ms");
      expect(
        screen.getByText(/checking carta availability/i)
      ).toBeInTheDocument();
    });
  });

  describe("no file specified", () => {
    it("shows no file state when no query params provided", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: true },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta");
      expect(
        screen.getByRole("heading", { name: /carta viewer/i })
      ).toBeInTheDocument();
      expect(
        screen.getByText(/advanced visualization for fits images/i)
      ).toBeInTheDocument();
    });

    it("provides link to browse images", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: true },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta");
      const browseLink = screen.getByRole("link", { name: /browse images/i });
      expect(browseLink).toBeInTheDocument();
      expect(browseLink).toHaveAttribute("href", "/images");
    });
  });

  describe("CARTA unavailable", () => {
    it("shows unavailable state when CARTA is not running", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: false, message: "CARTA server is not available" },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta?ms=/data/test.ms");
      expect(screen.getByText(/carta viewer unavailable/i)).toBeInTheDocument();
    });

    it("displays custom unavailable message from API", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: {
          available: false,
          message: "CARTA is undergoing maintenance",
        },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta?file=/data/test.fits");
      expect(
        screen.getByText(/carta is undergoing maintenance/i)
      ).toBeInTheDocument();
    });

    it("provides link to return to dashboard", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: false },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta?ms=/data/test.ms");
      const dashboardLink = screen.getByRole("link", {
        name: /return to dashboard/i,
      });
      expect(dashboardLink).toBeInTheDocument();
      expect(dashboardLink).toHaveAttribute("href", "/");
    });
  });

  describe("CARTA available", () => {
    it("renders viewer header with file path", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: true, version: "4.0.0" },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta?ms=/data/test.ms");
      expect(screen.getByText("CARTA Viewer")).toBeInTheDocument();
      expect(screen.getByText("/data/test.ms")).toBeInTheDocument();
    });

    it("displays CARTA version when available", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: true, version: "4.0.0" },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta?ms=/data/test.ms");
      expect(screen.getByText("v4.0.0")).toBeInTheDocument();
    });

    it("renders iframe with correct src for ?ms= parameter", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: true, url: "http://carta.local" },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta?ms=/data/2025-01-01.ms");
      const iframe = screen.getByTitle("CARTA Viewer");
      expect(iframe).toBeInTheDocument();
      expect(iframe.tagName).toBe("IFRAME");
    });

    it("renders iframe with correct src for ?file= parameter", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: true },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta?file=/data/image.fits");
      const iframe = screen.getByTitle("CARTA Viewer");
      expect(iframe).toBeInTheDocument();
    });

    it("provides open in new tab link", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: true },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta?ms=/data/test.ms");
      const newTabLink = screen.getByRole("link", {
        name: /open in new tab/i,
      });
      expect(newTabLink).toBeInTheDocument();
      expect(newTabLink).toHaveAttribute("target", "_blank");
      expect(newTabLink).toHaveAttribute("rel", "noopener noreferrer");
    });
  });

  describe("query parameter handling", () => {
    it("prefers ?ms= over ?file= when both provided", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: true },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      // When both are provided, ms should take precedence (first in || chain)
      renderPage("/viewer/carta?ms=/data/test.ms&file=/data/other.fits");
      expect(screen.getByText("/data/test.ms")).toBeInTheDocument();
    });

    it("falls back to ?file= when ?ms= not provided", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: true },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta?file=/data/image.fits");
      expect(screen.getByText("/data/image.fits")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("iframe has accessible title", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: true },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta?ms=/data/test.ms");
      const iframe = screen.getByTitle("CARTA Viewer");
      expect(iframe).toHaveAttribute("title", "CARTA Viewer");
    });

    it("has proper heading structure", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: true },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta?ms=/data/test.ms");
      expect(
        screen.getByRole("heading", { name: /carta viewer/i })
      ).toBeInTheDocument();
    });

    it("unavailable state has proper heading", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: false },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta?ms=/data/test.ms");
      expect(
        screen.getByRole("heading", { name: /carta viewer unavailable/i })
      ).toBeInTheDocument();
    });

    it("no file state has proper heading", () => {
      mockUseCARTAStatus.mockReturnValue({
        data: { available: true },
        isLoading: false,
        isSuccess: true,
        isError: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useCARTAStatus>);

      renderPage("/viewer/carta");
      expect(
        screen.getByRole("heading", { name: /carta viewer/i })
      ).toBeInTheDocument();
    });
  });
});
