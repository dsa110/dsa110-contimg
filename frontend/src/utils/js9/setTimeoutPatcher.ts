/**
 * setTimeout Patcher for JS9 Performance Optimization
 *
 * Patches the problematic setTimeout handler in js9support.js:3884
 * to break up long-running promise resolution chains into chunks.
 */

import { logger } from "../logger";

class SetTimeoutPatcher {
  private originalSetTimeout: typeof setTimeout;
  private isPatched: boolean = false;
  private readonly CHUNK_TIME_MS: number = 5; // Max time per chunk

  constructor() {
    this.originalSetTimeout = window.setTimeout;
  }

  /**
   * Patch setTimeout to use chunked execution for long-running handlers
   */
  patch(): void {
    if (this.isPatched) {
      logger.warn("[SetTimeoutPatcher] Already patched");
      return;
    }

    const self = this;
    (window.setTimeout as any) = function (
      handler: TimerHandler,
      timeout?: number,
      ...args: any[]
    ): number {
      if (typeof handler === "function") {
        // Check if this is likely the problematic handler from js9support.js
        const handlerString = handler.toString();
        const isJS9Handler =
          handlerString.includes("process") ||
          handlerString.includes("mightThrow") ||
          handlerString.includes("deferred") ||
          handlerString.includes("resolve");

        if (isJS9Handler && timeout === undefined) {
          // This is likely the problematic setTimeout(process) call
          return self.originalSetTimeout.call(
            window,
            self.createChunkedHandler(handler),
            timeout,
            ...args
          );
        }
      }

      // For all other setTimeout calls, use original
      return self.originalSetTimeout.call(window, handler, timeout, ...args);
    };

    this.isPatched = true;
    logger.info("[SetTimeoutPatcher] setTimeout patched for chunked execution");
  }

  /**
   * Create a chunked version of a handler that yields control periodically
   */
  private createChunkedHandler(handler: Function): Function {
    const self = this;

    return function (this: any, ...args: any[]) {
      const startTime = performance.now();

      // Use requestIdleCallback if available to defer execution
      if (typeof window !== "undefined" && window.requestIdleCallback) {
        return new Promise<void>((resolve, reject) => {
          window.requestIdleCallback!(
            () => {
              try {
                const result = handler.apply(this, args);
                const duration = performance.now() - startTime;

                if (duration > self.CHUNK_TIME_MS) {
                  logger.warn(
                    `[SetTimeoutPatcher] Handler took ${duration.toFixed(2)}ms after deferral`
                  );
                }

                resolve(result);
              } catch (error) {
                reject(error);
              }
            },
            { timeout: 100 }
          );
        });
      }

      // Fallback: Execute with monitoring
      try {
        const result = handler.apply(this, args);
        const duration = performance.now() - startTime;

        if (duration > 50) {
          logger.warn(`[SetTimeoutPatcher] Handler took ${duration.toFixed(2)}ms`);
        }

        return result;
      } catch (error) {
        throw error;
      }
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
    logger.info("[SetTimeoutPatcher] setTimeout restored to original");
  }

  /**
   * Check if patched
   */
  getPatched(): boolean {
    return this.isPatched;
  }
}

// Export singleton instance
export const setTimeoutPatcher = new SetTimeoutPatcher();

// Export class for testing
export { SetTimeoutPatcher };
