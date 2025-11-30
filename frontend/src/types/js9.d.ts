/**
 * Type declarations for the JS9 FITS viewer library.
 *
 * JS9 is loaded via CDN and has no official @types package.
 * These declarations cover the methods used in this application.
 *
 * @see https://js9.si.edu/
 */

// =============================================================================
// JS9 Type Definitions
// =============================================================================

/**
 * Color map options available in JS9.
 */
export type JS9ColorMap =
  | "grey"
  | "gray"
  | "heat"
  | "cool"
  | "rainbow"
  | "viridis"
  | "magma"
  | "inferno"
  | "plasma"
  | "red"
  | "green"
  | "blue"
  | "a"
  | "b"
  | "bb"
  | "he"
  | "i8";

/**
 * Scale options available in JS9.
 */
export type JS9Scale = "linear" | "log" | "pow" | "sqrt" | "squared" | "asinh" | "sinh" | "histeq";

/**
 * Display options passed to most JS9 methods.
 */
export interface JS9DisplayOptions {
  display?: string;
}

/**
 * Options for loading a FITS image.
 */
export interface JS9LoadOptions extends JS9DisplayOptions {
  /** Callback when image successfully loads */
  onload?: (image: JS9Image) => void;
  /** Callback when image fails to load */
  onerror?: (message: string) => void;
  /** Scale to apply on load */
  scale?: JS9Scale;
  /** Color map to apply on load */
  colormap?: JS9ColorMap;
}

/**
 * Represents a loaded JS9 image.
 */
export interface JS9Image {
  /** Unique image ID */
  id: string;
  /** Image file path or URL */
  file: string;
  /** Image width in pixels */
  width: number;
  /** Image height in pixels */
  height: number;
  /** FITS header data */
  header?: Record<string, string | number>;
}

/**
 * World Coordinate System result from pixel conversion.
 */
export interface JS9WCSResult {
  /** Right Ascension in degrees */
  ra: number;
  /** Declination in degrees */
  dec: number;
  /** RA as sexagesimal string */
  raStr?: string;
  /** Dec as sexagesimal string */
  decStr?: string;
}

/**
 * Mouse event passed to JS9 callbacks.
 */
export interface JS9MouseEvent {
  /** X pixel coordinate */
  x: number;
  /** Y pixel coordinate */
  y: number;
  /** Original browser event */
  evt?: MouseEvent;
}

/**
 * Region object in JS9.
 */
export interface JS9Region {
  /** Unique region ID */
  id: string;
  /** Region type (circle, box, ellipse, polygon, etc.) */
  shape: "circle" | "box" | "ellipse" | "polygon" | "point" | "line" | "text";
  /** X center in image coordinates */
  x: number;
  /** Y center in image coordinates */
  y: number;
  /** Radius (for circle) */
  radius?: number;
  /** Width (for box) */
  width?: number;
  /** Height (for box) */
  height?: number;
  /** Region text/label */
  text?: string;
  /** Region color */
  color?: string;
  /** Whether region is visible */
  visibility?: boolean;
  /** Whether region is moveable */
  moveable?: boolean;
  /** Whether region is deleteable */
  deleteable?: boolean;
}

/**
 * Properties that can be changed on a region.
 */
export interface JS9RegionChangeProperties {
  visibility?: boolean;
  color?: string;
  text?: string;
  moveable?: boolean;
  deleteable?: boolean;
}

/**
 * JS9 callback event types.
 */
export type JS9CallbackType =
  | "onload"
  | "onclose"
  | "onclick"
  | "onmousemove"
  | "onmousedown"
  | "onmouseup"
  | "onkeydown"
  | "onkeyup"
  | "onregionschange"
  | "onzoom"
  | "onpan";

/**
 * Callback function signature for JS9 events.
 */
export type JS9Callback = (
  image: JS9Image | null,
  region: JS9Region | null,
  event: JS9MouseEvent
) => void;

/**
 * Main JS9 library interface.
 */
export interface JS9Static {
  /**
   * Load a FITS image.
   * @param url URL or path to FITS file
   * @param options Load options
   */
  Load: (url: string, options?: JS9LoadOptions) => void;

  /**
   * Close the current image.
   * @param options Display options
   */
  CloseImage: (options?: JS9DisplayOptions) => void;

  /**
   * Close the JS9 display.
   * @param options Display options
   */
  CloseDisplay: (options?: JS9DisplayOptions) => void;

  /**
   * Set the color map.
   * @param colormap Color map name
   * @param options Display options
   */
  SetColormap: (colormap: JS9ColorMap | string, options?: JS9DisplayOptions) => void;

