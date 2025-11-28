/**
 * useJS9Initialization Hook
 *
 * Handles JS9 display initialization, including:
 * - Waiting for JS9 library to load
 * - Creating and configuring JS9 display
 * - Setting up JS9 options and paths
 * - Handling initialization errors
 */

import { useEffect, useState } from "react";
import { logger } from "../../../utils/logger";
import { isJS9Available } from "../../../utils/js9";
import { useJS9Safe } from "../../../contexts/JS9Context";
import { js9Service } from "../../../services/js9";

interface UseJS9InitializationOptions {
  displayId: string;
  containerRef: React.RefObject<HTMLDivElement>;
  height: number;
  isJS9Ready: boolean;
  getDisplaySafe: (id: string) => any | null;
  js9Context: ReturnType<typeof useJS9Safe> | null;
}

export function useJS9Initialization({
  displayId,
  containerRef,
  height,
  isJS9Ready,
  getDisplaySafe,
  js9Context,
}: UseJS9InitializationOptions) {
  const [initialized, setInitialized] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Check if JS9 is fully loaded (js9.min.js must have finished loading)
    // window.JS9 exists before js9.min.js loads, so check for JS9.Load function
    if (isJS9Ready) {
      const existingDisplay = getDisplaySafe(displayId);
      if (existingDisplay) {
        logger.debug("JS9 display already exists for:", displayId);
        setInitialized(true);
        return;
      }

      // Disable JS9's internal loading indicator to avoid duplicate spinners
      try {
        // Disable JS9's internal loading indicator
        js9Service.setOptions({
          loadImage: false,
          resizeDisplay: true,
          autoResize: true,
        });
        // Hide JS9's loading indicator via CSS if it exists
        const js9LoadingElements = document.querySelectorAll(
          '.JS9Loading, .js9-loading, [class*="js9"][class*="load"]'
        );
        js9LoadingElements.forEach((el: any) => {
          if (el.style) {
            el.style.display = "none";
          }
        });
      } catch (e) {
        logger.debug("Could not disable JS9 loading indicator:", e);
      }
    }

    if (initialized) return;

    // Wait for JS9 to be available
    if (!window.JS9) {
      // JS9 might not be loaded yet, wait for js9.min.js to finish loading
      // Check for JS9.Load function, not just window.JS9 (which exists before js9.min.js loads)
      const checkJS9 = setInterval(() => {
        const ready = js9Context?.isJS9Ready ?? isJS9Available();
        if (ready) {
          clearInterval(checkJS9);
          // Check again if display exists
          const existingDisplay = getDisplaySafe(displayId);
          if (!existingDisplay) {
            initializeJS9();
          } else {
            setInitialized(true);
          }
        }
      }, 100);

      // Timeout after 10 seconds
      const timeout = setTimeout(() => {
        clearInterval(checkJS9);
        if (!js9Service.isAvailable()) {
          logger.error("JS9 failed to load after 10 seconds");
          setError("JS9 library failed to load. Please refresh the page.");
        }
      }, 10000);

      return () => {
        clearInterval(checkJS9);
        clearTimeout(timeout);
      };
    }

    initializeJS9();

    function initializeJS9() {
      try {
        if (!containerRef.current) return;

        // Ensure div has the correct ID for JS9
        if (containerRef.current.id !== displayId) {
          containerRef.current.id = displayId;
        }

        // Wait for div to have proper dimensions before initializing JS9
        const checkDimensions = setInterval(() => {
          if (containerRef.current) {
            const rect = containerRef.current.getBoundingClientRect();
            // Ensure div has minimum dimensions (at least 100px width, 100px height)
            if (rect.width >= 100 && rect.height >= 100) {
              clearInterval(checkDimensions);
              doInitialize();
            }
          }
        }, 100);

        // Timeout after 5 seconds
        const dimensionTimeout = setTimeout(() => {
          clearInterval(checkDimensions);
          // Try to initialize anyway
          doInitialize();
        }, 5000);

        function doInitialize() {
          if (!containerRef.current) return;

          // Ensure div has explicit dimensions
          const rect = containerRef.current.getBoundingClientRect();
          if (rect.width < 100) {
            containerRef.current.style.width = "100%";
            containerRef.current.style.minWidth = "400px";
          }
          if (rect.height < 100) {
            containerRef.current.style.height = `${height}px`;
          }

          // Configure JS9 paths to use local files (already configured in index.html)
          // Use the same paths as index.html to avoid conflicts
          const js9Base = "/js9";
          try {
            // Configure JS9 options using the safe setOptions method
            // Do NOT try to assign to JS9.InstallDir directly - it's read-only
            js9Service.setOptions({
              loadImage: false,
              helperType: "none",  // Disable helper to prevent socket.io connection attempts
              helperPort: 0,
              loadProxy: false,
              resizeDisplay: true,
              autoResize: true,
            });
            logger.debug("JS9 options configured successfully");
          } catch (configErr) {
            logger.debug("JS9 path configuration failed:", configErr);
          }

          // Initialize JS9 globally if needed (only once)
          try {
            js9Service.init({
              loadImage: false,
              resizeDisplay: true,
              autoResize: true,
            });
          } catch (initErr) {
            // JS9 may already be initialized, try to set options instead
            try {
              js9Service.setOptions({
                loadImage: false,
                resizeDisplay: true,
                autoResize: true,
              });
            } catch (optErr) {
              logger.debug("JS9 Init and SetOptions failed:", initErr, optErr);
            }
          }

          // Register the div with JS9 using AddDivs
          js9Service.addDivs(displayId);

          setInitialized(true);
        }

        // Cleanup dimension check timeout
        return () => {
          clearInterval(checkDimensions);
          clearTimeout(dimensionTimeout);
        };
      } catch (err) {
        logger.error("JS9 initialization error:", err);
        setError("Failed to initialize JS9 display");
      }
    }
  }, [displayId, height, isJS9Ready, getDisplaySafe, js9Context, initialized, containerRef]);

  return { initialized, error };
}
