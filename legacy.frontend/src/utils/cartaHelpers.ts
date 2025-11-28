/**
 * CARTA Helper Functions
 *
 * Utilities for generating CARTA URLs and navigating to CARTA with files
 */

/**
 * Generate CARTA URL with file path parameter
 *
 * @param filePath - Path to FITS file (absolute or relative)
 * @param mode - Integration mode: 'iframe' or 'websocket'
 * @returns URL to CARTA page with file parameter
 */
export function getCartaUrl(filePath: string, mode: "iframe" | "websocket" = "iframe"): string {
  const baseUrl = "/carta";
  const params = new URLSearchParams();

  // Add file path as query parameter
  params.set("file", filePath);

  // Add mode if specified
  if (mode) {
    params.set("mode", mode);
  }

  return `${baseUrl}?${params.toString()}`;
}

/**
 * Check if a file path is a FITS file
 *
 * @param filePath - File path to check
 * @returns True if file is a FITS file
 */
export function isFitsFile(filePath: string): boolean {
  const fitsExtensions = [".fits", ".fits.gz", ".fit", ".fts"];
  const lowerPath = filePath.toLowerCase();
  return fitsExtensions.some((ext) => lowerPath.endsWith(ext));
}

/**
 * Check if a file path is a CASA table
 *
 * @param filePath - File path to check
 * @returns True if file is a CASA table
 */
export function isCasaTable(filePath: string): boolean {
  // CASA tables are directories, but we can check for common table names
  const casaTableNames = ["SPECTRAL_WINDOW", "FIELD", "ANTENNA", "DATA_DESCRIPTION"];
  const pathParts = filePath.split("/");
  const lastPart = pathParts[pathParts.length - 1];
  return casaTableNames.some((name) => lastPart.includes(name));
}
