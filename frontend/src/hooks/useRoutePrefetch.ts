import { useCallback } from "react";

/**
 * Hook for prefetching lazy-loaded components
 * Preloads component modules on hover to improve perceived performance
 */
export function useRoutePrefetch() {
  const prefetchComponent = useCallback(
    (lazyComponent: () => Promise<{ default: React.ComponentType }>) => {
      // Preload the lazy component module
      // This triggers the import() call, loading the chunk in the background
      lazyComponent().catch(() => {
        // Silently handle errors (component may already be loading)
      });
    },
    []
  );

  return { prefetchComponent };
}
