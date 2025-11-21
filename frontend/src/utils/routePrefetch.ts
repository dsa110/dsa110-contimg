/**
 * Route prefetching utilities
 * Maps routes to their lazy-loaded components for prefetching on hover
 */

// Route to component mapping for prefetching
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const routeComponentMap: Record<string, () => Promise<any>> = {
  "/dashboard": () => import("../pages/DashboardPage"),
  "/pipeline": () => import("../pages/PipelinePage"),
  "/operations": () => import("../pages/PipelineOperationsPage"),
  "/control": () => import("../pages/PipelineControlPage"),
  "/calibration": () => import("../pages/CalibrationWorkflowPage"),
  "/data": () => import("../pages/DataBrowserPage"),
  "/sources": () => import("../pages/SourceMonitoringPage"),
  "/mosaics": () => import("../pages/MosaicGalleryPage"),
  "/sky": () => import("../pages/SkyViewPage"),
  "/carta": () => import("../pages/CARTAPage"),
  "/qa": () => import("../pages/QAPage"),
  "/system-status": () => import("../pages/SystemStatusPage"),
  "/health": () => import("../pages/SystemDiagnosticsPage"),
  "/events": () => import("../pages/EventsPage"),
};

/**
 * Prefetch a route component on hover
 * @param path - Route path to prefetch
 */
export function prefetchRoute(path: string): void {
  const prefetchFn = routeComponentMap[path];
  if (prefetchFn) {
    // Prefetch the component module
    prefetchFn().catch(() => {
      // Silently handle errors (component may already be loading)
    });
  }
}
