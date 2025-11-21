/**
 * React Hook for JS9 Display Management
 *
 * Provides reactive access to JS9 display state
 */

import { useEffect, useState, useCallback } from "react";
import { findDisplay, isJS9Available, getDisplayImageId } from "../utils/js9";
import type { JS9Display } from "../types/js9";

interface UseJS9DisplayResult {
  display: JS9Display | null;
  imageId: string | null;
  isAvailable: boolean;
  refresh: () => void;
}

/**
 * Hook to access JS9 display state reactively
 *
 * @param displayId - The display ID to track
 * @returns Display state and refresh function
 */
export function useJS9Display(displayId: string): UseJS9DisplayResult {
  const [display, setDisplay] = useState<JS9Display | null>(null);
  const [imageId, setImageId] = useState<string | null>(null);
  const [isAvailable, setIsAvailable] = useState(false);

  const refresh = useCallback(() => {
    if (!isJS9Available()) {
      setIsAvailable(false);
      setDisplay(null);
      setImageId(null);
      return;
    }

    setIsAvailable(true);
    const foundDisplay = findDisplay(displayId);
    setDisplay(foundDisplay);
    setImageId(getDisplayImageId(displayId));
  }, [displayId]);

  // Initial check
  useEffect(() => {
    refresh();
  }, [refresh]);

  // Listen for JS9 events that might change display state
  useEffect(() => {
    if (!isJS9Available()) {
      return;
    }

    const handleImageChange = () => {
      refresh();
    };

    // Listen to events that indicate display state changed
    if (typeof window.JS9?.AddEventListener === "function") {
      window.JS9.AddEventListener("displayimage", handleImageChange);
      window.JS9.AddEventListener("imageLoad", handleImageChange);
      window.JS9.AddEventListener("imageDisplay", handleImageChange);
    }

    return () => {
      if (typeof window.JS9?.RemoveEventListener === "function") {
        window.JS9.RemoveEventListener("displayimage", handleImageChange);
        window.JS9.RemoveEventListener("imageLoad", handleImageChange);
        window.JS9.RemoveEventListener("imageDisplay", handleImageChange);
      }
    };
  }, [refresh]);

  return { display, imageId, isAvailable, refresh };
}
