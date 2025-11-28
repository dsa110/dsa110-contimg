/**
 * Early JS9 Patcher Initialization
 *
 * This module applies the JS9 setTimeout patcher immediately when imported,
 * ensuring it's active before JS9 library loads. This is critical because
 * the patcher must be in place before js9support.js executes.
 *
 * Import this module early in your application entry point (e.g., index.tsx or main.tsx)
 * before any JS9-related code is loaded.
 */

import { js9PromisePatcher } from "./js9PromisePatcher";

// Apply patch immediately when module loads
// This ensures the patch is active before JS9 library initializes
if (typeof window !== "undefined") {
  // Only patch in browser environment
  // Enable aggressive mode to catch all immediate setTimeout calls
  // This is safer than trying to detect specific handlers
  js9PromisePatcher.setAggressiveMode(true);
  js9PromisePatcher.patch();

  // Log that patcher is active
  // Note: Console statements are typically stripped in production builds
  // eslint-disable-next-line no-console
  console.log("[JS9 Patcher] Early initialization complete - setTimeout patched (aggressive mode)");
}

/**
 * Re-export for convenience
 */
export { js9PromisePatcher };
