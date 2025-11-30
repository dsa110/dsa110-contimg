/**
 * Centralized route constants.
 *
 * All application routes should be defined here to ensure consistency
 * and prevent hardcoded strings throughout the codebase.
 *
 * Usage:
 *   import { ROUTES } from '../constants/routes';
 *   <Link to={ROUTES.IMAGES.LIST}>Images</Link>
 *   <Link to={ROUTES.IMAGES.DETAIL(imageId)}>View Image</Link>
 */

/**
 * Application route definitions.
 */
export const ROUTES = {
  /** Home/dashboard page */
  HOME: "/",

  /** Image routes */
  IMAGES: {
    /** Images list page */
    LIST: "/images",
    /** Image detail page */
    DETAIL: (id: string) => `/images/${encodeURIComponent(id)}` as const,
  },

  /** Source routes */
  SOURCES: {
    /** Sources list page */
    LIST: "/sources",
    /** Source detail page */
    DETAIL: (id: string) => `/sources/${encodeURIComponent(id)}` as const,
  },

  /** Job routes */
  JOBS: {
    /** Jobs list page */
    LIST: "/jobs",
    /** Job detail page */
    DETAIL: (runId: string) => `/jobs/${encodeURIComponent(runId)}` as const,
  },

  /** Measurement Set routes */
  MS: {
    /** MS detail page */
    DETAIL: (path: string) => `/ms/${encodeURIComponent(path)}` as const,
  },

  /** Internal/utility routes */
  INTERNAL: {
    /** Calibration table detail */
    CAL: (table: string) => `/cal/${encodeURIComponent(table)}` as const,
    /** Job logs */
    LOGS: (runId: string) => `/logs/${runId}` as const,
    /** QA report for image */
    QA_IMAGE: (id: string) => `/qa/image/${id}` as const,
    /** QA report for MS */
    QA_MS: (path: string) => `/qa/ms/${encodeURIComponent(path)}` as const,
  },
} as const;

/**
 * Navigation items for the main menu.
 * Used by AppLayout and other navigation components.
 */
export const NAV_ITEMS = [
  { path: ROUTES.HOME, label: "Home" },
  { path: ROUTES.IMAGES.LIST, label: "Images" },
  { path: ROUTES.SOURCES.LIST, label: "Sources" },
  { path: ROUTES.JOBS.LIST, label: "Jobs" },
] as const;

/**
 * Helper to check if a path matches a route (for active state).
 * @param currentPath Current location pathname
 * @param routePath Route path to check
 * @returns Whether the route is active
 */
export function isRouteActive(currentPath: string, routePath: string): boolean {
  if (routePath === ROUTES.HOME) {
    return currentPath === ROUTES.HOME;
  }
  return currentPath.startsWith(routePath);
}

/**
 * Type for route path values.
 */
export type RoutePath = string;
