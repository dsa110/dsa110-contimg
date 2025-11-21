/**
 * JS9 Context Provider
 *
 * Centralizes JS9 initialization state and provides display context to components.
 * Eliminates prop drilling of displayId and provides reactive JS9 state.
 */

import { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import type { ReactNode } from "react";
import { isJS9Available, findDisplay, getDisplayImageId } from "../utils/js9";
import type { JS9Display } from "../types/js9";

export interface DisplayState {
  displayId: string;
  imageId: string | null;
  imagePath: string | null;
  isLoading: boolean;
  hasImage: boolean;
}

interface JS9ContextValue {
  // JS9 availability
  isJS9Ready: boolean;
  isJS9Initializing: boolean;
  js9Error: string | null;

  // Display management
  getDisplay: (displayId: string) => JS9Display | null;
  getImageId: (displayId: string) => string | null;
  hasImage: (displayId: string) => boolean;

  // Display state management
  getDisplayState: (displayId: string) => DisplayState | null;
  getAllDisplays: () => DisplayState[];

  // Image loading
  loadImage: (displayId: string, imagePath: string) => Promise<void>;

  // Refresh display state
  refreshDisplay: (displayId: string) => void;
}

const JS9Context = createContext<JS9ContextValue | undefined>(undefined);

export function useJS9() {
  const context = useContext(JS9Context);
  if (!context) {
    throw new Error("useJS9 must be used within JS9Provider");
  }
  return context;
}

/**
 * Safe hook to use JS9 context - returns null if context not available
 * Useful for backward compatibility when migrating components
 */
export function useJS9Safe() {
  const context = useContext(JS9Context);
  return context ?? null;
}

interface JS9ProviderProps {
  children: ReactNode;
}

export function JS9Provider({ children }: JS9ProviderProps) {
  const [isJS9Ready, setIsJS9Ready] = useState(false);
  const [isJS9Initializing, setIsJS9Initializing] = useState(false);
  const [js9Error, setJs9Error] = useState<string | null>(null);

  // Track display states
  const [displayStates, setDisplayStates] = useState<Map<string, DisplayState>>(new Map());
  const loadingRefs = useRef<Map<string, boolean>>(new Map());

  // Initialize JS9 availability check
  useEffect(() => {
    if (isJS9Available()) {
      setIsJS9Ready(true);
      setIsJS9Initializing(false);
      return;
    }

    setIsJS9Initializing(true);
    setJs9Error(null);

    // Poll for JS9 availability (single point of initialization)
    const checkJS9 = setInterval(() => {
      if (isJS9Available()) {
        clearInterval(checkJS9);
        setIsJS9Ready(true);
        setIsJS9Initializing(false);
        setJs9Error(null);
      }
    }, 100);

    const timeout = setTimeout(() => {
      clearInterval(checkJS9);
      if (!isJS9Available()) {
        setIsJS9Initializing(false);
        setJs9Error("JS9 library failed to load. Please refresh the page.");
      }
    }, 10000);

    return () => {
      clearInterval(checkJS9);
      clearTimeout(timeout);
    };
  }, []);

  // Get display by ID
  const getDisplay = useCallback((displayId: string) => {
    if (!isJS9Available()) return null;
    return findDisplay(displayId);
  }, []);

  // Get image ID for a display
  const getImageId = useCallback((displayId: string) => {
    if (!isJS9Available()) return null;
    return getDisplayImageId(displayId);
  }, []);

  // Check if display has an image
  const hasImage = useCallback(
    (displayId: string) => {
      const display = getDisplay(displayId);
      return !!display?.im;
    },
    [getDisplay]
  );

  // Get display state
  const getDisplayState = useCallback(
    (displayId: string): DisplayState | null => {
      const state = displayStates.get(displayId);
      if (state) return state;

      // Create state from current display
      const _display = getDisplay(displayId);
      const imageId = getImageId(displayId);
      const hasImg = hasImage(displayId);

      return {
        displayId,
        imageId,
        imagePath: null, // Path not tracked yet
        isLoading: loadingRefs.current.get(displayId) ?? false,
        hasImage: hasImg,
      };
    },
    [displayStates, getDisplay, getImageId, hasImage]
  );

  // Get all display states
  const getAllDisplays = useCallback((): DisplayState[] => {
    if (!isJS9Available()) return [];

    const displays: DisplayState[] = [];
    if (window.JS9?.displays) {
      window.JS9.displays.forEach((display: any) => {
        const displayId = display.id || display.display || display.divID;
        if (displayId) {
          const state = getDisplayState(displayId);
          if (state) displays.push(state);
        }
      });
    }
    return displays;
  }, [getDisplayState]);

  // Update display state
  const updateDisplayState = useCallback(
    (displayId: string) => {
      const _display = getDisplay(displayId);
      const imageId = getImageId(displayId);
      const hasImg = hasImage(displayId);
      const isLoading = loadingRefs.current.get(displayId) ?? false;

      setDisplayStates((prev) => {
        const newMap = new Map(prev);
        const currentState = newMap.get(displayId);
        newMap.set(displayId, {
          displayId,
          imageId,
          imagePath: currentState?.imagePath ?? null,
          isLoading,
          hasImage: hasImg,
        });
        return newMap;
      });
    },
    [getDisplay, getImageId, hasImage]
  );

  // Load image into display
  const loadImage = useCallback(
    async (displayId: string, imagePath: string): Promise<void> => {
      if (!isJS9Available()) {
        throw new Error("JS9 is not available");
      }

      // Mark as loading
      loadingRefs.current.set(displayId, true);
      updateDisplayState(displayId);

      return new Promise((resolve, reject) => {
        try {
          const cacheBuster = `?t=${Date.now()}`;
          const imageUrlWithCacheBuster = imagePath.includes("?")
            ? `${imagePath}&_cb=${Date.now()}`
            : `${imagePath}${cacheBuster}`;

          window.JS9.Load(imageUrlWithCacheBuster, {
            divID: displayId,
            scale: "linear",
            colormap: "grey",
            onload: () => {
              loadingRefs.current.set(displayId, false);
              updateDisplayState(displayId);

              // Update image path in state
              setDisplayStates((prev) => {
                const newMap = new Map(prev);
                const currentState = newMap.get(displayId);
                if (currentState) {
                  newMap.set(displayId, {
                    ...currentState,
                    imagePath,
                    isLoading: false,
                    hasImage: true,
                  });
                }
                return newMap;
              });

              resolve();
            },
            onerror: (err: any) => {
              loadingRefs.current.set(displayId, false);
              updateDisplayState(displayId);
              reject(new Error(`Failed to load image: ${err?.message || "Unknown error"}`));
            },
          });
        } catch (err: any) {
          loadingRefs.current.set(displayId, false);
          updateDisplayState(displayId);
          reject(new Error(`JS9.Load failed: ${err?.message || "Unknown error"}`));
        }
      });
    },
    [updateDisplayState]
  );

  // Refresh display state (for components that need to force refresh)
  const refreshDisplay = useCallback(
    (displayId: string) => {
      updateDisplayState(displayId);
    },
    [updateDisplayState]
  );

  // Listen for JS9 events to update display states
  useEffect(() => {
    if (!isJS9Ready) return;

    const handleImageLoad = () => {
      // Update all display states when an image loads
      if (window.JS9?.displays) {
        window.JS9.displays.forEach((display: any) => {
          const displayId = display.id || display.display || display.divID;
          if (displayId) {
            updateDisplayState(displayId);
          }
        });
      }
    };

    const handleImageDisplay = () => {
      // Update all display states when an image is displayed
      if (window.JS9?.displays) {
        window.JS9.displays.forEach((display: any) => {
          const displayId = display.id || display.display || display.divID;
          if (displayId) {
            updateDisplayState(displayId);
          }
        });
      }
    };

    if (typeof window.JS9?.AddEventListener === "function") {
      window.JS9.AddEventListener("imageLoad", handleImageLoad);
      window.JS9.AddEventListener("imageDisplay", handleImageDisplay);
    }

    return () => {
      if (typeof window.JS9?.RemoveEventListener === "function") {
        window.JS9.RemoveEventListener("imageLoad", handleImageLoad);
        window.JS9.RemoveEventListener("imageDisplay", handleImageDisplay);
      }
    };
  }, [isJS9Ready, updateDisplayState]);

  const value: JS9ContextValue = {
    isJS9Ready,
    isJS9Initializing,
    js9Error,
    getDisplay,
    getImageId,
    hasImage,
    getDisplayState,
    getAllDisplays,
    loadImage,
    refreshDisplay,
  };

  return <JS9Context.Provider value={value}>{children}</JS9Context.Provider>;
}
