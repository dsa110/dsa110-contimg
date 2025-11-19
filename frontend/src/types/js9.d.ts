/**
 * TypeScript type definitions for JS9 Astronomical Image Display
 *
 * JS9 is a JavaScript-based astronomical image viewer.
 * These types provide compile-time safety for JS9 API interactions.
 */

declare global {
  interface Window {
    JS9: JS9Instance;
  }
}

/**
 * Main JS9 instance interface
 */
export interface JS9Instance {
  displays: JS9Display[];
  images: JS9Image[];
  opts: Record<string, any>;
  InstallDir?: string;

  // Initialization
  Init(options?: JS9Options): void;
  SetOptions(options: JS9Options): void;

  // Image loading
  Load(
    source: string | ArrayBuffer | Blob,
    options?: JS9LoadOptions,
    handler?: {
      onload?: (im: JS9Image) => void;
      onerror?: (error: Error) => void;
    }
  ): Promise<JS9Image> | void;

  // Image management
  CloseImage(imageId?: string, display?: JS9Display | string): void;
  GetImage(display?: JS9Display | string): JS9Image | null;
  RefreshImage(display?: JS9Display | string): void;

  // Display management
  SetDisplay(displayId: string): void;
  GetDisplays(): JS9Display[];
  AddDivs(divId: string, opts?: Record<string, unknown>): void;
  ResizeDisplay(width: number, height: number, display?: JS9Display | string): void;

  // Image data access
  GetImageData(imageId?: string, display?: JS9Display | string): ImageData | null;
  GetWCS(imageId?: string, display?: JS9Display | string): WCSInfo | null;
  PixToWCS(
    x: number,
    y: number,
    imageId?: string,
    display?: JS9Display | string
  ): WCSCoordinates | null;
  WCSToPix(
    ra: number,
    dec: number,
    imageId?: string,
    display?: JS9Display | string
  ): PixelCoordinates | null;

  // Colormap and scale
  SetColormap(
    colormap: string,
    contrast?: number,
    bias?: number,
    display?: JS9Display | string
  ): void;
  GetColormap(display?: JS9Display | string): ColormapInfo | null;
  SetScale(
    scale: string,
    scalemin?: number,
    scalemax?: number,
    display?: JS9Display | string
  ): void;
  GetScale(display?: JS9Display | string): ScaleInfo | null;

  // Zoom and pan
  SetZoom(zoom: number | string, display?: JS9Display | string): void;
  GetZoom(display?: JS9Display | string): number;
  SetPan(x: number, y: number, display?: JS9Display | string): void;
  GetPan(display?: JS9Display | string): { x: number; y: number } | null;

  // Regions
  GetRegions(shape?: string, imageId?: string, display?: JS9Display | string): JS9Region[];
  AddRegion(
    region: Partial<JS9Region>,
    imageId?: string,
    display?: JS9Display | string
  ): JS9Region | null;
  RemoveRegion(regionId: string | JS9Region, imageId?: string, display?: JS9Display | string): void;
  ChangeRegion(
    regionId: string | JS9Region,
    opts: Partial<JS9Region>,
    imageId?: string,
    display?: JS9Display | string
  ): void;

  // Catalogs and overlays
  AddCatalog(
    catalog: string | CatalogData,
    opts?: CatalogOptions,
    display?: JS9Display | string
  ): void;
  RemoveCatalog(catalog: string, display?: JS9Display | string): void;

  // Analysis
  CountsInRegion(
    region?: string | JS9Region,
    imageId?: string,
    display?: JS9Display | string
  ): RegionCounts | null;
  GetPixelValues(
    opts?: PixelValueOptions,
    imageId?: string,
    display?: JS9Display | string
  ): PixelValueResult | null;

  // Event handling
  AddEventListener(
    event: JS9EventType,
    callback: JS9EventCallback,
    display?: JS9Display | string
  ): void;
  RemoveEventListener(
    event: JS9EventType,
    callback: JS9EventCallback,
    display?: JS9Display | string
  ): void;

  // Plugins
  RegisterPlugin(name: string, func: JS9PluginFunction, opts?: JS9PluginOptions): void;

  // FITS header
  GetFITSHeader(
    raw?: boolean,
    imageId?: string,
    display?: JS9Display | string
  ): FITSHeader | string | null;

  // Utilities
  LookupImage(imageId: string | number, display?: JS9Display | string): JS9Image | null;
  GetDisplayImage(display: JS9Display | string): JS9Image | null;
}

/**
 * JS9 Display
 */
export interface JS9Display {
  id: string;
  divjquery: unknown; // jQuery element
  canvas: HTMLCanvasElement;
  context: CanvasRenderingContext2D;
  width: number;
  height: number;
  im: JS9Image | null;
  layers: Record<string, unknown>;
}

/**
 * JS9 Image
 */
export interface JS9Image {
  id: string;
  file: string;
  file0?: string;
  width: number;
  height: number;
  bitpix?: number;
  header?: FITSHeader;
  params?: ImageParams;
  display?: JS9Display;
  raw?: ImageRawData;
  offscreen?: {
    canvas: HTMLCanvasElement;
    context: CanvasRenderingContext2D;
  };
}

/**
 * JS9 initialization options
 */
