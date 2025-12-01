/**
 * Shared Storybook decorators for consistent story rendering.
 */
import React from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AppLayout from "../src/components/layout/AppLayout";

/**
 * Create a fresh QueryClient for stories.
 */
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
        gcTime: Infinity,
      },
    },
  });
}

/**
 * Basic decorator with React Query provider.
 */
export const withQueryClient = (Story: React.ComponentType) => {
  const queryClient = createQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <Story />
    </QueryClientProvider>
  );
};

/**
 * Decorator with routing support.
 */
export const withRouter =
  (initialPath = "/") =>
  (Story: React.ComponentType) => {
    return (
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="*" element={<Story />} />
        </Routes>
      </MemoryRouter>
    );
  };

/**
 * Full app decorator with layout, routing, and query client.
 */
export const withAppLayout =
  (initialPath = "/") =>
  (Story: React.ComponentType) => {
    const queryClient = createQueryClient();
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[initialPath]}>
          <Routes>
            <Route path="*" element={<AppLayout />}>
              <Route index element={<Story />} />
              <Route path="*" element={<Story />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

/**
 * Dark theme wrapper for testing dark mode.
 */
export const withDarkTheme = (Story: React.ComponentType) => {
  return (
    <div className="dark bg-gray-900 min-h-screen p-4">
      <Story />
    </div>
  );
};

/**
 * Card container for component isolation.
 */
export const withCard = (title?: string) => (Story: React.ComponentType) => {
  return (
    <div className="bg-white rounded-lg shadow-md p-4 max-w-2xl">
      {title && <h3 className="text-lg font-semibold mb-3">{title}</h3>}
      <Story />
    </div>
  );
};

/**
 * Mock JS9 global for components that depend on it.
 */
export function mockJS9() {
  if (typeof window !== "undefined" && !window.JS9) {
    (window as any).JS9 = {
      Load: () => Promise.resolve(),
      GetImage: () => null,
      SetColormap: () => {},
      SetScale: () => {},
      SetZoom: () => {},
      Pan: () => {},
      GetRegions: () => [],
      AddRegions: () => {},
      RemoveRegions: () => {},
      ChangeRegions: () => {},
      regions2String: () => "",
      _regions: [],
    };
  }
}
