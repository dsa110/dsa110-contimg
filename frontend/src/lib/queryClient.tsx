import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import React from "react";

/**
 * TanStack Query client configuration.
 *
 * Default settings:
 * - staleTime: 30s - data considered fresh for 30 seconds
 * - gcTime: 5min - unused data garbage collected after 5 minutes
 * - retry: 2 - retry failed requests twice
 * - refetchOnWindowFocus: true - refetch when user returns to tab
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      gcTime: 5 * 60 * 1000, // 5 minutes (formerly cacheTime)
      retry: 2,
      refetchOnWindowFocus: true,
    },
  },
});

interface QueryProviderProps {
  children: React.ReactNode;
}

/**
 * Wraps the app with TanStack Query provider and devtools.
 */
export const QueryProvider: React.FC<QueryProviderProps> = ({ children }) => {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {/* Devtools only shown in development */}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
};
