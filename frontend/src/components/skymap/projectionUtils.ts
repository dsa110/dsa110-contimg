/**
 * Sky Map Projection and Coordinate Transformation Utilities
 *
 * This module provides coordinate system transformations and projection setup
 * for astronomical sky maps. Extracted from SkyCoverageMap for better maintainability.
 */

import * as d3 from "d3";
import { geoAitoff, geoHammer, geoMollweide } from "d3-geo-projection";
import {
  GALACTIC_POLE,
  EARTH_OBLIQUITY_DEG,
  DEG_TO_RAD,
  RAD_TO_DEG,
} from "../../constants/astronomical";

export type ProjectionType = "aitoff" | "mollweide" | "hammer" | "mercator";

/**
 * Convert galactic coordinates (l, b) to equatorial (RA, Dec) in degrees.
 * Uses the standard IAU transformation.
 *
 * @param l - Galactic longitude in degrees
 * @param b - Galactic latitude in degrees
 * @returns [RA, Dec] in degrees
 */
export function galacticToEquatorial(l: number, b: number): [number, number] {
  const lRad = l * DEG_TO_RAD;
  const bRad = b * DEG_TO_RAD;

  // North Galactic Pole (J2000) coordinates
  const raGP = GALACTIC_POLE.RA_DEG * DEG_TO_RAD;
  const decGP = GALACTIC_POLE.DEC_DEG * DEG_TO_RAD;
  const lAscend = GALACTIC_POLE.L_ASCENDING_NODE_DEG * DEG_TO_RAD;

  const sinDec =
    Math.sin(bRad) * Math.sin(decGP) + Math.cos(bRad) * Math.cos(decGP) * Math.sin(lRad - lAscend);
  const dec = Math.asin(sinDec);

  const y = Math.cos(bRad) * Math.cos(lRad - lAscend);
  const x =
    Math.sin(bRad) * Math.cos(decGP) - Math.cos(bRad) * Math.sin(decGP) * Math.sin(lRad - lAscend);

  let ra = raGP + Math.atan2(y, x);

  // Normalize RA to [0, 360)
  ra = ((ra * RAD_TO_DEG % 360) + 360) % 360;
  const decDeg = dec * RAD_TO_DEG;

  return [ra, decDeg];
}

/**
 * Calculate ecliptic coordinates as equatorial (RA, Dec).
 * The ecliptic is the Sun's apparent path through the sky.
 *
 * @param eclipticLon - Ecliptic longitude in degrees
 * @returns [RA, Dec] in degrees
 */
export function eclipticToEquatorial(eclipticLon: number): [number, number] {
  const oblRad = EARTH_OBLIQUITY_DEG * DEG_TO_RAD;
  const lonRad = eclipticLon * DEG_TO_RAD;

  // Convert from ecliptic to equatorial
  const sinDec = Math.sin(lonRad) * Math.sin(oblRad);
  const dec = Math.asin(sinDec) * RAD_TO_DEG;

  const y = Math.sin(lonRad) * Math.cos(oblRad);
  const x = Math.cos(lonRad);
  let ra = Math.atan2(y, x) * RAD_TO_DEG;

  // Normalize RA to [0, 360)
  ra = ((ra % 360) + 360) % 360;

  return [ra, dec];
}

/**
 * Generate galactic plane coordinates
 *
 * @param numPoints - Number of points to generate along the galactic plane
 * @returns Array of [RA, Dec] coordinates in degrees
 */
export function generateGalacticPlane(numPoints = 360): Array<[number, number]> {
  const galacticPlane: Array<[number, number]> = [];

  for (let l = 0; l <= 360; l += 360 / numPoints) {
    const [ra, dec] = galacticToEquatorial(l, 0);
    galacticPlane.push([ra, dec]);
  }

  return galacticPlane;
}

/**
 * Generate ecliptic path coordinates
 *
 * @param numPoints - Number of points to generate along the ecliptic
 * @returns Array of [RA, Dec] coordinates in degrees
 */
export function generateEcliptic(numPoints = 360): Array<[number, number]> {
  const ecliptic: Array<[number, number]> = [];

  for (let lon = 0; lon <= 360; lon += 360 / numPoints) {
    const [ra, dec] = eclipticToEquatorial(lon);
    ecliptic.push([ra, dec]);
  }

  return ecliptic;
}

/**
 * Create a D3 projection based on the specified type
 *
 * @param type - Type of projection to create
 * @param width - Width of the projection area
 * @param height - Height of the projection area
 * @returns Configured D3 projection
 */
export function createProjection(
  type: ProjectionType,
  width: number,
  height: number
): d3.GeoProjection {
  let projection: d3.GeoProjection;

  switch (type) {
    case "aitoff":
      projection = geoAitoff();
      break;
    case "mollweide":
      projection = geoMollweide();
      break;
    case "hammer":
      projection = geoHammer();
      break;
    case "mercator":
      projection = d3.geoMercator();
      break;
    default:
      projection = geoAitoff();
  }

  return projection
    .scale((width / 2 / Math.PI) * 0.95)
    .translate([width / 2, height / 2])
    .precision(0.1);
}

/**
 * Convert RA/Dec to projection coordinates
 *
 * @param ra - Right Ascension in degrees
 * @param dec - Declination in degrees
 * @param projection - D3 projection to use
 * @returns [x, y] pixel coordinates or null if not projectable
 */
export function projectCoordinates(
  ra: number,
  dec: number,
  projection: d3.GeoProjection
): [number, number] | null {
  // Convert RA (0-360) to longitude (-180 to 180)
  const lon = ra > 180 ? ra - 360 : ra;
  const coords = projection([lon, dec]);
  return coords as [number, number] | null;
}

/**
 * Create path data for a circle at specified coordinates
 *
 * @param ra - Center RA in degrees
 * @param dec - Center Dec in degrees
 * @param radius - Radius in degrees
 * @param projection - D3 projection to use
 * @param numPoints - Number of points to generate for the circle
 * @returns SVG path data string
 */
export function createCirclePath(
  ra: number,
  dec: number,
  radius: number,
  projection: d3.GeoProjection,
  numPoints = 32
): string {
  const points: Array<[number, number]> = [];

  for (let i = 0; i <= numPoints; i++) {
    const angle = (i / numPoints) * 2 * Math.PI;
    // Approximate circle in sky coordinates (this is simplified)
    const raOffset = (radius * Math.cos(angle)) / Math.cos((dec * Math.PI) / 180);
    const decOffset = radius * Math.sin(angle);

    const ptRa = ra + raOffset;
    const ptDec = Math.max(-90, Math.min(90, dec + decOffset));

    const projected = projectCoordinates(ptRa, ptDec, projection);
    if (projected) {
      points.push(projected);
    }
  }

  if (points.length === 0) return "";

  const pathData = points
    .map((p, i) => (i === 0 ? `M ${p[0]},${p[1]}` : `L ${p[0]},${p[1]}`))
    .join(" ");

  return pathData + " Z";
}
