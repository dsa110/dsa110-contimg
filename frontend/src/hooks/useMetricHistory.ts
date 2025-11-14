import { useState, useEffect, useRef } from "react";

interface MetricHistoryEntry {
  timestamp: number;
  value: number;
}

interface UseMetricHistoryOptions {
  maxEntries?: number;
  enabled?: boolean;
}

/**
 * Hook to track metric history over time for sparkline visualization
 * @param currentValue - Current metric value
 * @param options - Configuration options
 * @returns Array of historical values for sparkline
 */
export function useMetricHistory(
  currentValue: number | undefined,
  options: UseMetricHistoryOptions = {}
): number[] {
  const { maxEntries = 50, enabled = true } = options;
  const [history, setHistory] = useState<MetricHistoryEntry[]>([]);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastValueRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (!enabled || currentValue === undefined) {
      return;
    }

    // Only add to history if value has changed or enough time has passed
    const now = Date.now();
    const shouldAdd =
      currentValue !== lastValueRef.current ||
      history.length === 0 ||
      (history.length > 0 && now - history[history.length - 1].timestamp > 5000); // 5 second minimum interval

    if (shouldAdd) {
      setHistory((prev) => {
        const newHistory = [...prev, { timestamp: now, value: currentValue }].slice(-maxEntries); // Keep only last N entries
        return newHistory;
      });
      lastValueRef.current = currentValue;
    }
  }, [currentValue, enabled, maxEntries, history.length]);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Return just the values for sparkline
  return history.map((entry) => entry.value);
}
