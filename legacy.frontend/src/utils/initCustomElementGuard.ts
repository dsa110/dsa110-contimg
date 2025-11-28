/**
 * Early Custom Element Guard Initialization
 *
 * This module patches customElements.define to prevent duplicate
 * registration errors that occur during hot module reloading or when
 * third-party libraries (like TinyMCE) are loaded multiple times.
 *
 * Import this module early in your application entry point (e.g., index.tsx)
 * before any libraries that register custom elements are loaded.
 */

import { patchCustomElementsDefine } from "./customElementGuard";

// Apply patch immediately when module loads
// This ensures the patch is active before any custom elements are registered
if (typeof window !== "undefined" && window.customElements) {
  patchCustomElementsDefine();
}

/**
 * Re-export for convenience
 */
export { patchCustomElementsDefine, safeDefineCustomElement } from "./customElementGuard";
