/**
 * useJS9ContentPreservation Hook
 *
 * Preserves JS9 content across React re-renders.
 * Detects when React clears JS9 content and restores it automatically.
 */

import { useEffect, useLayoutEffect } from "react";
import { logger } from "../../../utils/logger";
// import { useJS9Safe } from "../../../contexts/JS9Context";
import { js9Service } from "../../../services/js9";

interface UseJS9ContentPreservationOptions {
  displayId: string;
  containerRef: React.RefObject<HTMLDivElement>;
  initialized: boolean;
  isJS9Ready: boolean;
  imagePath: string | null;
  loading: boolean;
  imageLoadedRef: React.MutableRefObject<boolean>;
  getDisplaySafe: (id: string) => any | null;
}

export function useJS9ContentPreservation({
  displayId,
  containerRef,
  initialized,
  isJS9Ready,
  imagePath,
  loading,
  imageLoadedRef,
  getDisplaySafe,
}: UseJS9ContentPreservationOptions) {
  // Preserve JS9 content after React renders using useLayoutEffect
  // Only restore if we're not currently loading a new image
  useLayoutEffect(() => {
    if (!containerRef.current || !initialized || !isJS9Ready || !imageLoadedRef.current || loading)
      return;

    const div = containerRef.current;
    const display = getDisplaySafe(displayId);

    // If JS9 has an image loaded but the div is empty, restore it
    // Only restore if we have a valid image and we're not loading a new one
    if (display && display.im && div.children.length === 0 && imagePath) {
      logger.debug("Restoring JS9 display after React render");
      // Use requestAnimationFrame to ensure this happens after React's render
      requestAnimationFrame(() => {
        try {
          // Reload the image into the display using the current imagePath
          // This ensures we restore the correct image, not an old one
          if (imagePath && js9Service.isAvailable()) {
            js9Service.loadImage(imagePath, { divID: displayId });
          }
        } catch (e) {
          logger.debug("Failed to restore JS9 display:", e);
        }
      });
    }
  }, [
    displayId,
    initialized,
    isJS9Ready,
    loading,
    imagePath,
    imageLoadedRef,
    getDisplaySafe,
    containerRef,
  ]);

  // Monitor div for React clearing JS9 content and restore if needed
  useEffect(() => {
    if (!containerRef.current || !initialized || !js9Service.isAvailable()) return;

    const div = containerRef.current;

    const observer = new MutationObserver(() => {
      // If React cleared the content but JS9 has an image loaded, restore it
      // Only restore if we're not currently loading a new image
      if (
        div.children.length === 0 &&
        imageLoadedRef.current &&
        !loading &&
        js9Service.isAvailable() &&
        imagePath
      ) {
        const display = getDisplaySafe(displayId);
        if (display && display.im) {
          logger.debug("React cleared JS9 content, restoring...");
          // Force JS9 to redraw using the current imagePath to ensure we restore the correct image
          setTimeout(() => {
            try {
              if (imagePath && js9Service.isAvailable()) {
                js9Service.loadImage(imagePath, { divID: displayId });
              }
            } catch (e) {
              logger.debug("Failed to restore JS9 display:", e);
            }
          }, 100);
        }
      }
    });

    observer.observe(div, {
      childList: true,
      subtree: true,
      attributes: false,
    });

    return () => observer.disconnect();
  }, [displayId, initialized, loading, imagePath, imageLoadedRef, getDisplaySafe, containerRef]);
}
