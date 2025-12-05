/**
 * Centralized Constants Exports
 *
 * Import constants from this barrel file:
 * import { ROUTES, CATALOG_DEFINITIONS, errorMappings } from '../constants';
 *
 * For configuration (env vars, feature flags), use:
 * import { config } from '../config';
 */

// Route definitions
export { ROUTES, isRouteActive, NAV_ITEMS } from "./routes";
export type { NavItem, RouteParams } from "./routes";

// Astronomical constants
export {
  GALACTIC_POLE,
  EARTH_OBLIQUITY_DEG,
  DEG_TO_RAD,
  RAD_TO_DEG,
  HOURS_TO_DEG,
  DEG_TO_HOURS,
  VIEWER_TIMEOUTS,
  ANIMATION_DEFAULTS,
  SEARCH_DEFAULTS,
  CHART_DEFAULTS,
} from "./astronomical";

// Catalog definitions
export { CATALOG_DEFINITIONS } from "./catalogDefinitions";
export type { CatalogDefinition } from "./catalogDefinitions";

// Error mappings
export { errorMappings } from "./errorMappings";
export type { ErrorMapping } from "./errorMappings";
