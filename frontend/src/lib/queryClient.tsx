import { QueryClient, QueryClientProvider, onlineManager } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import React from "react";

/**
 * TanStack Query client configuration with resilient offline handling.
 *
 * Default settings:
 * - staleTime: 30s - data considered fresh for 30 seconds
 * - gcTime: 5min - unused data garbage collected after 5 minutes
 * - retry: 3 - retry failed requests with exponential backoff
 * - retryDelay: exponential backoff with jitter
 * - refetchOnWindowFocus: true - refetch when user returns to tab
 * - refetchOnReconnect: true - refetch when network reconnects
 * - networkMode: 'offlineFirst' - use cache when offline
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      gcTime: 5 * 60 * 1000, // 5 minutes (formerly cacheTime)
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      // Use cached data when offline, refetch when back online
      networkMode: "offlineFirst",
    },
    mutations: {
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
      // Pause mutations when offline
      networkMode: "offlineFirst",
    },
  },
});

// Configure online status detection
// Uses navigator.onLine with fallback to periodic checks
onlineManager.setEventListener((setOnline) => {
  const handleOnline = () => setOnline(true);
  const handleOffline = () => setOnline(false);

  window.addEventListener("online", handleOnline);
  window.addEventListener("offline", handleOffline);

  return () => {
    window.removeEventListener("online", handleOnline);
    window.removeEventListener("offline", handleOffline);
  };
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
