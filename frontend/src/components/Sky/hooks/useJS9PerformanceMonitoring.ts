/**
 * useJS9PerformanceMonitoring Hook
 *
 * Provides performance monitoring for JS9 operations.
 * Automatically tracks slow operations and setTimeout handlers.
 */

import { useEffect, useRef } from "react";
import { js9PerformanceProfiler } from "../../../utils/js9/performanceProfiler";
import { js9PromisePatcher } from "../../../utils/js9/js9PromisePatcher";

interface UseJS9PerformanceMonitoringOptions {
  enabled?: boolean;
  slowThresholdMs?: number;
  onSlowOperation?: (entry: {
    operation: string;
    duration: number;
    details?: Record<string, any>;
  }) => void;
  autoLog?: boolean;
}

export function useJS9PerformanceMonitoring(options: UseJS9PerformanceMonitoringOptions = {}) {
  const {
    enabled = process.env.NODE_ENV === "development",
    slowThresholdMs = 50,
    onSlowOperation,
    autoLog = true,
  } = options;

  const onSlowOperationRef = useRef(onSlowOperation);
  onSlowOperationRef.current = onSlowOperation;
  const patchedByHookRef = useRef(false);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    // Start monitoring
    js9PerformanceProfiler.startMonitoring();

    // Patch setTimeout to optimize JS9 promise resolution
    // Only patch if not already patched (e.g., by initPatcher)
    if (!js9PromisePatcher.getPatched()) {
      js9PromisePatcher.patch();
      patchedByHookRef.current = true;
    } else {
      patchedByHookRef.current = false;
    }

    // Set up interval to check for slow operations
    const checkInterval = setInterval(() => {
      const slowOps = js9PerformanceProfiler.getSlowOperations(slowThresholdMs);

      if (slowOps.length > 0 && onSlowOperationRef.current) {
        slowOps.forEach((entry) => {
          onSlowOperationRef.current?.({
            operation: entry.operation,
            duration: entry.duration,
            details: entry.details,
          });
        });
      }

      if (autoLog && slowOps.length > 0) {
        const summary = js9PerformanceProfiler.getSummary();
        if (summary.slowOperations > 0) {
          console.group("[JS9 Performance] Slow Operations Detected");
          console.table(
            slowOps.map((e) => ({
              Operation: e.operation,
              Duration: `${e.duration.toFixed(2)}ms`,
              Timestamp: new Date(e.timestamp).toLocaleTimeString(),
            }))
          );
          console.log("Summary:", summary);
          console.groupEnd();
        }
      }
    }, 5000); // Check every 5 seconds

    return () => {
      clearInterval(checkInterval);
      js9PerformanceProfiler.stopMonitoring();
      // Only unpatch if we patched it ourselves (not if it was patched by initPatcher)
      if (patchedByHookRef.current && js9PromisePatcher.getPatched()) {
        js9PromisePatcher.unpatch();
        patchedByHookRef.current = false;
      }
    };
  }, [enabled, slowThresholdMs, autoLog]);

  return {
    profiler: js9PerformanceProfiler,
    getSummary: () => js9PerformanceProfiler.getSummary(),
    getSlowOperations: (threshold?: number) =>
      js9PerformanceProfiler.getSlowOperations(threshold || slowThresholdMs),
    export: () => js9PerformanceProfiler.export(),
    clear: () => js9PerformanceProfiler.clear(),
  };
}
