/**
 * Parse astronomical coordinates from various formats.
 * Supports decimal degrees, HMS (hours:minutes:seconds) for RA,
 * and DMS (degrees:minutes:seconds) for Dec.
 */

/**
 * Parse RA from various formats to decimal degrees.
 * Accepts:
 * - Decimal degrees: 180.5
 * - HMS with colons: 12:30:00 or 12:30:00.0
 * - HMS with letters: 12h30m00s
 * - HMS with spaces: 12 30 00
 *
 * @returns RA in decimal degrees [0, 360) or null if invalid
 */
export function parseRA(input: string): number | null {
  if (!input || typeof input !== "string") return null;

  const trimmed = input.trim();
  if (!trimmed) return null;

  // Try decimal degrees first
  const decimal = parseFloat(trimmed);
  if (!isNaN(decimal) && !trimmed.includes(":") && !trimmed.match(/[hms°'"]/i)) {
    // Validate range
    if (decimal >= 0 && decimal < 360) {
      return decimal;
    }
    // Could be hours if in [0, 24)
    if (decimal >= 0 && decimal < 24) {
      return decimal * 15; // Convert hours to degrees
    }
    return null;
  }

  // Try HMS format
  const hmsMatch = trimmed.match(
    /^(\d{1,2})(?:h|:|\s)\s*(\d{1,2})(?:m|:|\s)\s*(\d{1,2}(?:\.\d+)?)\s*s?$/i
  );

  if (hmsMatch) {
    const hours = parseInt(hmsMatch[1], 10);
    const minutes = parseInt(hmsMatch[2], 10);
    const seconds = parseFloat(hmsMatch[3]);

    if (hours >= 0 && hours < 24 && minutes >= 0 && minutes < 60 && seconds >= 0 && seconds < 60) {
      const totalHours = hours + minutes / 60 + seconds / 3600;
      return totalHours * 15; // Convert hours to degrees
    }
  }

  // Try short HMS (no seconds): 12:30 or 12h30m
  const hmsShortMatch = trimmed.match(/^(\d{1,2})(?:h|:|\s)\s*(\d{1,2})(?:m)?$/i);

  if (hmsShortMatch) {
    const hours = parseInt(hmsShortMatch[1], 10);
    const minutes = parseInt(hmsShortMatch[2], 10);

    if (hours >= 0 && hours < 24 && minutes >= 0 && minutes < 60) {
      const totalHours = hours + minutes / 60;
      return totalHours * 15;
    }
  }

  return null;
}

/**
 * Parse Dec from various formats to decimal degrees.
 * Accepts:
 * - Decimal degrees: +45.5 or -45.5
 * - DMS with colons: +45:30:00 or -45:30:00
 * - DMS with symbols: +45°30'00" or 45d30m00s
 * - DMS with spaces: +45 30 00
 *
 * @returns Dec in decimal degrees [-90, 90] or null if invalid
 */
export function parseDec(input: string): number | null {
  if (!input || typeof input !== "string") return null;

  const trimmed = input.trim();
  if (!trimmed) return null;

  // Determine sign
  let sign = 1;
  let working = trimmed;

  if (working.startsWith("-")) {
    sign = -1;
    working = working.slice(1).trim();
  } else if (working.startsWith("+")) {
    working = working.slice(1).trim();
  }

  // Try decimal degrees first
  const decimal = parseFloat(working);
  if (!isNaN(decimal) && !working.includes(":") && !working.match(/[dms°'"]/i)) {
    const result = sign * decimal;
    if (result >= -90 && result <= 90) {
      return result;
    }
    return null;
  }

  // Try DMS format
  const dmsMatch = working.match(
    /^(\d{1,2})(?:d|°|:|\s)\s*(\d{1,2})(?:m|'|:|\s)\s*(\d{1,2}(?:\.\d+)?)\s*(?:s|")?$/i
  );

  if (dmsMatch) {
    const degrees = parseInt(dmsMatch[1], 10);
    const minutes = parseInt(dmsMatch[2], 10);
    const seconds = parseFloat(dmsMatch[3]);

    if (
      degrees >= 0 &&
      degrees <= 90 &&
      minutes >= 0 &&
      minutes < 60 &&
      seconds >= 0 &&
      seconds < 60
    ) {
      const totalDegrees = degrees + minutes / 60 + seconds / 3600;
      const result = sign * totalDegrees;
      if (result >= -90 && result <= 90) {
        return result;
      }
    }
  }

  // Try short DMS (no seconds): +45:30 or 45d30m
  const dmsShortMatch = working.match(/^(\d{1,2})(?:d|°|:|\s)\s*(\d{1,2})(?:m|')?$/i);

  if (dmsShortMatch) {
    const degrees = parseInt(dmsShortMatch[1], 10);
    const minutes = parseInt(dmsShortMatch[2], 10);

    if (degrees >= 0 && degrees <= 90 && minutes >= 0 && minutes < 60) {
      const totalDegrees = degrees + minutes / 60;
      const result = sign * totalDegrees;
      if (result >= -90 && result <= 90) {
        return result;
      }
    }
  }

  return null;
}

/**
 * Format RA in decimal degrees to HMS string.
 */
export function formatRAtoHMS(ra: number): string {
  const totalHours = ra / 15;
  const hours = Math.floor(totalHours);
  const remainingMinutes = (totalHours - hours) * 60;
  const minutes = Math.floor(remainingMinutes);
  const seconds = (remainingMinutes - minutes) * 60;

  return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds
    .toFixed(2)
    .padStart(5, "0")}`;
}

/** Alias for formatRAtoHMS */
export const formatRA = formatRAtoHMS;

/**
 * Format Dec in decimal degrees to DMS string.
 */
export function formatDectoDMS(dec: number): string {
  const sign = dec >= 0 ? "+" : "-";
  const absDec = Math.abs(dec);
  const degrees = Math.floor(absDec);
  const remainingMinutes = (absDec - degrees) * 60;
  const minutes = Math.floor(remainingMinutes);
  const seconds = (remainingMinutes - minutes) * 60;

  return `${sign}${degrees.toString().padStart(2, "0")}:${minutes
    .toString()
    .padStart(2, "0")}:${seconds.toFixed(1).padStart(4, "0")}`;
}

/** Alias for formatDectoDMS */
export const formatDec = formatDectoDMS;

/**
 * Parse a coordinate pair string (RA and Dec together).
 * Accepts formats like:
 * - "180.0, 45.5"
 * - "12:00:00, +45:30:00"
 * - "12:00:00 +45:30:00"
 */
export function parseCoordinatePair(input: string): { ra: number; dec: number } | null {
  if (!input || typeof input !== "string") return null;

  const trimmed = input.trim();
  if (!trimmed) return null;

  // Try comma-separated
  if (trimmed.includes(",")) {
    const parts = trimmed.split(",").map((s) => s.trim());
    if (parts.length === 2) {
      const ra = parseRA(parts[0]);
      const dec = parseDec(parts[1]);
      if (ra !== null && dec !== null) {
        return { ra, dec };
      }
    }
  }

  // Try space-separated (look for sign in second part)
  const signMatch = trimmed.match(/^(.+?)\s+([+-]?\d.*)$/);
  if (signMatch) {
    const ra = parseRA(signMatch[1].trim());
    const dec = parseDec(signMatch[2].trim());
    if (ra !== null && dec !== null) {
      return { ra, dec };
    }
  }

  return null;
}

/**
 * Validate coordinates are in valid range.
 */
export function validateCoordinates(
  ra: number | null,
  dec: number | null
): {
  valid: boolean;
  raError?: string;
  decError?: string;
} {
  const result: { valid: boolean; raError?: string; decError?: string } = { valid: true };

  if (ra !== null) {
    if (ra < 0 || ra >= 360) {
      result.valid = false;
      result.raError = "RA must be between 0 and 360 degrees";
    }
  }

  if (dec !== null) {
    if (dec < -90 || dec > 90) {
      result.valid = false;
      result.decError = "Dec must be between -90 and 90 degrees";
    }
  }

  return result;
}
