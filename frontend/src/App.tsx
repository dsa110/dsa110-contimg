import { useState, lazy, Suspense, useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { ThemeProvider, CssBaseline, Box, CircularProgress, Alert } from "@mui/material";
import { env } from "./config/env";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { darkTheme } from "./theme/darkTheme";
import { NotificationProvider } from "./contexts/NotificationContext";
import { JS9Provider } from "./contexts/JS9Context";
import { WorkflowProvider } from "./contexts/WorkflowContext";
import Navigation from "./components/Navigation";
import WorkflowBreadcrumbs from "./components/WorkflowBreadcrumbs";
import ErrorBoundary from "./components/ErrorBoundary";
import { LoadingProgress } from "./components/LoadingProgress";
import { OfflineIndicator } from "./components/OfflineIndicator";
import { isRetryableError } from "./utils/errorUtils";
import { initErrorTracking } from "./utils/errorTracking";
import { registerServiceWorker } from "./utils/serviceWorker";

// Lazy load all page components for code splitting
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
// Merged pages - consolidated functionality
const PipelineControlPage = lazy(() => import("./pages/PipelineControlPage"));
const PipelineOperationsPage = lazy(() => import("./pages/PipelineOperationsPage"));
const SystemDiagnosticsPage = lazy(() => import("./pages/SystemDiagnosticsPage"));
const QAPage = lazy(() => import("./pages/QAPage"));

// Component pages (used within consolidated pages, not as standalone routes)
const ControlPage = lazy(() => import("./pages/ControlPage"));
const StreamingPage = lazy(() => import("./pages/StreamingPage"));
const ObservingPage = lazy(() => import("./pages/ObservingPage"));
const HealthPage = lazy(() => import("./pages/HealthPage"));
const CachePage = lazy(() => import("./pages/CachePage"));

// Other pages
const MosaicGalleryPage = lazy(() => import("./pages/MosaicGalleryPage"));
const MosaicViewPage = lazy(() => import("./pages/MosaicViewPage"));
const SourceMonitoringPage = lazy(() => import("./pages/SourceMonitoringPage"));
const SourceDetailPage = lazy(() => import("./pages/SourceDetailPage"));
const ImageDetailPage = lazy(() => import("./pages/ImageDetailPage"));
const SkyViewPage = lazy(() => import("./pages/SkyViewPage"));
const DataBrowserPage = lazy(() => import("./pages/DataBrowserPage"));
const DataDetailPage = lazy(() => import("./pages/DataDetailPage"));
const CARTAPage = lazy(() => import("./pages/CARTAPage"));
const PipelinePage = lazy(() => import("./pages/PipelinePage"));
const EventsPage = lazy(() => import("./pages/EventsPage"));
const DataLineagePage = lazy(() => import("./pages/DataLineagePage"));
const CalibrationWorkflowPage = lazy(() => import("./pages/CalibrationWorkflowPage"));
const ErrorAnalyticsPage = lazy(() => import("./pages/ErrorAnalyticsPage"));

// Loading fallback component
function PageLoadingFallback() {
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "400px",
        width: "100%",
      }}
    >
      <CircularProgress />
    </Box>
  );
}

