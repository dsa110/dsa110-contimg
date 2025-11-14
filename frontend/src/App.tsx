import { useState, lazy, Suspense, useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { ThemeProvider, CssBaseline, Box, CircularProgress } from "@mui/material";
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
const ControlPage = lazy(() => import("./pages/ControlPage"));
const MosaicGalleryPage = lazy(() => import("./pages/MosaicGalleryPage"));
const MosaicViewPage = lazy(() => import("./pages/MosaicViewPage"));
const SourceMonitoringPage = lazy(() => import("./pages/SourceMonitoringPage"));
const SourceDetailPage = lazy(() => import("./pages/SourceDetailPage"));
const ImageDetailPage = lazy(() => import("./pages/ImageDetailPage"));
const SkyViewPage = lazy(() => import("./pages/SkyViewPage"));
const StreamingPage = lazy(() => import("./pages/StreamingPage"));
const DataBrowserPage = lazy(() => import("./pages/DataBrowserPage"));
const DataDetailPage = lazy(() => import("./pages/DataDetailPage"));
const QAVisualizationPage = lazy(() => import("./pages/QAVisualizationPage"));
const QACartaPage = lazy(() => import("./pages/QACartaPage"));
const CARTAPage = lazy(() => import("./pages/CARTAPage"));
const ObservingPage = lazy(() => import("./pages/ObservingPage"));
const HealthPage = lazy(() => import("./pages/HealthPage"));
const OperationsPage = lazy(() => import("./pages/OperationsPage"));
const PipelinePage = lazy(() => import("./pages/PipelinePage"));
const EventsPage = lazy(() => import("./pages/EventsPage"));
const CachePage = lazy(() => import("./pages/CachePage"));
const DataLineagePage = lazy(() => import("./pages/DataLineagePage"));
const CalibrationWorkflowPage = lazy(() => import("./pages/CalibrationWorkflowPage"));
const MSBrowserPage = lazy(() => import("./pages/MSBrowserPage"));
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
  const [queryClient] = useState(() => getQueryClient());

  // Set basename for production builds served from /ui/
  // Ensure basename is always a string or undefined (never an object)
  // Use explicit type guard to prevent object coercion errors in React Router
  const basename: string | undefined =
    typeof import.meta.env.PROD === "boolean" && import.meta.env.PROD ? "/ui" : undefined;

  // Initialize error tracking and service worker
  useEffect(() => {
    // Initialize error tracking (Sentry) if DSN is provided
    const sentryDsn = import.meta.env.VITE_SENTRY_DSN;
    if (sentryDsn) {
      initErrorTracking(sentryDsn);
    }

    // Register service worker for offline support
    if (import.meta.env.PROD) {
      registerServiceWorker();
    }
  }, []);

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
        <ThemeProvider theme={darkTheme}>
          <CssBaseline />
          <NotificationProvider>
            <JS9Provider>
              <BrowserRouter basename={basename}>
                <WorkflowProvider>
                  <LoadingProgress />
                  <OfflineIndicator />
                  <Box sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
                    <Navigation />
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
                              <Route path="/control" element={<ControlPage />} />
                              <Route path="/mosaics" element={<MosaicGalleryPage />} />
                              <Route path="/mosaics/:mosaicId" element={<MosaicViewPage />} />
                              <Route path="/sources" element={<SourceMonitoringPage />} />
                              <Route path="/sources/:sourceId" element={<SourceDetailPage />} />
                              <Route path="/images/:imageId" element={<ImageDetailPage />} />
                              <Route path="/sky" element={<SkyViewPage />} />
                              <Route path="/streaming" element={<StreamingPage />} />
                              <Route path="/data" element={<DataBrowserPage />} />
                              <Route path="/data/:type/:id" element={<DataDetailPage />} />
                              <Route path="/qa" element={<QAVisualizationPage />} />
                              <Route path="/qa/carta" element={<QACartaPage />} />
                              <Route path="/carta" element={<CARTAPage />} />
                              <Route path="/observing" element={<ObservingPage />} />
                              <Route path="/health" element={<HealthPage />} />
                              <Route path="/operations" element={<OperationsPage />} />
                              <Route path="/error-analytics" element={<ErrorAnalyticsPage />} />
                              <Route path="/pipeline" element={<PipelinePage />} />
                              <Route path="/events" element={<EventsPage />} />
                              <Route path="/cache" element={<CachePage />} />
                              {/* Domain-specific pages */}
                              <Route path="/lineage/:id" element={<DataLineagePage />} />
                              <Route path="/calibration" element={<CalibrationWorkflowPage />} />
                              <Route path="/ms-browser" element={<MSBrowserPage />} />
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
