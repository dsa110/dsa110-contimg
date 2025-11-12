/**
 * JS9Service - Abstraction Layer for JS9 API
 * 
 * Provides a clean, typed interface to JS9 functionality with:
 * - Error handling
 * - Type safety
 * - Easier testing (mockable)
 * - Consistent API usage
 */

import { logger } from '../../utils/logger';

declare global {
  interface Window {
    JS9: any;
  }
}

export interface JS9Image {
  id: string;
  [key: string]: any;
}

export interface JS9Display {
  id?: string;
  display?: string;
  divID?: string;
  im?: JS9Image;
  [key: string]: any;
}

export interface JS9LoadOptions {
  divID?: string;
  display?: string;
  scale?: string;
  colormap?: string;
  onload?: (im: JS9Image) => void;
  onerror?: (err: any) => void;
  [key: string]: any;
}

export interface JS9InitOptions {
  loadImage?: boolean;
  resizeDisplay?: boolean;
  autoResize?: boolean;
  InstallDir?: string;
  workerPath?: string;
  wasmPath?: string;
  wasmJS?: string;
  prefsPath?: string;
  helperType?: string;
  helperPort?: number;
  loadProxy?: boolean;
  [key: string]: any;
}

export interface JS9SetOptions extends JS9InitOptions {
  [key: string]: any;
}

class JS9Service {
  /**
   * Check if JS9 is available and fully loaded
   */
  isAvailable(): boolean {
    return (
      typeof window !== 'undefined' &&
      window.JS9 !== undefined &&
      typeof window.JS9.Load === 'function'
    );
  }

  /**
   * Get all JS9 displays
   */
  getDisplays(): JS9Display[] {
    if (!this.isAvailable() || !window.JS9.displays) {
      return [];
    }
    return window.JS9.displays;
  }

  /**
   * Find a display by ID
   */
  findDisplay(displayId: string): JS9Display | null {
    if (!this.isAvailable() || !window.JS9.displays) {
      return null;
    }

    return (
      window.JS9.displays.find((d: JS9Display) => {
        const divId = d.id || d.display || d.divID;
        return divId === displayId;
      }) || null
    );
  }

  /**
   * Get image ID from a display
   */
  getImageId(displayId: string): string | null {
    const display = this.findDisplay(displayId);
    return display?.im?.id || null;
  }

  /**
   * Check if a display has an image loaded
   */
  hasImage(displayId: string): boolean {
    const display = this.findDisplay(displayId);
    return !!(display?.im);
  }

  /**
   * Initialize JS9 globally
   */
  init(options?: JS9InitOptions): void {
    if (!this.isAvailable()) {
      throw new Error('JS9 is not available');
    }

    if (typeof window.JS9.Init === 'function') {
      try {
        window.JS9.Init(options || {});
        logger.debug('JS9 initialized:', options);
      } catch (err) {
        logger.error('JS9 Init failed:', err);
        throw err;
      }
    }
  }

  /**
   * Set JS9 global options
   */
  setOptions(options: JS9SetOptions): void {
    if (!this.isAvailable()) {
      throw new Error('JS9 is not available');
    }

    if (typeof window.JS9.SetOptions === 'function') {
      try {
        window.JS9.SetOptions(options);
        logger.debug('JS9 options set:', options);
      } catch (err) {
        logger.warn('JS9 SetOptions failed:', err);
        // Fallback: try setting opts directly (read-only properties will fail silently)
        if (window.JS9.opts) {
          Object.assign(window.JS9.opts, options);
        }
      }
    } else if (window.JS9.opts) {
      // Fallback: set opts directly
      Object.assign(window.JS9.opts, options);
    }
  }

  /**
   * Register a div with JS9
   */
  addDivs(displayId: string): void {
    if (!this.isAvailable()) {
      throw new Error('JS9 is not available');
    }

    if (typeof window.JS9.AddDivs === 'function') {
      try {
        window.JS9.AddDivs(displayId);
        logger.debug('JS9 div registered:', displayId);
      } catch (err) {
        logger.debug('JS9 AddDivs:', err);
        // Continue anyway - JS9 might auto-detect the div
      }
    }
  }

  /**
   * Load an image into JS9
   */
  loadImage(imagePath: string, options?: JS9LoadOptions): void {
    if (!this.isAvailable()) {
      throw new Error('JS9 is not available');
    }

    if (typeof window.JS9.Load !== 'function') {
      throw new Error('JS9.Load is not available');
    }

    try {
      window.JS9.Load(imagePath, options || {});
    } catch (err) {
      logger.error('JS9 Load failed:', err);
      throw err;
    }
  }

  /**
   * Close an image
   */
  closeImage(imageId: string): void {
    if (!this.isAvailable()) {
      return;
    }

    if (typeof window.JS9.CloseImage === 'function') {
      try {
        window.JS9.CloseImage(imageId);
        // Also try to remove from internal cache
        if (window.JS9.images && window.JS9.images[imageId]) {
          delete window.JS9.images[imageId];
        }
      } catch (err) {
        logger.debug('Error closing image:', err);
      }
    }
  }

  /**
   * Resize a display
   */
  resizeDisplay(displayId: string): void {
    if (!this.isAvailable()) {
      return;
    }

    if (typeof window.JS9.ResizeDisplay === 'function') {
      try {
        window.JS9.ResizeDisplay(displayId);
      } catch (err) {
        logger.warn('Failed to resize JS9 display:', err);
      }
    }
  }

  /**
   * Set the active display for an image
   */
  setDisplay(displayId: string, imageId: string): void {
    if (!this.isAvailable()) {
      return;
    }

    if (typeof window.JS9.SetDisplay === 'function') {
      try {
        window.JS9.SetDisplay(displayId, imageId);
      } catch (err) {
        logger.debug('Error setting display:', err);
      }
    }
  }

  /**
   * Get JS9 InstallDir function (if available)
   */
  getInstallDir(): ((path: string) => string) | null {
    if (!this.isAvailable()) {
      return null;
    }

    if (typeof window.JS9.InstallDir === 'function') {
      return window.JS9.InstallDir;
    }

    return null;
  }

  /**
   * Get JS9 options object
   */
  getOptions(): any {
    if (!this.isAvailable()) {
      return null;
    }

    return window.JS9.opts || null;
  }

  /**
   * Get JS9 images cache
   */
  getImages(): Record<string, JS9Image> | null {
    if (!this.isAvailable()) {
      return null;
    }

    return window.JS9.images || null;
  }
}

// Export singleton instance
export const js9Service = new JS9Service();

// Export class for testing
export { JS9Service };

