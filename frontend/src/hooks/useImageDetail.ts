/**
 * Hook for image detail page logic.
 *
 * Centralizes image detail fetching, delete handling,
 * and recent item tracking.
 */

import { useState, useEffect, useCallback } from "react";
import { useImage } from "./useQueries";
import { usePreferencesStore } from "../stores/appStore";
import apiClient, { noRetry } from "../api/client";
import { ROUTES } from "../constants/routes";

/**
 * State for delete operation.
 */
interface DeleteState {
  isDeleting: boolean;
  error: string | null;
  showModal: boolean;
}

/**
 * Hook for image detail page logic.
 *
 * @param imageId Image ID from route params
 * @returns Image data, loading state, and action handlers
 *
 * @example
 * ```tsx
 * const {
 *   image,
 *   isLoading,
 *   error,
 *   refetch,
 *   deleteState,
 *   openDeleteModal,
 *   closeDeleteModal,
 *   confirmDelete,
 * } = useImageDetail(imageId);
 * ```
 */
export function useImageDetail(imageId: string | undefined) {
  // Fetch image data
  const queryResult = useImage(imageId);
  const { data: image, isLoading, error, refetch } = queryResult;

  // Recent items tracking
  const addRecentImage = usePreferencesStore((state) => state.addRecentImage);

  // Delete operation state
  const [deleteState, setDeleteState] = useState<DeleteState>({
    isDeleting: false,
    error: null,
    showModal: false,
  });

  // Track in recent items when image loads
  useEffect(() => {
    if (image && imageId) {
      addRecentImage(imageId);
    }
  }, [image, imageId, addRecentImage]);

  /**
   * Open the delete confirmation modal.
   */
  const openDeleteModal = useCallback(() => {
    setDeleteState((s) => ({ ...s, showModal: true, error: null }));
  }, []);

  /**
   * Close the delete confirmation modal.
   */
  const closeDeleteModal = useCallback(() => {
    setDeleteState((s) => ({ ...s, showModal: false }));
  }, []);

  /**
   * Confirm and execute the delete operation.
   */
  const confirmDelete = useCallback(async () => {
    if (!imageId) return;

    setDeleteState((s) => ({ ...s, isDeleting: true, error: null }));

    try {
      const encodedId = encodeURIComponent(imageId);
      await apiClient.delete(`/images/${encodedId}`, noRetry());
      // Navigate to images list after successful delete
      window.location.href = ROUTES.IMAGES.LIST;
    } catch (e) {
      const message = e instanceof Error ? e.message : "Failed to delete image";
      console.error("Failed to delete image:", e);
      setDeleteState((s) => ({ ...s, isDeleting: false, error: message }));
    }
  }, [imageId]);

  /**
   * Submit a rating for this image.
   */
  const submitRating = useCallback(
    async (rating: { confidence: "true" | "false" | "unsure"; tagId: string; notes: string }) => {
      if (!imageId) return;

      try {
        await apiClient.post(`/images/${imageId}/rating`, {
          itemId: imageId,
          ...rating,
        });
        // Refresh image data to show updated rating
        refetch();
      } catch (e) {
        console.error("Failed to submit rating:", e);
        throw e;
      }
    },
    [imageId, refetch]
  );

  return {
    // Query result
    image,
    isLoading,
    error,
    refetch,

    // Delete operation
    deleteState,
    openDeleteModal,
    closeDeleteModal,
    confirmDelete,

    // Rating
    submitRating,

    // Computed values
    encodedImageId: imageId ? encodeURIComponent(imageId) : "",
    filename: image?.path?.split("/").pop() || image?.id || "",
  };
}

export default useImageDetail;
