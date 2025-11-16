/**
 * Promise Resolution Optimizer for JS9
 *
 * Optimizes jQuery Deferred promise resolution to prevent long setTimeout handlers.
 * Patches the problematic promise resolution code in js9support.js.
 */

interface PromiseResolutionStats {
  totalResolutions: number;
  slowResolutions: number;
  maxDuration: number;
  averageDuration: number;
}

class PromiseResolutionOptimizer {
  private stats: PromiseResolutionStats = {
    totalResolutions: 0,
    slowResolutions: 0,
    maxDuration: 0,
    averageDuration: 0,
  };
  private isOptimized: boolean = false;
  private readonly SLOW_THRESHOLD_MS: number = 50;

  /**
   * Optimize promise resolution by patching jQuery Deferred
   */
  optimize(): void {
    if (this.isOptimized) {
      console.warn("[PromiseOptimizer] Already optimized");
      return;
    }

    if (typeof window === "undefined" || !(window as any).jQuery) {
      console.warn("[PromiseOptimizer] jQuery not available, skipping optimization");
      return;
    }

    // Patch jQuery.Deferred to use chunked resolution
    this.patchJQueryDeferred();

    this.isOptimized = true;
    console.log("[PromiseOptimizer] Promise resolution optimized");
  }

  /**
   * Patch jQuery.Deferred to break up long promise chains
   */
  private patchJQueryDeferred(): void {
    const jQuery = (window as any).jQuery;
    if (!jQuery || !jQuery.Deferred) {
      return;
    }

    const originalDeferred = jQuery.Deferred;
    const self = this;

    // Wrap Deferred to monitor and optimize resolution
    jQuery.Deferred = function (func?: any) {
      const deferred = originalDeferred.call(this, func);

      // Patch the resolveWith method to use chunked execution
      const originalResolveWith = deferred.resolveWith;
      deferred.resolveWith = function (context: any, args: any[]) {
        const startTime = performance.now();

        try {
          // Use requestIdleCallback if available for non-critical resolution
          if (
            typeof window !== "undefined" &&
            window.requestIdleCallback &&
            args &&
            args.length > 0
          ) {
            // For large argument arrays, use idle callback
            if (args.length > 10) {
              window.requestIdleCallback(
                () => {
                  originalResolveWith.call(deferred, context, args);
                },
                { timeout: 100 }
              );
              return deferred;
            }
          }

          // For smaller resolutions, execute immediately but monitor
          const result = originalResolveWith.call(deferred, context, args);
          const duration = performance.now() - startTime;

          self.recordStats(duration);

          return result;
        } catch (error) {
          const duration = performance.now() - startTime;
          self.recordStats(duration);
          throw error;
        }
      };

      return deferred;
    };

    // Copy static methods
    Object.keys(originalDeferred).forEach((key) => {
      if (typeof originalDeferred[key] === "function") {
        (jQuery.Deferred as any)[key] = originalDeferred[key];
      }
    });
  }

  /**
   * Record statistics about promise resolution
   */
  private recordStats(duration: number): void {
    this.stats.totalResolutions++;
    this.stats.averageDuration =
      (this.stats.averageDuration * (this.stats.totalResolutions - 1) + duration) /
      this.stats.totalResolutions;

    if (duration > this.stats.maxDuration) {
      this.stats.maxDuration = duration;
    }

    if (duration > this.SLOW_THRESHOLD_MS) {
      this.stats.slowResolutions++;
      if (duration > 100) {
        console.warn(`[PromiseOptimizer] Slow promise resolution: ${duration.toFixed(2)}ms`);
      }
    }
  }

  /**
   * Get optimization statistics
   */
  getStats(): PromiseResolutionStats {
    return { ...this.stats };
  }

  /**
   * Reset statistics
   */
  resetStats(): void {
    this.stats = {
      totalResolutions: 0,
      slowResolutions: 0,
      maxDuration: 0,
      averageDuration: 0,
    };
  }

  /**
   * Check if optimized
   */
  getOptimized(): boolean {
    return this.isOptimized;
  }
}

// Export singleton instance
export const promiseResolutionOptimizer = new PromiseResolutionOptimizer();

// Export class for testing
export { PromiseResolutionOptimizer };
