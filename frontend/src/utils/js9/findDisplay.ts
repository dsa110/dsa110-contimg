/**
 * JS9 Display Finding Utility
 * 
 * Centralizes the pattern of finding a JS9 display by displayId.
 * Handles JS9's inconsistent property names (id, display, divID).
 * 
 * @param displayId - The display ID to find
 * @returns The JS9 display object, or null if not found
 */

declare global {
  interface Window {
    JS9: any;
  }
}

export function findDisplay(displayId: string): any | null {
  if (!window.JS9 || !window.JS9.displays) {
    return null;
  }

  return window.JS9.displays.find((d: any) => {
    const divId = d.id || d.display || d.divID;
    return divId === displayId;
  }) || null;
}

/**
 * Type guard to check if JS9 is available and fully loaded
 */
export function isJS9Available(): boolean {
  return !!(window.JS9 && typeof window.JS9.Load === 'function');
}

/**
 * Get the current image ID for a display, if available
 */
export function getDisplayImageId(displayId: string): string | null {
  const display = findDisplay(displayId);
  return display?.im?.id || null;
}

