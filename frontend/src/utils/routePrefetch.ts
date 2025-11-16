/**
 * Route prefetching utilities
 * Maps routes to their lazy-loaded components for prefetching on hover
 */

// Route to component mapping for prefetching
export const routeComponentMap: Record<string, () => Promise<any>> = {
  "/dashboard": () => import("../pages/DashboardPage"),
  "/pipeline": () => import("../pages/PipelinePage"),
  "/operations": () => import("../pages/OperationsPage"),
  "/control": () => import("../pages/ControlPage"),
  "/calibration": () => import("../pages/CalibrationWorkflowPage"),
  // "/ms-browser": MS Browser functionality merged into Control page
  // "/ms-browser": () => import("../pages/MSBrowserPage"),
  "/streaming": () => import("../pages/StreamingPage"),
  "/data": () => import("../pages/DataBrowserPage"),
  "/sources": () => import("../pages/SourceMonitoringPage"),
  "/mosaics": () => import("../pages/MosaicGalleryPage"),
  "/sky": () => import("../pages/SkyViewPage"),
  "/carta": () => import("../pages/CARTAPage"),
  "/qa": () => import("../pages/QAVisualizationPage"),
  "/health": () => import("../pages/HealthPage"),
  "/events": () => import("../pages/EventsPage"),
  "/cache": () => import("../pages/CachePage"),
  "/observing": () => import("../pages/ObservingPage"),
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
