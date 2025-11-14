import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { ThemeProvider, CssBaseline, Box } from "@mui/material";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { darkTheme } from "./theme/darkTheme";
import { NotificationProvider } from "./contexts/NotificationContext";
import { JS9Provider } from "./contexts/JS9Context";
import { WorkflowProvider } from "./contexts/WorkflowContext";
import Navigation from "./components/Navigation";
import WorkflowBreadcrumbs from "./components/WorkflowBreadcrumbs";
import ErrorBoundary from "./components/ErrorBoundary";
import DashboardPage from "./pages/DashboardPage";
import ControlPage from "./pages/ControlPage";
import MosaicGalleryPage from "./pages/MosaicGalleryPage";
import MosaicViewPage from "./pages/MosaicViewPage";
import SourceMonitoringPage from "./pages/SourceMonitoringPage";
import SourceDetailPage from "./pages/SourceDetailPage";
import ImageDetailPage from "./pages/ImageDetailPage";
import SkyViewPage from "./pages/SkyViewPage";
import StreamingPage from "./pages/StreamingPage";
import DataBrowserPage from "./pages/DataBrowserPage";
import DataDetailPage from "./pages/DataDetailPage";
import QAVisualizationPage from "./pages/QAVisualizationPage";
import QACartaPage from "./pages/QACartaPage";
import ObservingPage from "./pages/ObservingPage";
import HealthPage from "./pages/HealthPage";
import { OperationsPage } from "./pages/OperationsPage";
import PipelinePage from "./pages/PipelinePage";
import EventsPage from "./pages/EventsPage";
import CachePage from "./pages/CachePage";
// Consolidated pages
import PipelineOperationsPage from "./pages/PipelineOperationsPage";
import DataExplorerPage from "./pages/DataExplorerPage";
import PipelineControlPage from "./pages/PipelineControlPage";
import SystemDiagnosticsPage from "./pages/SystemDiagnosticsPage";
import { isRetryableError } from "./utils/errorUtils";

// Create React Query client factory function
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
        staleTime: 30000, // 30 seconds default stale time
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
  const basename = import.meta.env.PROD ? "/ui" : undefined;

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
                  <Box
                    sx={{
                      display: "flex",
                      flexDirection: "column",
                      minHeight: "100vh",
                    }}
                  >
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
                          <Routes>
                            <Route path="/" element={<Navigate to="/dashboard" replace />} />
                            <Route path="/dashboard" element={<DashboardPage />} />

                            {/* Consolidated pages - primary routes */}
                            <Route
                              path="/pipeline-operations"
                              element={<PipelineOperationsPage />}
                            />
                            <Route path="/data-explorer" element={<DataExplorerPage />} />
                            <Route path="/pipeline-control" element={<PipelineControlPage />} />
                            <Route path="/system-diagnostics" element={<SystemDiagnosticsPage />} />

                            {/* Legacy routes - kept for backward compatibility */}
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
                            <Route path="/observing" element={<ObservingPage />} />
                            <Route path="/health" element={<HealthPage />} />
                            <Route path="/operations" element={<OperationsPage />} />
                            <Route path="/pipeline" element={<PipelinePage />} />
                            <Route path="/events" element={<EventsPage />} />
                            <Route path="/cache" element={<CachePage />} />
                          </Routes>
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
