/**
 * CARTA Integration API
 *
 * Provides hooks for:
 * - Checking CARTA server availability
 * - Opening files in CARTA
 * - Managing CARTA sessions
 *
 * CARTA (Cube Analysis and Rendering Tool for Astronomy) is used for
 * advanced visualization of FITS images and measurement sets.
 *
 * Backend endpoints required:
 * - GET /api/v1/carta/status - Check if CARTA server is available
 * - POST /api/v1/carta/open - Open a file in CARTA
 * - GET /api/v1/carta/sessions - List active CARTA sessions
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "./client";

// ============================================================================
// Types
// ============================================================================

export interface CARTAStatus {
  available: boolean;
  version?: string;
  url?: string;
  sessions_active?: number;
  max_sessions?: number;
  message?: string;
}

export interface CARTASession {
  id: string;
  file_path: string;
  file_type: "ms" | "fits" | "image";
  created_at: string;
  last_activity: string;
  user?: string;
}

export interface CARTAOpenRequest {
  file_path: string;
  file_type?: "ms" | "fits" | "image";
  /** Whether to create a new session or reuse existing */
  new_session?: boolean;
}

export interface CARTAOpenResponse {
  success: boolean;
  session_id: string;
  viewer_url: string;
  message?: string;
}

// ============================================================================
// Query Keys
// ============================================================================

export const cartaKeys = {
  all: ["carta"] as const,
  status: () => [...cartaKeys.all, "status"] as const,
  sessions: () => [...cartaKeys.all, "sessions"] as const,
  session: (id: string) => [...cartaKeys.all, "session", id] as const,
};

// ============================================================================
// Hooks
// ============================================================================

/**
 * Check CARTA server availability
 */
export function useCARTAStatus() {
  return useQuery({
    queryKey: cartaKeys.status(),
    queryFn: async (): Promise<CARTAStatus> => {
      try {
        const response = await apiClient.get("/carta/status");
        return response.data;
      } catch (error) {
        // If endpoint doesn't exist (404) or network error, CARTA is unavailable
        return {
          available: false,
          message: "CARTA server is not available",
        };
      }
    },
    // Check status every 30 seconds
    refetchInterval: 30000,
    // Don't retry on failure - just mark as unavailable
    retry: false,
    // Keep stale data while refetching
    staleTime: 10000,
  });
}

/**
 * List active CARTA sessions
 */
export function useCARTASessions() {
  return useQuery({
    queryKey: cartaKeys.sessions(),
    queryFn: async (): Promise<CARTASession[]> => {
      const response = await apiClient.get("/carta/sessions");
      return response.data;
    },
    // Only fetch if CARTA might be available
    enabled: true,
    retry: 1,
  });
}

/**
 * Open a file in CARTA
 */
export function useOpenInCARTA() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      request: CARTAOpenRequest
    ): Promise<CARTAOpenResponse> => {
      const response = await apiClient.post("/carta/open", request);
      return response.data;
    },
    onSuccess: () => {
      // Refresh sessions list after opening a file
      queryClient.invalidateQueries({ queryKey: cartaKeys.sessions() });
    },
  });
}

/**
 * Close a CARTA session
 */
export function useCloseCARTASession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (sessionId: string): Promise<void> => {
      await apiClient.delete(`/carta/sessions/${sessionId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cartaKeys.sessions() });
    },
  });
}

/**
 * Get the CARTA viewer URL for a file
 * This constructs the URL client-side without requiring a backend call
 */
export function getCARTAViewerUrl(filePath: string, baseUrl?: string): string {
  const base = baseUrl ?? "/carta";
  const encodedPath = encodeURIComponent(filePath);
  return `${base}?file=${encodedPath}`;
}

/**
 * Hook to get CARTA viewer URL with status check
 */
export function useCARTAViewerUrl(filePath: string) {
  const { data: status, isLoading } = useCARTAStatus();

  return {
    url: status?.url
      ? `${status.url}?file=${encodeURIComponent(filePath)}`
      : getCARTAViewerUrl(filePath),
    isAvailable: status?.available ?? false,
    isLoading,
    status,
  };
}
