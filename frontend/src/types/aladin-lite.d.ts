/**
 * Type declarations for Aladin Lite v3
 *
 * This provides TypeScript type safety for the Aladin Lite sky viewer library.
 * Note: These are partial declarations based on the API we actually use.
 * For full API documentation, see: https://aladin.cds.unistra.fr/AladinLite/doc/
 */

declare module "aladin-lite" {
  /**
   * Main Aladin module
   */
  interface AladinStatic {
    /**
     * Promise that resolves when WASM module is initialized
     */
    init: Promise<void>;

    /**
     * Create an Aladin instance in the specified container
     */
    aladin(container: HTMLElement | string, options?: AladinOptions): AladinInstance;

    /**
     * Create a catalog
     */
    catalog(options?: CatalogOptions): AladinCatalog;

    /**
     * Create a source marker
     */
    source(ra: number, dec: number, data?: { name?: string; [key: string]: any }): AladinSource;
  }

  /**
   * Options for creating an Aladin instance
   */
  interface AladinOptions {
    /** Target coordinates as string "RA DEC" or object */
    target?: string | { ra: number; dec: number };
    /** Field of view in degrees */
    fov?: number;
    /** Survey to display */
    survey?: string;
    /** Show reticle (crosshair) */
    showReticle?: boolean;
    /** Show zoom controls */
    showZoomControl?: boolean;
    /** Show fullscreen button */
    showFullscreenControl?: boolean;
    /** Show layers panel */
    showLayersControl?: boolean;
    /** Show goto controls */
    showGotoControl?: boolean;
    /** Show share button */
    showShareControl?: boolean;
    /** Show catalog in sidebar */
    showCatalog?: boolean;
    /** Show coordinate frame */
    showFrame?: boolean;
    /** Projection type */
    projection?: string;
    /** Enable/disable zoom with mouse wheel */
    allowFullZoomout?: boolean;
    /** Cooframe (coordinate frame) */
    cooFrame?: string;
  }

  /**
   * Aladin viewer instance
   */
  interface AladinInstance {
    /**
     * Navigate to specified coordinates
     */
    gotoRaDec(ra: number, dec: number): void;

    /**
     * Set field of view
     */
    setFoV(fov: number): void;

    /**
     * Set image survey
     */
    setImageSurvey(survey: string): void;

    /**
     * Add a catalog overlay
     */
    addCatalog(catalog: AladinCatalog): void;

    /**
     * Remove a catalog overlay
     */
    removeCatalog(catalog: AladinCatalog): void;

    /**
     * Increase zoom level
     */
    increaseZoom(): void;

    /**
     * Decrease zoom level
     */
    decreaseZoom(): void;

    /**
     * Toggle fullscreen mode
     */
    toggleFullscreen(): void;

    /**
     * Get current field of view
     */
    getFoV(): [number, number];

    /**
     * Get current RA/Dec
     */
    getRaDec(): [number, number];

    /**
     * Destroy the Aladin instance and clean up resources
     */
    destroy(): void;

    /**
     * On event handler
     */
    on(event: string, callback: (...args: any[]) => void): void;

    /**
     * Off event handler
     */
    off(event: string, callback?: (...args: any[]) => void): void;
  }

  /**
   * Options for creating a catalog
   */
  interface CatalogOptions {
    /** Catalog name */
    name?: string;
    /** Source size in pixels */
    sourceSize?: number;
    /** Source color */
    color?: string;
    /** Catalog shape */
    shape?: "square" | "circle" | "plus" | "cross" | "triangle";
    /** Limit on number of sources */
    limit?: number;
    /** Show catalog in layer control */
    displayLabel?: boolean;
    /** Catalog onClick callback */
    onClick?: (source: AladinSource) => void;
  }

  /**
   * Catalog layer
   */
  interface AladinCatalog {
    /**
     * Add sources to the catalog
     */
    addSources(sources: AladinSource[]): void;

    /**
     * Remove sources from the catalog
     */
    removeSources(sources: AladinSource[]): void;

    /**
     * Hide catalog
     */
    hide(): void;

    /**
     * Show catalog
     */
    show(): void;

    /**
     * Get all sources
     */
    getSources(): AladinSource[];
  }

  /**
   * Source marker
   */
  interface AladinSource {
    /** Right ascension in degrees */
    ra: number;
    /** Declination in degrees */
    dec: number;
    /** Source data */
    data: { name?: string; [key: string]: any };
  }

  const A: AladinStatic;
  export default A;
}
