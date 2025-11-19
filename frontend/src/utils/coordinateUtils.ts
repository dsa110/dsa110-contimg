/**
 * Coordinate utilities for astronomy
 */

/**
 * Convert decimal degrees to HMS format (HH:MM:SS.ss)
 * @param ra Right Ascension in decimal degrees
 * @param precision Number of decimal places for seconds
 * @returns Formatted string
 */
export const formatRA = (ra: number, precision: number = 2): string => {
  if (ra < 0 || ra >= 360) return "Invalid RA";

  const hours = Math.floor(ra / 15);
  const minutes = Math.floor((ra / 15 - hours) * 60);
  const seconds = ((ra / 15 - hours) * 60 - minutes) * 60;

  return `${hours.toString().padStart(2, "0")}:${minutes
    .toString()
    .padStart(2, "0")}:${seconds.toFixed(precision).padStart(3 + precision, "0")}`;
};

/**
 * Convert decimal degrees to DMS format (+DD:MM:SS.ss)
 * @param dec Declination in decimal degrees
 * @param precision Number of decimal places for seconds
 * @returns Formatted string
 */
export const formatDec = (dec: number, precision: number = 2): string => {
  if (dec < -90 || dec > 90) return "Invalid Dec";

  const sign = dec >= 0 ? "+" : "-";
  const absDec = Math.abs(dec);
  const degrees = Math.floor(absDec);
  const minutes = Math.floor((absDec - degrees) * 60);
  const seconds = ((absDec - degrees) * 60 - minutes) * 60;

  return `${sign}${degrees.toString().padStart(2, "0")}:${minutes
    .toString()
    .padStart(2, "0")}:${seconds.toFixed(precision).padStart(3 + precision, "0")}`;
};

/**
 * Copy text to clipboard
 */
export const copyToClipboard = (text: string): Promise<void> => {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  } else {
    // Fallback for non-secure contexts
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-9999px";
    textArea.style.top = "0";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    return new Promise((resolve, reject) => {
      try {
        document.execCommand("copy");
        textArea.remove();
        resolve();
      } catch (error) {
        reject(error);
      }
    });
  }
};
