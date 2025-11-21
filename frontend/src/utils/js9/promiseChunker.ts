/**
 * Promise Chunker Utility
 *
 * Provides utilities to break up long-running promise chains into smaller chunks
 * to prevent setTimeout handler violations and improve UI responsiveness.
 */

/**
 * Execute a function in chunks, yielding control back to the event loop periodically
 */
export function chunkedExecution<T>(
  work: () => T | null,
  checkComplete: (result: T | null) => boolean,
  chunkTimeMs: number = 5
): Promise<T | null> {
  return new Promise((resolve) => {
    function processChunk() {
      const startTime = performance.now();
      let result: T | null = null;

      // Process work until chunk time is exceeded or work is complete
      while (performance.now() - startTime < chunkTimeMs) {
        result = work();
        if (checkComplete(result)) {
          resolve(result);
          return;
        }
      }

      // Yield control back to event loop
      if (typeof window !== "undefined" && window.requestIdleCallback) {
        window.requestIdleCallback(processChunk, { timeout: 10 });
      } else {
        setTimeout(processChunk, 0);
      }
    }

    processChunk();
  });
}

/**
 * Process an array of items in chunks to avoid blocking the event loop
 */
export async function processArrayInChunks<T, R>(
  items: T[],
  processor: (item: T) => R | Promise<R>,
  chunkSize: number = 10,
  delayBetweenChunks: number = 0
): Promise<R[]> {
  const results: R[] = [];

  for (let i = 0; i < items.length; i += chunkSize) {
    const chunk = items.slice(i, i + chunkSize);
    const chunkResults = await Promise.all(chunk.map(processor));
    results.push(...chunkResults);

    // Yield control between chunks if delay is specified
    if (delayBetweenChunks > 0 && i + chunkSize < items.length) {
      await new Promise((resolve) => setTimeout(resolve, delayBetweenChunks));
    }
  }

  return results;
}

/**
 * Wrap a promise-returning function to execute in chunks
 */
export function chunkedPromise<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  options?: { chunkTimeMs?: number; maxChunks?: number }
): T {
  const chunkTimeMs = options?.chunkTimeMs || 5;
  const maxChunks = options?.maxChunks || 1000;

  return (async (...args: Parameters<T>): Promise<ReturnType<T>> => {
    let chunkCount = 0;

    const execute = async (): Promise<ReturnType<T>> => {
      const startTime = performance.now();
      let result: ReturnType<T> | null = null;

      try {
        result = await fn(...args);
        return result;
      } catch (error) {
        throw error;
      } finally {
        const duration = performance.now() - startTime;
        if (duration > chunkTimeMs && chunkCount < maxChunks) {
          chunkCount++;
          // If execution took too long, yield before continuing
          await new Promise((resolve) => {
            if (typeof window !== "undefined" && window.requestIdleCallback) {
              window.requestIdleCallback(() => resolve(undefined), { timeout: 10 });
            } else {
              setTimeout(() => resolve(undefined), 0);
            }
          });
        }
      }
    };

    return execute();
  }) as T;
}

/**
 * Create a debounced version of a function that ensures execution doesn't block
 */
export function nonBlockingDebounce<T extends (...args: any[]) => any>(
  fn: T,
  delayMs: number = 0
): T {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  let lastArgs: Parameters<T> | null = null;

  return ((...args: Parameters<T>) => {
    lastArgs = args;

    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    timeoutId = setTimeout(() => {
      if (lastArgs) {
        // Execute in next tick to avoid blocking
        if (typeof window !== "undefined" && window.requestIdleCallback) {
          window.requestIdleCallback(() => fn(...lastArgs!), { timeout: delayMs });
        } else {
          setTimeout(() => fn(...lastArgs!), 0);
        }
      }
      timeoutId = null;
      lastArgs = null;
    }, delayMs);
  }) as T;
}

/**
 * Monitor promise chain execution time and warn if it exceeds threshold
 */
export function monitorPromiseChain<T>(
  promise: Promise<T>,
  operationName: string,
  thresholdMs: number = 50
): Promise<T> {
  const startTime = performance.now();

  return promise
    .then((result) => {
      const duration = performance.now() - startTime;
      if (duration > thresholdMs) {
        console.warn(
          `[Promise Monitor] ${operationName} took ${duration.toFixed(2)}ms (threshold: ${thresholdMs}ms)`
        );
      }
      return result;
    })
    .catch((error) => {
      const duration = performance.now() - startTime;
      console.error(
        `[Promise Monitor] ${operationName} failed after ${duration.toFixed(2)}ms:`,
        error
      );
      throw error;
    });
}
