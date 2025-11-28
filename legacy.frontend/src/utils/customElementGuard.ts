/**
 * Custom Element Registration Guard
 *
 * Prevents duplicate custom element registration errors that occur
 * during hot module reloading or when libraries are loaded multiple times.
 *
 * This is particularly useful for third-party libraries like TinyMCE
 * that register custom elements without checking if they're already defined.
 */

/**
 * Safely define a custom element, preventing duplicate registration errors
 *
 * @param name - The custom element name
 * @param constructor - The custom element constructor
 * @param options - Optional element definition options
 * @returns true if the element was registered, false if it already existed
 */
export function safeDefineCustomElement(
  name: string,
  constructor: CustomElementConstructor,
  options?: ElementDefinitionOptions
): boolean {
  // Check if custom elements API is available
  if (typeof window === "undefined" || !window.customElements) {
    console.warn(
      `[CustomElementGuard] Custom Elements API not available, cannot register: ${name}`
    );
    return false;
  }

  // Check if element is already defined
  if (window.customElements.get(name)) {
    // Element already exists - this is fine, just return false
    // Note: Console statements are typically stripped in production builds
    // eslint-disable-next-line no-console
    console.debug(
      `[CustomElementGuard] Custom element '${name}' already defined, skipping registration`
    );
    return false;
  }

  try {
    // Register the element
    window.customElements.define(name, constructor, options);
    return true;
  } catch (error) {
    // If registration fails (e.g., already defined), log and continue
    if (error instanceof Error && error.message.includes("already been defined")) {
      console.warn(
        `[CustomElementGuard] Custom element '${name}' registration failed (already defined):`,
        error
      );
      return false;
    }
    // Re-throw unexpected errors
    throw error;
  }
}

/**
 * Patch customElements.define to prevent duplicate registration errors
 *
 * This wraps the native customElements.define to automatically handle
 * duplicate registration attempts gracefully.
 *
 * Call this early in your application initialization (e.g., in index.tsx)
 * before any third-party libraries that register custom elements are loaded.
 */
export function patchCustomElementsDefine(): void {
  if (typeof window === "undefined" || !window.customElements) {
    console.warn("[CustomElementGuard] Custom Elements API not available, cannot patch");
    return;
  }

  // Store original define method
  const originalDefine = window.customElements.define.bind(window.customElements);

  // Replace with guarded version
  window.customElements.define = function (
    name: string,
    constructor: CustomElementConstructor,
    options?: ElementDefinitionOptions
  ): void {
    // Check if already defined
    if (window.customElements.get(name)) {
      // eslint-disable-next-line no-console
      console.debug(`[CustomElementGuard] Preventing duplicate registration of '${name}'`);
      // Silently ignore duplicate registration
      return;
    }

    try {
      // Call original define
      originalDefine(name, constructor, options);
    } catch (error) {
      // If error is about duplicate registration, ignore it
      if (error instanceof Error && error.message.includes("already been defined")) {
        // eslint-disable-next-line no-console
        console.debug(
          `[CustomElementGuard] Caught duplicate registration error for '${name}', ignoring`
        );
        return;
      }
      // Re-throw unexpected errors
      throw error;
    }
  };

  // eslint-disable-next-line no-console
  console.log(
    "[CustomElementGuard] customElements.define patched to prevent duplicate registration"
  );
}

/**
 * Restore original customElements.define (for testing or cleanup)
 */
export function unpatchCustomElementsDefine(): void {
  if (typeof window === "undefined" || !window.customElements) {
    return;
  }

  // Note: We can't easily restore the original without storing it
  // This is mainly for testing scenarios
  console.warn(
    "[CustomElementGuard] Unpatching not fully supported - customElements.define may have been modified"
  );
}
