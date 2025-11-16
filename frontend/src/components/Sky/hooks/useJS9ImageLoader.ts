/**
 * useJS9ImageLoader Hook
 *
 * Handles loading images into JS9 display, including:
 * - Loading images when path changes
 * - Managing loading and error states
 * - Hiding JS9's internal loading indicators
 * - Handling image load errors and retries
 */

import { useEffect, useState, useRef } from "react";
import { logger } from "../../../utils/logger";
import { findDisplay } from "../../../utils/js9";
// import { useJS9Safe } from "../../../contexts/JS9Context";
import { js9Service } from "../../../services/js9";
import { monitorPromiseChain } from "../../../utils/js9/promiseChunker";

interface UseJS9ImageLoaderOptions {
  imagePath: string | null;
  displayId: string;
  initialized: boolean;
  isJS9Ready: boolean;
  timeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  getDisplaySafe: (id: string) => any | null;
}

export function useJS9ImageLoader({
  imagePath,
  displayId,
  initialized,
  isJS9Ready,
  timeoutRef,
  getDisplaySafe,
}: UseJS9ImageLoaderOptions) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const imageLoadedRef = useRef(false);

  useEffect(() => {
    if (!imagePath || !initialized || !isJS9Ready) {
      // Reset state when imagePath is cleared
      if (!imagePath) {
        imageLoadedRef.current = false;
        setLoading(false);
        setError(null);
      }
      return;
    }

    setLoading(true);
    setError(null);
    imageLoadedRef.current = false;

    // Define variables outside try/catch so they're accessible everywhere
    let hideInterval: NodeJS.Timeout | null = null;
    let observer: MutationObserver | null = null;
    let targetDiv: HTMLElement | null = null;

    const hideJS9Loading = () => {
      // Try multiple selectors to catch JS9 loading indicators
      const selectors = [
        ".JS9Loading",
        ".js9-loading",
        '[class*="js9"][class*="load"]',
        '[id*="js9"][id*="load"]',
        '[class*="JS9"][class*="Load"]',
        'div[class*="spinner"]',
        'div[class*="loader"]',
        'div[class*="loading"]',
        '.JS9 div[style*="spinner"]',
        '.JS9 div[style*="loader"]',
        '.JS9 div[style*="loading"]',
      ];

      selectors.forEach((selector) => {
        try {
          const elements = document.querySelectorAll(selector);
          elements.forEach((el: any) => {
            if (el && el.style) {
              el.style.display = "none";
              el.style.visibility = "hidden";
              el.style.opacity = "0";
              el.style.pointerEvents = "none";
            }
          });
        } catch (e) {
          // Ignore selector errors
        }
      });

      // Also check inside the target div specifically - hide ANY element that might be a spinner
      if (targetDiv) {
        const allChildren = targetDiv.querySelectorAll("*");
        allChildren.forEach((el: any) => {
          if (el && el.style) {
            // Handle className properly - it can be a string, DOMTokenList, or SVGAnimatedString
            let className = "";
            if (typeof el.className === "string") {
              className = el.className;
            } else if (el.className && typeof el.className.toString === "function") {
              className = el.className.toString();
            } else if (el.className && el.className.baseVal) {
              className = el.className.baseVal;
            } else if (el.getAttribute && el.getAttribute("class")) {
              className = el.getAttribute("class") || "";
            }

            const id = (el.id || "").toString();
            const style = el.getAttribute("style") || "";
            const tagName = (el.tagName || "").toLowerCase();

            // Check if this looks like a loading indicator
            const classNameLower = className.toLowerCase();
            const isSpinner =
              classNameLower.includes("load") ||
              classNameLower.includes("spinner") ||
              classNameLower.includes("loader") ||
              id.toLowerCase().includes("load") ||
              id.toLowerCase().includes("spinner") ||
              style.toLowerCase().includes("spinner") ||
              style.toLowerCase().includes("loader") ||
              style.toLowerCase().includes("rotate") ||
              // Check for animated elements (common in spinners)
              (el.getAttribute &&
                el.getAttribute("class") &&
                el.getAttribute("class")?.includes("animate")) ||
              // Check for SVG spinners
              (tagName === "svg" && (classNameLower.includes("spin") || id.includes("spin"))) ||
              // Check for circular/rotating elements
              (style.includes("animation") && (style.includes("spin") || style.includes("rotate")));

            if (isSpinner) {
              el.style.display = "none";
              el.style.visibility = "hidden";
              el.style.opacity = "0";
              el.style.pointerEvents = "none";
            }
          }
        });

        // Also hide any direct children that are not the canvas (JS9 uses canvas for images)
        // If there's a div that's not a canvas and not our loading box, it might be JS9's spinner
        Array.from(targetDiv.children).forEach((child: any) => {
          if (child && child.tagName && child.tagName.toLowerCase() !== "canvas") {
            // Check if it's not our React loading box
            const isOurSpinner =
              child.querySelector && child.querySelector(".MuiCircularProgress-root");
            if (!isOurSpinner && child.style) {
              // This might be JS9's spinner - hide it
              const rect = child.getBoundingClientRect();
              // If it's a small element in the center, it's likely a spinner
              if (rect.width < 100 && rect.height < 100) {
                child.style.display = "none";
                child.style.visibility = "hidden";
                child.style.opacity = "0";
              }
            }
          }
        });
      }
    };

    // Cleanup interval and observer when loading completes
    const cleanupInterval = () => {
      if (hideInterval) {
        clearInterval(hideInterval);
        hideInterval = null;
      }
      if (observer) {
        observer.disconnect();
        observer = null;
      }
    };

    try {
      // Load image into JS9 display
      // Ensure the div exists and is visible before loading
      targetDiv = document.getElementById(displayId);
      if (!targetDiv) {
        setError(`Display div with id "${displayId}" not found`);
        setLoading(false);
        return;
      }

      // Hide immediately and set up interval to catch dynamically created elements
      hideJS9Loading();
      hideInterval = setInterval(hideJS9Loading, 50); // Check more frequently

      // Also use MutationObserver to catch elements as they're added
      observer = new MutationObserver(() => {
        hideJS9Loading();
      });

      if (targetDiv) {
        observer.observe(targetDiv, {
          childList: true,
          subtree: true,
          attributes: true,
          attributeFilter: ["class", "id", "style"],
        });
      }

      // Clear any existing image from the display before loading a new one
      const display = getDisplaySafe(displayId);

      if (display && display.im) {
        // Close the existing image to clear the display
        const oldImageId = display.im.id;
        js9Service.closeImage(oldImageId);
      }

      // Don't clear the div - JS9 manages its own DOM
      // Clearing can interfere with JS9's canvas rendering

      // Clear any existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }

      // Small delay to ensure cleanup completes before loading
      const loadTimeout = setTimeout(() => {
        // Double-check that imagePath hasn't changed (component might have unmounted or path changed)
        if (!imagePath || !window.JS9) {
          setLoading(false);
          return;
        }

        // Add a cache-busting parameter to ensure JS9 treats this as a new image
        // This prevents JS9 from using a cached version of a previously loaded image
        const cacheBuster = `?t=${Date.now()}`;
        const imageUrlWithCacheBuster = imagePath.includes("?")
          ? `${imagePath}&_cb=${Date.now()}`
          : `${imagePath}${cacheBuster}`;

        // Close any existing image in this display first
        const existingDisplay = findDisplay(displayId);

        if (existingDisplay && existingDisplay.im) {
          js9Service.closeImage(existingDisplay.im.id);
        }

        // JS9.Load with divID should automatically create a display in that div
        // Use a small delay after closing to ensure cleanup
        timeoutRef.current = setTimeout(() => {
          if (!imagePath || !js9Service.isAvailable()) {
            logger.error("JS9.Load not available when trying to load image");
            setError("JS9 library not fully loaded. Please refresh the page.");
            setLoading(false);
            return;
          }

          try {
            // Wrap JS9.Load in a Promise for monitoring
            const loadPromise = new Promise<void>((resolve, reject) => {
              js9Service.loadImage(imageUrlWithCacheBuster, {
                divID: displayId,
                scale: "linear",
                colormap: "grey",
                onload: (im: any) => {
                  logger.debug("FITS image loaded:", im, "Display:", displayId);
                  imageLoadedRef.current = true;
                  setLoading(false);
                  cleanupInterval();
                  hideJS9Loading();

                  // Restore page title (JS9 modifies it when loading images)
                  const originalTitle = document.title.split(":")[0].trim();
                  if (document.title !== originalTitle) {
                    document.title = originalTitle;
                  }

                  // Resize JS9 to fill container width after image loads
                  setTimeout(() => {
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
                      logger.warn("Failed to resize JS9 display after image load:", e);
                    }
                  }, 200);

                  // Force JS9 to display the image in the correct div
                  try {
                    js9Service.setDisplay(displayId, im.id);
                    // Verify the image is in the correct display
                    const display = getDisplaySafe(displayId);
                    if (display && display.im && display.im.id === im.id) {
                      logger.debug("Image confirmed in display:", displayId);
                    } else {
                      logger.debug(
                        "Image loaded but not in expected display, attempting to fix..."
                      );
                      js9Service.setDisplay(displayId, im.id);
                    }
                  } catch (e) {
                    logger.debug("Error verifying display:", e);
                  }
                  resolve();
                },
                onerror: (err: any) => {
                  logger.error("JS9 load error:", err);
                  setError(`Failed to load image: ${err.message || "Unknown error"}`);
                  setLoading(false);
                  imageLoadedRef.current = false;
                  cleanupInterval();
                  hideJS9Loading();
                  reject(err);
                },
              });
            });

            // Monitor the promise chain for performance issues
            monitorPromiseChain(
              loadPromise,
              `JS9.Load: ${displayId}`,
              100 // threshold in ms
            ).catch((err) => {
              // Error already handled in onerror callback
              logger.debug("JS9.Load promise rejected:", err);
            });
          } catch (loadErr: any) {
            // If divID doesn't work, try without specifying display
            logger.warn("JS9.Load with divID failed, trying without display parameter:", loadErr);
            try {
              if (!js9Service.isAvailable()) {
                throw new Error("JS9.Load not available");
              }
              // Wrap JS9.Load in a Promise for monitoring (fallback path)
              const loadPromise = new Promise<void>((resolve, reject) => {
                js9Service.loadImage(imageUrlWithCacheBuster, {
                  scale: "linear",
                  colormap: "grey",
                  onload: (im: any) => {
                    logger.debug("FITS image loaded (fallback):", im);
                    imageLoadedRef.current = true;
                    setLoading(false);

                    // Resize JS9 to fill container width after image loads
                    setTimeout(() => {
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
                        logger.warn("Failed to resize JS9 display after image load:", e);
                      }
                    }, 200);
                    cleanupInterval();
                    hideJS9Loading();

                    // Restore page title (JS9 modifies it when loading images)
                    const originalTitle = document.title.split(":")[0].trim();
                    if (document.title !== originalTitle) {
                      document.title = originalTitle;
                    }

                    // Try to move to correct display after loading
                    js9Service.setDisplay(displayId, im.id);
                    resolve();
                  },
                  onerror: (err: any) => {
                    logger.error("JS9 load error (fallback):", err);
                    setError(`Failed to load image: ${err.message || "Unknown error"}`);
                    setLoading(false);
                    imageLoadedRef.current = false;
                    cleanupInterval();
                    hideJS9Loading();
                    reject(err);
                  },
                });
              });

              // Monitor the promise chain for performance issues (fallback path)
              monitorPromiseChain(
                loadPromise,
                `JS9.Load (fallback): ${displayId}`,
                100 // threshold in ms
              ).catch((err) => {
                // Error already handled in onerror callback
                logger.debug("JS9.Load promise rejected (fallback):", err);
              });
            } catch (fallbackErr: any) {
              setError(`Failed to load image: ${fallbackErr.message || "Unknown error"}`);
              setLoading(false);
              imageLoadedRef.current = false;
              cleanupInterval();
              hideJS9Loading();
            }
          }
        }, 100); // Small delay after closing to ensure cleanup
      }, 50); // Small delay to ensure cleanup completes

      // Cleanup function to cancel timeout if imagePath changes or component unmounts
      return () => {
        clearTimeout(loadTimeout);
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        cleanupInterval();
        hideJS9Loading();
      };
    } catch (err: any) {
      logger.error("Error loading image:", err);
      setError(`Error: ${err.message || "Unknown error"}`);
      setLoading(false);
      imageLoadedRef.current = false;
      cleanupInterval();
      hideJS9Loading();
    }
  }, [imagePath, displayId, initialized, isJS9Ready, timeoutRef, getDisplaySafe]);

  return { loading, error, imageLoadedRef };
}
