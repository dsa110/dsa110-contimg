/**
 * JS9 Promise Patcher
 *
 * Directly patches the problematic setTimeout(process) call in js9support.js:3884
 * to break up promise resolution chains and prevent long-running setTimeout handlers.
 */

class JS9PromisePatcher {
  private isPatched: boolean = false;
  private originalSetTimeout: typeof setTimeout;
  private readonly YIELD_THRESHOLD_MS: number = 10; // Yield if handler exceeds this
  private aggressiveMode: boolean = false; // Patch all immediate setTimeout calls

  constructor() {
    this.originalSetTimeout = window.setTimeout;
  }

  /**
   * Enable aggressive mode - patches ALL setTimeout calls with timeout=0 or undefined
   * Use this if the handler detection is not working correctly
   */
  setAggressiveMode(enabled: boolean): void {
    this.aggressiveMode = enabled;
    if (this.isPatched) {
      // Re-patch with new mode
      this.unpatch();
      this.patch();
    }
  }

  /**
   * Patch setTimeout to intercept and optimize JS9 promise resolution
   */
  patch(): void {
    if (this.isPatched) {
      // Silently return if already patched (e.g., by initPatcher)
      // Only log in development mode for debugging
      if (import.meta.env.DEV) {
        logger.debug("[JS9PromisePatcher] Already patched, skipping");
      }
      return;
    }

    const self = this;

    window.setTimeout = function (handler: TimerHandler, timeout?: number, ...args: any[]): number {
      // Patch handlers called with no timeout or timeout=0 (immediate execution)
      // This matches the pattern: window.setTimeout(process) in js9support.js:3884
      if (typeof handler === "function" && (timeout === undefined || timeout === 0)) {
        let shouldPatch = false;

        if (self.aggressiveMode) {
          // Aggressive mode: patch ALL immediate setTimeout calls
          shouldPatch = true;
        } else {
          // Normal mode: only patch handlers that match JS9 promise resolution patterns
          const handlerStr = handler.toString();
          const handlerName = handler.name || "";

          // Detection strategies:
          // 1. Check function name (if not minified)
          // 2. Check function string content
          // 3. Check stack trace (if available)
          const isPromiseHandler =
            handlerName === "process" ||
            handlerStr.includes("process") ||
            handlerStr.includes("mightThrow") ||
            handlerStr.includes("resolve") ||
            handlerStr.includes("deferred") ||
            handlerStr.includes("Deferred") ||
            // Also catch handlers that might be closures wrapping process
            (handlerStr.length < 200 && // Short functions are more likely to be the process wrapper
              (handlerStr.includes("try") || handlerStr.includes("catch")));

          shouldPatch = isPromiseHandler;
        }

        if (shouldPatch) {
          // Wrap in optimized handler that yields control
          const optimizedHandler = self.createOptimizedHandler(handler);

          // Log in development mode for debugging
          if (import.meta.env.DEV) {
            const handlerName = (handler as any).name || "anonymous";
            console.debug(`[JS9PromisePatcher] Intercepted setTimeout handler: ${handlerName}`);
          }

          return self.originalSetTimeout.call(window, optimizedHandler, timeout, ...args);
        }
      }

      // For all other setTimeout calls, use original
      return self.originalSetTimeout.call(window, handler, timeout, ...args);
    };

    this.isPatched = true;
    console.log("[JS9PromisePatcher] setTimeout patched for JS9 promise optimization");
  }

  /**
   * Create an optimized handler that yields control to prevent blocking
   * Uses time-slicing to break up long-running promise chain execution
   */
  private createOptimizedHandler(handler: Function): Function {
    const self = this;

    return function (this: any, ...args: any[]) {
      // Strategy: Use requestIdleCallback if available for better yielding
      // Otherwise, use setTimeout with immediate execution but monitor duration
      if (typeof window !== "undefined" && window.requestIdleCallback) {
        // Use requestIdleCallback to defer execution to idle time
        window.requestIdleCallback(
          () => {
            const startTime = performance.now();
            try {
              const result = handler.apply(this, args);
              const duration = performance.now() - startTime;

              if (duration > self.YIELD_THRESHOLD_MS) {
                console.warn(
                  `[JS9PromisePatcher] Handler took ${duration.toFixed(2)}ms (after idle callback)`
                );
              }

              // If still too long, the handler itself needs optimization
              // but we've at least yielded control once
              return result;
            } catch (error) {
              console.error("[JS9PromisePatcher] Handler error:", error);
              throw error;
            }
          },
          { timeout: 50 } // Don't wait more than 50ms
        );
        return;
      }

      // Fallback: Use setTimeout with immediate execution but monitor
      // This still yields control to the event loop before execution
      self.originalSetTimeout(() => {
        const startTime = performance.now();

        try {
          const result = handler.apply(this, args);
          const duration = performance.now() - startTime;

          if (duration > self.YIELD_THRESHOLD_MS) {
            console.warn(
              `[JS9PromisePatcher] Handler took ${duration.toFixed(2)}ms (threshold: ${self.YIELD_THRESHOLD_MS}ms)`
            );

            // If handler is still very long, log additional warning
            if (duration > 50) {
              console.warn(
                `[JS9PromisePatcher] Handler execution exceeded 50ms threshold. ` +
                  `Consider optimizing the promise chain or using chunked execution.`
              );
            }
          }

          return result;
        } catch (error) {
          console.error("[JS9PromisePatcher] Handler error:", error);
          throw error;
        }
      }, 0); // Yield to event loop before execution
    };
  }

  /**
   * Restore original setTimeout
   */
  unpatch(): void {
    if (!this.isPatched) {
      return;
    }

    window.setTimeout = this.originalSetTimeout;
    this.isPatched = false;
    console.log("[JS9PromisePatcher] setTimeout restored");
  }

  /**
   * Check if patched
   */
  getPatched(): boolean {
    return this.isPatched;
  }
}

// Export singleton instance
export const js9PromisePatcher = new JS9PromisePatcher();

// Export class for testing
export { JS9PromisePatcher };
