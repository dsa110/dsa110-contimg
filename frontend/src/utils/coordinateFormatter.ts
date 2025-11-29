/**
 * Format Right Ascension from decimal degrees to HMS (hours:minutes:seconds).
 * @param raDeg - RA in decimal degrees (0-360)
 * @param precision - decimal places for seconds (default: 2)
 */
export const formatRA = (raDeg: number, precision: number = 2): string => {
  const totalHours = raDeg / 15;
  const hours = Math.floor(totalHours);
  const totalMinutes = (totalHours - hours) * 60;
  const minutes = Math.floor(totalMinutes);
  const seconds = (totalMinutes - minutes) * 60;
  return `${hours.toString().padStart(2, "0")}h ${minutes.toString().padStart(2, "0")}m ${seconds
    .toFixed(precision)
    .padStart(precision + 3, "0")}s`;
};

/**
 * Format Declination from decimal degrees to DMS (degrees:arcmin:arcsec).
 * @param decDeg - Dec in decimal degrees (-90 to +90)
 * @param precision - decimal places for arcseconds (default: 1)
 */
export const formatDec = (decDeg: number, precision: number = 1): string => {
  const sign = decDeg >= 0 ? "+" : "-";
  const absDec = Math.abs(decDeg);
  const degrees = Math.floor(absDec);
  const totalArcmin = (absDec - degrees) * 60;
  const arcmin = Math.floor(totalArcmin);
  const arcsec = (totalArcmin - arcmin) * 60;
  return `${sign}${degrees.toString().padStart(2, "0")}° ${arcmin
    .toString()
    .padStart(2, "0")}′ ${arcsec.toFixed(precision).padStart(precision + 3, "0")}″`;
};

/**
 * Format coordinates as a compact string for display.
 * @param raDeg - RA in decimal degrees
 * @param decDeg - Dec in decimal degrees
 */
export const formatCoordinates = (raDeg: number, decDeg: number): string => {
  return `${formatRA(raDeg, 1)}, ${formatDec(decDeg, 0)}`;
};

/**
 * Format decimal degrees with specified precision.
 * @param deg - Value in degrees
 * @param precision - decimal places (default: 4)
 */
export const formatDegrees = (deg: number, precision: number = 4): string => {
  return `${deg.toFixed(precision)}°`;
};