// Create React Query client factory function with optimized staleTime strategy
function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: (failureCount, error) => {
          // Retry up to 3 times, but only for retryable errors
          if (failureCount >= 3) {
            return false;
          }
          // Safely check if error is retryable, return false if check fails
          try {
            return isRetryableError(error);
          } catch {
            return false;
          }
        },
        retryDelay: (attemptIndex) => {
          // Exponential backoff: 1s, 2s, 4s
          return Math.min(1000 * Math.pow(2, attemptIndex), 10000);
        },
        refetchOnWindowFocus: false,
        // Strategic staleTime: shorter for dynamic data, longer for static data
        // Individual queries can override this with longer staleTime for static data
        staleTime: 30000, // 30 seconds default (for dynamic data)
        // Cache time: keep unused data for 5 minutes
        gcTime: 300000, // 5 minutes (formerly cacheTime)
      },
      mutations: {
        retry: (failureCount, error) => {
          // Mutations: retry once for retryable errors
          if (failureCount >= 1) {
            return false;
          }
          // Safely check if error is retryable, return false if check fails
          try {
            return isRetryableError(error);
          } catch {
            return false;
          }
        },
        retryDelay: 1000,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined = undefined;

function getQueryClient() {
  if (typeof window === "undefined") {
    // Server: always make a new query client
    return makeQueryClient();
  }
  // Browser: make a new query client if we don't already have one
  if (!browserQueryClient) browserQueryClient = makeQueryClient();
  return browserQueryClient;
}

function AppContent() {
  // Use useState with lazy initialization to ensure QueryClient is only created once
  // This ensures QueryClient is stable across re-renders and properly initialized
  const [queryClient] = useState(() => {
    try {
      return getQueryClient();
    } catch (error) {
      // If QueryClient creation fails, create a new one as fallback
      console.error("Failed to get QueryClient, creating new one:", error);
      return makeQueryClient();
    }
  });

  // Set basename for production builds served from /ui/
  // Ensure basename is always a string or undefined (never an object)
  // Use explicit type guard to prevent object coercion errors in React Router
  const basename: string | undefined = env.PROD ? "/ui" : undefined;

  // Initialize error tracking and service worker
  useEffect(() => {
    // Initialize error tracking (Sentry) if DSN is provided
    if (env.VITE_SENTRY_DSN) {
      initErrorTracking(env.VITE_SENTRY_DSN);
    }

    // Register service worker for offline support
    if (env.PROD) {
      registerServiceWorker();
    }
  }, []);

  // Ensure QueryClient is valid before rendering
  if (!queryClient) {
    console.error("QueryClient is null, creating new one");
    const fallbackClient = makeQueryClient();
    return (
      <ErrorBoundary>
        <QueryClientProvider client={fallbackClient}>
          <ThemeProvider theme={darkTheme}>
            <CssBaseline />
            <Box sx={{ p: 3 }}>
              <Alert severity="warning">
                QueryClient initialization error. Please refresh the page.
              </Alert>
            </Box>
          </ThemeProvider>
        </QueryClientProvider>
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        {env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
        <ThemeProvider theme={darkTheme}>
          <CssBaseline />
          <NotificationProvider>
            <JS9Provider>
              <BrowserRouter basename={basename}>
                <WorkflowProvider>
                  <LoadingProgress />
                  <OfflineIndicator />
                  <Box
                    sx={{
                      display: "flex",
                      flexDirection: "column",
                      minHeight: "100vh",
                      width: "100%",
                    }}
                  >
                    <Box sx={{ width: "100%", margin: 0, padding: 0 }}>
                      <Navigation />
                    </Box>
                    <WorkflowBreadcrumbs />
                    <Box
                      component="main"
                      sx={{
                        flexGrow: 1,
                        width: "100%",
                        display: "flex",
                        justifyContent: "center",
                      }}
                    >
                      <Box
                        sx={{
                          width: "100%",
                          maxWidth: "1536px", // MUI xl breakpoint
                          px: { xs: 2, sm: 3, md: 4 },
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "stretch", // Stretch children to container width, but container respects maxWidth
                        }}
                      >
                        <ErrorBoundary>
                          <Suspense fallback={<PageLoadingFallback />}>
                            <Routes>
                              <Route path="/" element={<Navigate to="/dashboard" replace />} />
                              <Route path="/dashboard" element={<DashboardPage />} />
                              {/* Legacy route redirects */}
                              <Route
                                path="/pipeline-control"
                                element={<Navigate to="/control" replace />}
                              />
                              <Route
                                path="/pipeline-operations"
                                element={<Navigate to="/pipeline" replace />}
                              />
                              <Route
                                path="/data-explorer"
                                element={<Navigate to="/data" replace />}
                              />
                              <Route
                                path="/system-diagnostics"
                                element={<Navigate to="/health" replace />}
                              />
                              {/* Consolidated pages - primary routes */}
                              <Route path="/control" element={<PipelineControlPage />} />
                              <Route path="/operations" element={<PipelineOperationsPage />} />
                              <Route path="/health" element={<SystemDiagnosticsPage />} />
                              <Route path="/qa" element={<QAPage />} />

                              {/* Redirects - old routes to consolidated pages */}
                              <Route
                                path="/streaming"
                                element={<Navigate to="/control?tab=1" replace />}
                              />
                              <Route
                                path="/observing"
                                element={<Navigate to="/control?tab=2" replace />}
                              />
                              <Route
                                path="/cache"
                                element={<Navigate to="/health?tab=3" replace />}
                              />
                              <Route path="/qa/carta" element={<Navigate to="/qa" replace />} />
                              <Route
                                path="/ms-browser"
                                element={<Navigate to="/control" replace />}
                              />

                              {/* Other pages */}
                              <Route path="/mosaics" element={<MosaicGalleryPage />} />
                              <Route path="/mosaics/:mosaicId" element={<MosaicViewPage />} />
                              <Route path="/sources" element={<SourceMonitoringPage />} />
                              <Route path="/sources/:sourceId" element={<SourceDetailPage />} />
                              <Route path="/images/:imageId" element={<ImageDetailPage />} />
                              <Route path="/sky" element={<SkyViewPage />} />
                              <Route path="/data" element={<DataBrowserPage />} />
                              <Route path="/data/:type/:id" element={<DataDetailPage />} />
                              <Route path="/carta" element={<CARTAPage />} />
                              <Route path="/error-analytics" element={<ErrorAnalyticsPage />} />
                              <Route path="/pipeline" element={<PipelinePage />} />
                              <Route path="/events" element={<EventsPage />} />
                              {/* Domain-specific pages */}
                              <Route path="/lineage/:id" element={<DataLineagePage />} />
                              <Route path="/calibration" element={<CalibrationWorkflowPage />} />
                            </Routes>
                          </Suspense>
                        </ErrorBoundary>
                      </Box>
                    </Box>
                  </Box>
                </WorkflowProvider>
              </BrowserRouter>
            </JS9Provider>
          </NotificationProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

function App() {
  return <AppContent />;
}

export default App;