export interface JS9Options {
  globalOpts?: {
    helperType?: string;
    helperPort?: number;
    helperURL?: string;
    workDir?: string;
    workDirQuota?: number;
    dataPath?: string;
    analysisPlugins?: string;
  };
  imageOpts?: {
    valpos?: boolean;
    wcssys?: string;
    wcsunits?: string;
  };
  regionOpts?: {
    tagSelect?: boolean;
  };
  [key: string]: unknown;
}

/**
 * JS9 Load options
 */
export interface JS9LoadOptions {
  onload?: (im: JS9Image) => void;
  onerror?: (error: Error) => void;
  display?: string;
  scale?: string;
  colormap?: string;
  contrast?: number;
  bias?: number;
  zoom?: number | string;
  parentFile?: string;
  [key: string]: unknown;
}

/**
 * JS9 Event types
 */
export type JS9EventType =
  | "displayimage"
  | "imageLoad"
  | "imageDisplay"
  | "imageclose"
  | "regionchange"
  | "onregionchange"
  | "onimageload"
  | "onimagedisplay"
  | "onimageclose"
  | "keydown"
  | "keyup"
  | "keypress"
  | "mousedown"
  | "mouseup"
  | "mousemove"
  | "mouseout"
  | "touchstart"
  | "touchmove"
  | "touchend";

/**
 * JS9 Event callback
 */
export type JS9EventCallback = (im: JS9Image, data?: unknown) => void;

/**
 * JS9 Region
 */
export interface JS9Region {
  id: string;
  shape: "annulus" | "box" | "circle" | "ellipse" | "line" | "point" | "polygon" | "text";
  tags?: string;
  x?: number;
  y: number;
  dx?: number;
  dy?: number;
  width?: number;
  height?: number;
  radius?: number;
  radii?: number[];
  angle?: number;
  pts?: Array<{ x: number; y: number }>;
  color?: string;
  strokeWidth?: number;
  text?: string;
  fontFamily?: string;
  fontSize?: number;
  fontStyle?: string;
  fontWeight?: string;
  data?: unknown;
  [key: string]: unknown;
}

/**
 * WCS Coordinate information
 */
export interface WCSInfo {
  wcsname?: string;
  wcstype?: string;
  crpix1?: number;
  crpix2?: number;
  crval1?: number;
  crval2?: number;
  cdelt1?: number;
  cdelt2?: number;
  ctype1?: string;
  ctype2?: string;
  cunit1?: string;
  cunit2?: string;
  [key: string]: unknown;
}

/**
 * WCS Coordinates (RA/Dec)
 */
export interface WCSCoordinates {
  ra: number;
  dec: number;
  str?: string;
  sys?: string;
  [key: string]: unknown;
}

/**
 * Pixel Coordinates
 */
export interface PixelCoordinates {
  x: number;
  y: number;
}

/**
 * Colormap information
 */
export interface ColormapInfo {
  colormap: string;
  contrast: number;
  bias: number;
}

/**
 * Scale information
 */
export interface ScaleInfo {
  scale: string;
  scalemin: number;
  scalemax: number;
}

/**
 * FITS Header
 */
export interface FITSHeader {
  [keyword: string]: string | number | boolean | undefined;
  SIMPLE?: boolean;
  BITPIX?: number;
  NAXIS?: number;
  NAXIS1?: number;
  NAXIS2?: number;
  BUNIT?: string;
  BSCALE?: number;
  BZERO?: number;
}

/**
 * Image parameters
 */
export interface ImageParams {
  wcssys?: string;
  wcsunits?: string;
  [key: string]: unknown;
}

/**
 * Image raw data
 */
export interface ImageRawData {
  width: number;
  height: number;
  bitpix: number;
  data: ArrayBuffer | Float32Array | Float64Array | Int8Array | Int16Array | Int32Array;
  header?: FITSHeader;
}

/**
 * Region counts result
 */
export interface RegionCounts {
  area: number;
  sum: number;
  mean: number;
  median?: number;
  min: number;
  max: number;
  npix: number;
}

/**
 * Pixel value options
 */
export interface PixelValueOptions {
  x?: number;
  y?: number;
  [key: string]: unknown;
}

/**
 * Pixel value result
 */
export interface PixelValueResult {
  x: number;
  y: number;
  value: number;
  ra?: number;
  dec?: number;
  [key: string]: unknown;
}

/**
 * Catalog data
 */
export interface CatalogData {
  name: string;
  data: Array<{
    ra: number;
    dec: number;
    [key: string]: unknown;
  }>;
}

/**
 * Catalog options
 */
export interface CatalogOptions {
  shape?: string;
  color?: string;
  width?: number;
  height?: number;
  radius?: number;
  [key: string]: unknown;
}

/**
 * JS9 Plugin function
 */
export type JS9PluginFunction = (im: JS9Image, opts?: Record<string, unknown>) => void;

/**
 * JS9 Plugin options
 */
export interface JS9PluginOptions {
  menu?: string;
  menuItem?: string;
  help?: string;
  [key: string]: unknown;
}

/**
 * Type guard to check if JS9 is available
 */
export function isJS9Available(): boolean {
  return typeof window !== "undefined" && typeof window.JS9 !== "undefined" && window.JS9 !== null;
}

/**
 * Type guard to check if a display has an image
 */
export function displayHasImage(
  display: JS9Display | null
): display is JS9Display & { im: JS9Image } {
  return display !== null && display.im !== null;
}

export {};
