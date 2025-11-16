/**
 * useJS9Resize Hook
 *
 * Handles window and container resize events for JS9 display.
 * Ensures JS9 display fills container width and maintains aspect ratio.
 */

import { useEffect, useRef } from "react";
import { logger } from "../../../utils/logger";
// import { useJS9Safe } from "../../../contexts/JS9Context";

declare global {
  interface Window {
    JS9: any;
  }
}

interface UseJS9ResizeOptions {
  displayId: string;
  containerRef: React.RefObject<HTMLDivElement>;
  initialized: boolean;
  isJS9Ready: boolean;
  getDisplaySafe: (id: string) => any | null;
}

export function useJS9Resize({
  displayId,
  containerRef,
  initialized,
  isJS9Ready,
  getDisplaySafe,
}: UseJS9ResizeOptions) {
  const resizeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!initialized || !isJS9Ready) return;

    const handleResize = () => {
      if (!containerRef.current || !isJS9Ready) return;

      const display = getDisplaySafe(displayId);

      if (display) {
        try {
          // Small delay to ensure container has updated dimensions
          if (resizeTimeoutRef.current) {
            clearTimeout(resizeTimeoutRef.current);
          }

          resizeTimeoutRef.current = setTimeout(() => {
            try {
              const container = document.getElementById(displayId);
              if (container) {
                js9Service.resizeDisplay(displayId);
                // Force canvas to match container width
                const canvas = container.querySelector("canvas");
                if (canvas && canvas.style) {
                  canvas.style.width = "100%";
                  canvas.style.maxWidth = "100%";
                }
              }
            } catch (e) {
              logger.debug("Error resizing JS9 display:", e);
            }
          }, 100);
        } catch (e) {
          logger.debug("Error in resize handler:", e);
        }
      }
    };

    const ensureCanvasWidth = () => {
      const container = document.getElementById(displayId);
      if (container) {
        const canvas = container.querySelector("canvas");
        if (canvas && canvas.style) {
          canvas.style.width = "100%";
          canvas.style.maxWidth = "100%";
        }
      }
    };

    // Use ResizeObserver for container size changes
    let resizeObserver: ResizeObserver | null = null;
    if (containerRef.current && typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(() => {
        handleResize();
        ensureCanvasWidth();
      });
      resizeObserver.observe(containerRef.current);
    }

    // Watch for canvas elements being added/updated
    const container = containerRef.current;
    let canvasObserver: MutationObserver | null = null;
    if (container) {
      canvasObserver = new MutationObserver(() => {
        ensureCanvasWidth();
      });
      canvasObserver.observe(container, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["style", "width", "height"],
      });
    }

    // Also listen to window resize events
    window.addEventListener("resize", handleResize);

    // Initial resize
    handleResize();

    return () => {
      if (resizeTimeoutRef.current) {
        clearTimeout(resizeTimeoutRef.current);
      }
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      if (canvasObserver) {
        canvasObserver.disconnect();
      }
      window.removeEventListener("resize", handleResize);
    };
  }, [displayId, initialized, isJS9Ready, containerRef, getDisplaySafe]);
}