  /**
   * Set the scale/stretch.
   * @param scale Scale name
   * @param options Display options
   */
  SetScale: (scale: JS9Scale | string, options?: JS9DisplayOptions) => void;

  /**
   * Set a display parameter.
   * @param param Parameter name
   * @param value Parameter value
   * @param options Display options
   */
  SetParam: (param: string, value: unknown, options?: JS9DisplayOptions) => void;

  /**
   * Get a display parameter.
   * @param param Parameter name
   * @param options Display options
   */
  GetParam: (param: string, options?: JS9DisplayOptions) => unknown;

  /**
   * Set the pan position.
   * @param x X coordinate (RA in degrees or pixel)
   * @param y Y coordinate (Dec in degrees or pixel)
   * @param options Display options
   */
  SetPan: (x: number, y: number, options?: JS9DisplayOptions) => void;

  /**
   * Set the zoom level.
   * @param zoom Zoom factor or "tofit"
   * @param options Display options
   */
  SetZoom: (zoom: number | "tofit" | "in" | "out", options?: JS9DisplayOptions) => void;

  /**
   * Get the current zoom level.
   * @param options Display options
   */
  GetZoom: (options?: JS9DisplayOptions) => number;

  /**
   * Convert pixel coordinates to WCS.
   * @param x X pixel coordinate
   * @param y Y pixel coordinate
   * @param options Display options
   */
  PixToWCS: (x: number, y: number, options?: JS9DisplayOptions) => JS9WCSResult | null;

  /**
   * Convert WCS coordinates to pixel.
   * @param ra Right Ascension in degrees
   * @param dec Declination in degrees
   * @param options Display options
   */
  WCSToPix: (
    ra: number,
    dec: number,
    options?: JS9DisplayOptions
  ) => { x: number; y: number } | null;

  /**
   * Get regions.
   * @param which Which regions ("all" or region ID)
   * @param options Display options
   */
  GetRegions: (which?: string | "all", options?: JS9DisplayOptions) => JS9Region[];

  /**
   * Add a region.
   * @param shape Region shape
   * @param properties Region properties
   * @param options Display options
   */
  AddRegions: (
    shape: JS9Region["shape"],
    properties?: Partial<JS9Region>,
    options?: JS9DisplayOptions
  ) => void;

  /**
   * Change region properties.
   * @param which Region ID or "all"
   * @param properties Properties to change
   * @param options Display options
   */
  ChangeRegions: (
    which: string | "all",
    properties: JS9RegionChangeProperties,
    options?: JS9DisplayOptions
  ) => void;

  /**
   * Remove regions.
   * @param which Region ID or "all"
   * @param options Display options
   */
  RemoveRegions: (which?: string | "all", options?: JS9DisplayOptions) => void;

  /**
   * Get the current pan position.
   * @param options Display options
   * @returns Object with x, y pixel coordinates
   */
  GetPan: (options?: JS9DisplayOptions) => { x: number; y: number } | null;

  /**
   * Save the current image as PNG.
   * @param filenameOrOptions Optional filename or display options
   * @param options Display options (if first param is filename)
   */
  SavePNG: (filenameOrOptions?: string | JS9DisplayOptions, options?: JS9DisplayOptions) => void;

  /**
   * Save the current image as FITS.
   * @param filenameOrOptions Optional filename or display options
   * @param options Display options (if first param is filename)
   */
  SaveFITS: (filenameOrOptions?: string | JS9DisplayOptions, options?: JS9DisplayOptions) => void;

  /**
   * Get image data as a 2D array.
   * @param options Display options
   * @returns Image data array
   */
  GetImageData: (options?: JS9DisplayOptions) => {
    width: number;
    height: number;
    data: number[];
  } | null;

  /**
   * Close the current image.
   * @param options Display options
   */
  CloseImage: (options?: JS9DisplayOptions) => void;

  /**
   * Display a message in the JS9 message area.
   * @param message Message text
   * @param options Display options
   */
  DisplayMessage: (message: string, options?: JS9DisplayOptions) => void;

  /**
   * Set an event callback.
   * @param event Event type
   * @param callback Callback function
   * @param options Display options
   */
  SetCallback: (event: JS9CallbackType, callback: JS9Callback, options?: JS9DisplayOptions) => void;

  /**
   * Remove an event callback.
   * @param event Event type
   * @param options Display options
   */
  RemoveCallback: (event: JS9CallbackType, options?: JS9DisplayOptions) => void;
}

// =============================================================================
// Global Augmentation
// =============================================================================

declare global {
  interface Window {
    /**
     * JS9 FITS viewer library instance.
     * Loaded via CDN script tag.
     */
    JS9: JS9Static;
  }
}

export {};
