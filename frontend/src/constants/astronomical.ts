/**
 * Astronomical Constants
 *
 * Standard astronomical constants used throughout the application.
 * All values are for J2000.0 epoch unless otherwise noted.
 *
 * References:
 * - IAU (International Astronomical Union) recommendations
 * - IERS Conventions (2010)
 */

// =============================================================================
// Coordinate System Constants
// =============================================================================

/**
 * North Galactic Pole coordinates (J2000.0)
 * Used for galactic-to-equatorial coordinate transformations.
 */
export const GALACTIC_POLE = {
  /** Right Ascension of the North Galactic Pole in degrees */
  RA_DEG: 192.85948,
  /** Declination of the North Galactic Pole in degrees */
  DEC_DEG: 27.12825,
  /** Galactic longitude of the ascending node in degrees */
  L_ASCENDING_NODE_DEG: 32.93192,
} as const;

/**
 * Earth's obliquity (axial tilt) in degrees (J2000.0)
 * Used for ecliptic-to-equatorial coordinate transformations.
 */
export const EARTH_OBLIQUITY_DEG = 23.4392911;

// =============================================================================
// Conversion Factors
// =============================================================================

/** Degrees to radians conversion factor */
export const DEG_TO_RAD = Math.PI / 180;

/** Radians to degrees conversion factor */
export const RAD_TO_DEG = 180 / Math.PI;

/** Hours to degrees conversion factor (for RA) */
export const HOURS_TO_DEG = 15;

/** Degrees to hours conversion factor (for RA) */
export const DEG_TO_HOURS = 1 / 15;

// =============================================================================
// Viewer Defaults
// =============================================================================

/**
 * Default timeout values for external library loading (in milliseconds)
 */
export const VIEWER_TIMEOUTS = {
  /** Timeout for JS9 FITS viewer to load */
  JS9_LOAD_MS: 10000,
  /** Polling interval to check if JS9 is ready */
  JS9_POLL_INTERVAL_MS: 100,
  /** Timeout for Aladin Lite to initialize */
  ALADIN_INIT_MS: 10000,
} as const;

/**
 * Default animation settings
 */
export const ANIMATION_DEFAULTS = {
  /** Default frame delay for GIF playback in milliseconds */
  FRAME_DELAY_MS: 100,
  /** Default playback speed multiplier */
  SPEED_MULTIPLIER: 1,
} as const;

// =============================================================================
// Search and Query Defaults
// =============================================================================

/**
 * Default search parameters
 */
export const SEARCH_DEFAULTS = {
  /** Default catalog search radius in arcminutes */
  CATALOG_RADIUS_ARCMIN: 5,
  /** Maximum catalog search radius in arcminutes */
  MAX_CATALOG_RADIUS_ARCMIN: 30,
  /** Default crossmatch radius in arcseconds */
  CROSSMATCH_RADIUS_ARCSEC: 5,
} as const;

// =============================================================================
// Chart and Visualization Defaults
// =============================================================================

/**
 * Default chart dimensions
 */
export const CHART_DEFAULTS = {
  /** Default height for ECharts components */
  HEIGHT_PX: 300,
  /** Minimum height for responsive charts */
  MIN_HEIGHT_PX: 200,
  /** Maximum height for responsive charts */
  MAX_HEIGHT_PX: 600,
} as const;

/**
 * Service health check configuration
 */
export const HEALTH_CHECK_DEFAULTS = {
  /** Interval between health checks in milliseconds */
  INTERVAL_MS: 30000,
  /** Number of consecutive failures before marking unhealthy */
  FAILURE_THRESHOLD: 3,
} as const;
