/**
 * Shared region types for FITS tools and API payloads.
 */

export type RegionShape = "circle" | "box" | "ellipse" | "polygon" | "point";

export type RegionFormat = "ds9" | "crtf" | "json";

export interface Region {
  id: string;
  shape: RegionShape;
  x: number;
  y: number;
  radius?: number;
  width?: number;
  height?: number;
  points?: Array<{ x: number; y: number }>;
  text?: string;
  color?: string;
}

