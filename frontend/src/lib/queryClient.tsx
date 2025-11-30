import { QueryClient, QueryClientProvider, onlineManager } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import React from "react";
import { DEFAULT_RETRY_CONFIG } from "../api/client";

/**
 * Calculate retry delay with exponential backoff and jitter.
 * Aligned with apiClient resilience settings for consistent behavior.
 *
 * @param attemptIndex - Zero-based attempt index (0 = first retry)
 * @returns Delay in milliseconds
 */
function calculateRetryDelay(attemptIndex: number): number {
  const baseDelay = DEFAULT_RETRY_CONFIG.baseDelayMs;
  const maxDelay = DEFAULT_RETRY_CONFIG.maxDelayMs;
  const multiplier = DEFAULT_RETRY_CONFIG.backoffMultiplier;
  const jitter = DEFAULT_RETRY_CONFIG.jitterFactor;

  // Exponential backoff: baseDelay * multiplier^attempt
  const exponentialDelay = baseDelay * Math.pow(multiplier, attemptIndex);
  const clampedDelay = Math.min(exponentialDelay, maxDelay);

  // Add jitter to prevent thundering herd (synchronized retries)
  const jitterAmount = clampedDelay * jitter * Math.random();

  return Math.floor(clampedDelay + jitterAmount);
}

/**
 * Determine if a query should be retried based on error type.
 * Skip retries for certain errors that won't benefit from retrying.
 *
 * @param failureCount - Number of times the query has failed
 * @param error - The error that caused the failure
 * @returns Whether to retry the query
 */
function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  const maxRetries = DEFAULT_RETRY_CONFIG.maxRetries;

  // Don't retry beyond max attempts
  if (failureCount >= maxRetries) {
    return false;
  }

  // Check if error has a status code (axios or fetch error)
  const status = (error as { response?: { status?: number } })?.response?.status;

  if (status) {
    // Don't retry client errors (400-499) except rate limiting (429)
    if (status >= 400 && status < 500 && status !== 429) {
      return false;
    }
  }

  // Don't retry if it's an abort error
  if (error instanceof DOMException && error.name === "AbortError") {
    return false;
  }

  return true;
}

/**
 * TanStack Query client configuration with resilient offline handling.
 *
 * Default settings aligned with apiClient resilience:
 * - staleTime: 30s - data considered fresh for 30 seconds
 * - gcTime: 5min - unused data garbage collected after 5 minutes
 * - retry: 3 - retry failed requests (aligned with DEFAULT_RETRY_CONFIG)
 * - retryDelay: exponential backoff with jitter (aligned with apiClient)
 * - refetchOnWindowFocus: true - refetch when user returns to tab
 * - refetchOnReconnect: true - refetch when network reconnects
 * - networkMode: 'offlineFirst' - use cache when offline
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      gcTime: 5 * 60 * 1000, // 5 minutes (formerly cacheTime)
      retry: shouldRetryQuery,
      retryDelay: calculateRetryDelay,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      // Use cached data when offline, refetch when back online
      networkMode: "offlineFirst",
    },
    mutations: {
      // Fewer retries for mutations (they may have side effects)
      retry: (failureCount, error) => {
        // Only retry mutations twice, and only for network errors
        if (failureCount >= 2) return false;
        const status = (error as { response?: { status?: number } })?.response?.status;
        // Only retry on network errors or 5xx server errors
        return !status || status >= 500;
      },
      retryDelay: calculateRetryDelay,
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
