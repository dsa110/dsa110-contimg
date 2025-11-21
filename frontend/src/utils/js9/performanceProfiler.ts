/**
 * JS9 Performance Profiler
 *
 * Monitors JS9 operations to identify slow promise chains and setTimeout handlers
 * that exceed performance thresholds.
 */

interface PerformanceEntry {
  operation: string;
  duration: number;
  timestamp: number;
  stack?: string;
  details?: Record<string, any>;
}

class JS9PerformanceProfiler {
  private entries: PerformanceEntry[] = [];
  private readonly MAX_ENTRIES = 100;
  private readonly SLOW_THRESHOLD_MS = 50; // Flag operations taking >50ms
  private originalSetTimeout: typeof setTimeout;
  private isMonitoring = false;

  constructor() {
    this.originalSetTimeout = window.setTimeout;
  }

  /**
   * Start monitoring JS9 operations and setTimeout handlers
   */
  startMonitoring(): void {
    if (this.isMonitoring) {
      console.warn("JS9 Performance Profiler is already monitoring");
      return;
    }

    this.isMonitoring = true;
    this.entries = [];

    // Patch setTimeout to monitor long-running handlers
    const self = this;
    (window.setTimeout as any) = function (
      handler: TimerHandler,
      timeout?: number,
      ...args: any[]
    ): number {
      if (typeof handler === "function") {
        const wrappedHandler = self.wrapHandler(handler);
        return self.originalSetTimeout.call(window, wrappedHandler, timeout, ...args);
      }
      return self.originalSetTimeout.call(window, handler, timeout, ...args);
    };

    // Monitor JS9.Load calls
    this.monitorJS9Load();

    console.log("JS9 Performance Profiler started");
  }

  /**
   * Stop monitoring and restore original functions
   */
  stopMonitoring(): void {
    if (!this.isMonitoring) {
      return;
    }

    this.isMonitoring = false;
    window.setTimeout = this.originalSetTimeout;
    this.restoreJS9Load();

    console.log("JS9 Performance Profiler stopped");
  }

  /**
   * Wrap setTimeout handler to measure execution time
   */
  private wrapHandler(handler: Function): Function {
    const self = this;
    return function (this: any, ...args: any[]) {
      const startTime = performance.now();
      const stack = new Error().stack;

      try {
        const result = handler.apply(this, args);
        const duration = performance.now() - startTime;

        if (duration > self.SLOW_THRESHOLD_MS) {
          self.recordEntry({
            operation: "setTimeout handler",
            duration,
            timestamp: Date.now(),
            stack: stack?.split("\n").slice(0, 5).join("\n"),
            details: {
              handlerName: handler.name || "anonymous",
              argsCount: args.length,
            },
          });
        }

        return result;
      } catch (error) {
        const duration = performance.now() - startTime;
        self.recordEntry({
          operation: "setTimeout handler (error)",
          duration,
          timestamp: Date.now(),
          stack: stack?.split("\n").slice(0, 5).join("\n"),
          details: {
            error: String(error),
            handlerName: handler.name || "anonymous",
          },
        });
        throw error;
      }
    };
  }

  /**
   * Monitor JS9.Load calls
   */
  private monitorJS9Load(): void {
    if (typeof window === "undefined" || !window.JS9) {
      // Retry when JS9 is available
      setTimeout(() => this.monitorJS9Load(), 100);
      return;
    }

    const originalLoad = window.JS9.Load;
    if (!originalLoad) {
      return;
    }

    const self = this;
    window.JS9.Load = function (this: any, ...args: any[]) {
      const startTime = performance.now();
      const imagePath = args[0];
      const options = args[1] || {};

      try {
        const result = originalLoad.apply(this, args);
        const duration = performance.now() - startTime;

        self.recordEntry({
          operation: "JS9.Load",
          duration,
          timestamp: Date.now(),
          details: {
            imagePath:
              typeof imagePath === "string" ? imagePath.substring(0, 100) : String(imagePath),
            displayId: options.divID || options.display || "default",
            hasOnload: !!options.onload,
            hasOnerror: !!options.onerror,
          },
        });

        return result;
      } catch (error) {
        const duration = performance.now() - startTime;
        self.recordEntry({
          operation: "JS9.Load (error)",
          duration,
          timestamp: Date.now(),
          details: {
            error: String(error),
            imagePath:
              typeof imagePath === "string" ? imagePath.substring(0, 100) : String(imagePath),
          },
        });
        throw error;
      }
    };
  }

  /**
   * Restore original JS9.Load
   */
  private restoreJS9Load(): void {
    // Note: This is a simplified restore - in practice, you'd need to track
    // the original function more carefully
    if (typeof window !== "undefined" && window.JS9 && window.JS9.Load) {
      // The original would need to be stored when patching
      console.warn("JS9.Load restore not fully implemented - page refresh required");
    }
  }

  /**
   * Record a performance entry
   */
  private recordEntry(entry: PerformanceEntry): void {
    this.entries.push(entry);

    // Keep only the most recent entries
    if (this.entries.length > this.MAX_ENTRIES) {
      this.entries.shift();
    }

    // Log slow operations to console
    if (entry.duration > 100) {
      console.warn(
        `[JS9 Performance] Slow operation detected: ${entry.operation} took ${entry.duration.toFixed(2)}ms`,
        entry.details
      );
    }
  }

  /**
   * Get all performance entries
   */
  getEntries(): PerformanceEntry[] {
    return [...this.entries];
  }

  /**
   * Get slow operations (exceeding threshold)
   */
  getSlowOperations(threshold?: number): PerformanceEntry[] {
    const limit = threshold || this.SLOW_THRESHOLD_MS;
    return this.entries.filter((entry) => entry.duration > limit);
  }

  /**
   * Get summary statistics
   */
  getSummary(): {
    totalOperations: number;
    slowOperations: number;
    averageDuration: number;
    maxDuration: number;
    operationsByType: Record<string, { count: number; avgDuration: number }>;
  } {
    const slowOps = this.getSlowOperations();
    const durations = this.entries.map((e) => e.duration);
    const avgDuration =
      durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : 0;
    const maxDuration = durations.length > 0 ? Math.max(...durations) : 0;

    const operationsByType: Record<string, { count: number; totalDuration: number }> = {};
    this.entries.forEach((entry) => {
      if (!operationsByType[entry.operation]) {
        operationsByType[entry.operation] = { count: 0, totalDuration: 0 };
      }
      operationsByType[entry.operation].count++;
      operationsByType[entry.operation].totalDuration += entry.duration;
    });

    const operationsByTypeSummary: Record<string, { count: number; avgDuration: number }> = {};
    Object.keys(operationsByType).forEach((key) => {
      const stats = operationsByType[key];
      operationsByTypeSummary[key] = {
        count: stats.count,
        avgDuration: stats.totalDuration / stats.count,
      };
    });

    return {
      totalOperations: this.entries.length,
      slowOperations: slowOps.length,
      averageDuration: avgDuration,
      maxDuration: maxDuration,
      operationsByType: operationsByTypeSummary,
    };
  }

  /**
   * Clear all entries
   */
  clear(): void {
    this.entries = [];
  }

  /**
   * Export entries as JSON
   */
  export(): string {
    return JSON.stringify(
      {
        entries: this.entries,
        summary: this.getSummary(),
        timestamp: new Date().toISOString(),
      },
      null,
      2
    );
  }
}

// Export singleton instance
export const js9PerformanceProfiler = new JS9PerformanceProfiler();

// Export class for testing
export { JS9PerformanceProfiler };
