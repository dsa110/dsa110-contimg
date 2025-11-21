/**
 * System Status Page
 *
 * Centralized dashboard showing health status of all services, APIs, and connections.
 * Provides a single place to monitor system health and diagnose connectivity issues.
 */

import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  Chip,
  Stack,
  Alert,
  Button,
  Divider,
  LinearProgress,
  IconButton,
  Collapse,
} from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import {
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  HelpOutline as UnknownIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from "@mui/icons-material";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import { apiClient } from "../api/client";
import { useAbsurdHealth } from "../api/absurdQueries";
import { env } from "../config/env";
import { logger } from "../utils/logger";

interface ServiceStatus {
  name: string;
  status: "healthy" | "unhealthy" | "degraded" | "unknown";
  responseTime?: number;
  error?: string;
  details?: string;
  lastCheck?: Date;
  endpoint?: string;
}

interface ConnectionTest {
  service: string;
  url: string;
  method: "GET" | "POST" | "WS";
  expectedStatus?: number;
}

const CONNECTION_TESTS: ConnectionTest[] = [
  // ========== CORE BACKEND APIS ==========
  { service: "Backend API Health", url: "/api/health", method: "GET", expectedStatus: 200 },
  { service: "Health Summary", url: "/api/health/summary", method: "GET", expectedStatus: 200 },
  { service: "Health Services", url: "/api/health/services", method: "GET", expectedStatus: 200 },

  // ========== PIPELINE APIS ==========
  { service: "Pipeline Status", url: "/api/status", method: "GET", expectedStatus: 200 },
  {
    service: "Pipeline Metrics Summary",
    url: "/api/pipeline/metrics/summary",
    method: "GET",
    expectedStatus: 200,
  },
  {
    service: "Pipeline Executions",
    url: "/api/pipeline/executions?limit=10",
    method: "GET",
    expectedStatus: 200,
  },
  {
    service: "Pipeline Active Executions",
    url: "/api/pipeline/executions/active",
    method: "GET",
    expectedStatus: 200,
  },
  {
    service: "Pipeline Dependency Graph",
    url: "/api/pipeline/dependency-graph",
    method: "GET",
    expectedStatus: 200,
  },
  {
    service: "Pipeline Stage Metrics",
    url: "/api/pipeline/stages/metrics?limit=10",
    method: "GET",
    expectedStatus: 200,
  },

  // ========== JOB MANAGEMENT APIS ==========
  { service: "Jobs List", url: "/api/jobs?limit=10", method: "GET", expectedStatus: 200 },
  { service: "Batch Jobs List", url: "/api/batch?limit=10", method: "GET", expectedStatus: 200 },

  // ========== DATA APIS ==========
  { service: "Measurement Sets", url: "/api/ms?limit=10", method: "GET", expectedStatus: 200 },
  { service: "Images", url: "/api/images?limit=10", method: "GET", expectedStatus: 200 },
  { service: "Data Instances", url: "/api/data?limit=10", method: "GET", expectedStatus: 200 },
  { service: "Mosaics", url: "/api/mosaics?limit=10", method: "GET", expectedStatus: 200 },
  { service: "Sources", url: "/api/sources?limit=10", method: "GET", expectedStatus: 200 },
  { service: "UVH5 Files", url: "/api/uvh5?limit=10", method: "GET", expectedStatus: 200 },

  // ========== METRICS APIS ==========
  { service: "System Metrics", url: "/api/metrics/system", method: "GET", expectedStatus: 200 },
  { service: "Database Metrics", url: "/api/metrics/database", method: "GET", expectedStatus: 200 },

  // ========== STREAMING APIS ==========
  { service: "Streaming Status", url: "/api/streaming/status", method: "GET", expectedStatus: 200 },
  { service: "Streaming Health", url: "/api/streaming/health", method: "GET", expectedStatus: 200 },
  {
    service: "Streaming Metrics",
    url: "/api/streaming/metrics",
    method: "GET",
    expectedStatus: 200,
  },
  { service: "Streaming Config", url: "/api/streaming/config", method: "GET", expectedStatus: 200 },

  // ========== POINTING APIS ==========
  {
    service: "Pointing Monitor Status",
    url: "/api/pointing-monitor/status",
    method: "GET",
    expectedStatus: 200,
  },
  {
    service: "Pointing History",
    url: "/api/pointing/history?limit=10",
    method: "GET",
    expectedStatus: 200,
  },
  {
    service: "Pointing Sky Map Data",
    url: "/api/pointing/sky-map-data",
    method: "GET",
    expectedStatus: 200,
  },
  {
    service: "Pointing History Records",
    url: "/api/pointing_history?limit=10",
    method: "GET",
    expectedStatus: 200,
  },

  // ========== OPERATIONS APIS ==========
  { service: "DLQ Stats", url: "/api/operations/dlq/stats", method: "GET", expectedStatus: 200 },
  {
    service: "DLQ Items",
    url: "/api/operations/dlq/items?limit=10",
    method: "GET",
    expectedStatus: 200,
  },
  {
    service: "Circuit Breakers",
    url: "/api/operations/circuit-breakers",
    method: "GET",
    expectedStatus: 200,
  },

  // ========== EVENT & CACHE APIS ==========
  { service: "Event Statistics", url: "/api/events/stats", method: "GET", expectedStatus: 200 },
  {
    service: "Event Stream",
    url: "/api/events/stream?limit=10",
    method: "GET",
    expectedStatus: 200,
  },
  { service: "Event Types", url: "/api/events/types", method: "GET", expectedStatus: 200 },
  { service: "Cache Statistics", url: "/api/cache/stats", method: "GET", expectedStatus: 200 },
  { service: "Cache Keys", url: "/api/cache/keys?limit=10", method: "GET", expectedStatus: 200 },
  {
    service: "Cache Performance",
    url: "/api/cache/performance",
    method: "GET",
    expectedStatus: 200,
  },

  // ========== CALIBRATION APIS ==========
  {
    service: "Calibration Status",
    url: "/api/calibration/status",
    method: "GET",
    expectedStatus: 200,
  },
  { service: "Cal Tables", url: "/api/caltables?limit=10", method: "GET", expectedStatus: 200 },

  // ========== QA APIS ==========
  {
    service: "Alerts History",
    url: "/api/alerts/history?limit=10",
    method: "GET",
    expectedStatus: 200,
  },

  // ========== VISUALIZATION APIS ==========
  { service: "Directory Listing", url: "/api/visualization/browse?path=/data", method: "GET" },
  { service: "FITS Info", url: "/api/visualization/fits/info?path=/data/test.fits", method: "GET" },
  {
    service: "Casa Table Info",
    url: "/api/visualization/casatable/info?path=/data/test.ms",
    method: "GET",
  },
  {
    service: "CARTA Status",
    url: "/api/visualization/carta/status",
    method: "GET",
    expectedStatus: 200,
  },

  // ========== CATALOG & REGIONS APIS ==========
  {
    service: "Catalog Overlay",
    url: "/api/catalog/overlay?ra=0&dec=0&radius=1",
    method: "GET",
    expectedStatus: 200,
  },
  { service: "Regions", url: "/api/regions?limit=10", method: "GET", expectedStatus: 200 },

  // ========== ABSURD TASK MANAGEMENT ==========
  { service: "ABSURD Health", url: "/api/absurd/health", method: "GET" },
  { service: "ABSURD Tasks", url: "/api/absurd/tasks?limit=10", method: "GET" },
  { service: "ABSURD Queue Stats", url: "/api/absurd/queues/dsa110-pipeline/stats", method: "GET" },

  // ========== WEBSOCKET ==========
  { service: "WebSocket Status", url: "/api/ws/status", method: "GET" },

  // ========== REAL-TIME DATA ==========
  {
    service: "ESE Candidates",
    url: "/api/ese/candidates?limit=10",
    method: "GET",
    expectedStatus: 200,
  },

  // ========== EXTERNAL SERVICES ==========
  { service: "CARTA Frontend", url: "http://localhost:9002", method: "GET" },
];

const StatusIcon = ({ status }: { status: ServiceStatus["status"] }) => {
  switch (status) {
    case "healthy":
      return <CheckIcon color="success" />;
    case "unhealthy":
      return <ErrorIcon color="error" />;
    case "degraded":
      return <WarningIcon color="warning" />;
    default:
      return <UnknownIcon color="disabled" />;
  }
};

const StatusChip = ({ status }: { status: ServiceStatus["status"] }) => {
  const colorMap = {
    healthy: "success",
    unhealthy: "error",
    degraded: "warning",
    unknown: "default",
  } as const;

  return (
    <Chip
      label={status.toUpperCase()}
      color={colorMap[status]}
      size="small"
      sx={{ fontWeight: 600, minWidth: 90 }}
    />
  );
};

interface ServiceCardProps {
  service: ServiceStatus;
  expanded: Set<string>;
  onToggle: (serviceName: string) => void;
}

const ServiceCard = ({ service, expanded, onToggle }: ServiceCardProps) => (
  <Card variant="outlined">
    <CardContent>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, flex: 1 }}>
          <StatusIcon status={service.status} />
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle1" fontWeight={600}>
              {service.name}
            </Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ fontFamily: "monospace", fontSize: "0.85em" }}
            >
              {service.endpoint}
            </Typography>
          </Box>
          <StatusChip status={service.status} />
          {service.responseTime && (
            <Chip label={`${service.responseTime}ms`} size="small" variant="outlined" />
          )}
          <IconButton size="small" onClick={() => onToggle(service.name)}>
            {expanded.has(service.name) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>
      </Box>

      <Collapse in={expanded.has(service.name)}>
        <Box sx={{ mt: 2, p: 2, bgcolor: "grey.50", borderRadius: 1 }}>
          <Typography variant="body2" component="div">
            <strong>Last Check:</strong> {service.lastCheck?.toLocaleString()}
          </Typography>
          {service.details && (
            <Typography variant="body2" component="div" sx={{ mt: 1 }}>
              <strong>Details:</strong> {service.details}
            </Typography>
          )}
          {service.error && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {service.error}
            </Alert>
          )}
        </Box>
      </Collapse>
    </CardContent>
  </Card>
);

export default function SystemStatusPage() {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [expandedServices, setExpandedServices] = useState<Set<string>>(new Set());

  const { data: absurdHealth } = useAbsurdHealth();

  const toggleExpanded = (serviceName: string) => {
    setExpandedServices((prev) => {
      const next = new Set(prev);
      if (next.has(serviceName)) {
        next.delete(serviceName);
      } else {
        next.add(serviceName);
      }
      return next;
    });
  };

  const testConnection = async (test: ConnectionTest): Promise<ServiceStatus> => {
    const startTime = Date.now();
    const status: ServiceStatus = {
      name: test.service,
      status: "unknown",
      lastCheck: new Date(),
      endpoint: test.url,
    };

    try {
      if (test.method === "GET") {
        // Handle absolute URLs differently
        if (test.url.startsWith("http://") || test.url.startsWith("https://")) {
          const response = await fetch(test.url, {
            method: "GET",
            mode: "no-cors", // Allow testing external services
          });

          // For no-cors, we can't read status but can detect if request succeeded
          status.responseTime = Date.now() - startTime;
          status.status = "healthy";
          status.details = `Response received in ${status.responseTime}ms`;
        } else {
          // Use fetch with absolute URL to bypass circuit breaker for status checks
          const fullUrl = test.url.startsWith("/")
            ? `${window.location.origin}${test.url}`
            : test.url;

          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 10000); // Increased to 10s

          try {
            const response = await fetch(fullUrl, {
              method: "GET",
              headers: { Accept: "application/json" },
              signal: controller.signal,
            });
            clearTimeout(timeoutId);

            status.responseTime = Date.now() - startTime;

            // Handle non-OK responses (4xx, 5xx)
            if (!response.ok) {
              let errorMessage = `HTTP ${response.status}`;

              // Try to parse error details from response body
              try {
                const errorData = await response.json();
                errorMessage = errorData?.message || errorData?.error || errorMessage;
              } catch {
                // If JSON parsing fails, just use status text
                errorMessage = response.statusText || errorMessage;
              }

              if (response.status === 500) {
                status.status = "degraded";
                status.error = errorMessage;
                status.details = `HTTP 500: ${errorMessage}`;
              } else if (response.status === 404) {
                status.status = "degraded";
                status.error = "Endpoint not found";
                status.details = `HTTP 404: Resource not available`;
              } else if (response.status >= 400 && response.status < 500) {
                status.status = "degraded";
                status.error = errorMessage;
                status.details = `HTTP ${response.status}: ${errorMessage}`;
              } else {
                status.status = "unhealthy";
                status.error = errorMessage;
                status.details = `HTTP ${response.status} in ${status.responseTime}ms`;
              }
            } else if (test.expectedStatus && response.status !== test.expectedStatus) {
              status.status = "degraded";
              status.details = `HTTP ${response.status} (expected ${test.expectedStatus})`;
            } else {
              status.status = "healthy";
              status.details = `HTTP ${response.status} in ${status.responseTime}ms`;
            }
          } catch (fetchError) {
            clearTimeout(timeoutId);
            throw fetchError;
          }
        }
      }
    } catch (error) {
      status.responseTime = Date.now() - startTime;

      // Check if it's a fetch Response error (HTTP error with response body)
      if (error && typeof error === "object" && "status" in error) {
        const httpStatus = (error as any).status;

        if (httpStatus === 500) {
          status.status = "degraded";
          status.error = "Internal server error";
          status.details = `HTTP 500 in ${status.responseTime}ms`;
        } else if (httpStatus === 404) {
          status.status = "degraded";
          status.error = "Endpoint not found";
          status.details = `HTTP 404 in ${status.responseTime}ms`;
        } else if (httpStatus >= 400 && httpStatus < 500) {
          status.status = "degraded";
          status.error = "Client error";
          status.details = `HTTP ${httpStatus} in ${status.responseTime}ms`;
        } else {
          status.status = "unhealthy";
          status.error = `HTTP ${httpStatus}`;
          status.details = `Failed after ${status.responseTime}ms`;
        }
      }
      // Check if it's an axios error with a response
      else if (error && typeof error === "object" && "response" in error) {
        const axiosError = error as any;
        const httpStatus = axiosError.response?.status;
        const errorData = axiosError.response?.data;

        // 500 errors mean backend is reachable but has internal issues (degraded, not down)
        if (httpStatus === 500) {
          status.status = "degraded";
          status.error = errorData?.message || errorData?.error || "Internal server error";
          status.details = `HTTP 500: ${status.error}`;
        } else if (httpStatus === 404) {
          status.status = "degraded";
          status.error = "Endpoint not found";
          status.details = `HTTP 404: Resource not available`;
        } else if (httpStatus >= 400 && httpStatus < 500) {
          status.status = "degraded";
          status.error = errorData?.message || "Client error";
          status.details = `HTTP ${httpStatus}: ${status.error}`;
        } else {
          // Other HTTP errors (network issues, timeouts, etc.)
          status.status = "unhealthy";
          status.error = error instanceof Error ? error.message : String(error);
          status.details = `Failed after ${status.responseTime}ms`;
        }
      }
      // Check for AbortError (timeout)
      else if (error instanceof Error && error.name === "AbortError") {
        status.status = "unhealthy";
        status.error = "Request timeout (10s)";
        status.details = `Timeout after ${status.responseTime}ms`;
      }
      // Other errors (network failures, CORS issues, etc.)
      else {
        status.status = "unhealthy";
        status.error = error instanceof Error ? error.message : String(error);
        status.details = `Failed after ${status.responseTime}ms`;
      }

      logger.warn(`Service check failed: ${test.service}`, { error: status.error });
    }

    return status;
  };

  const checkAllServices = useCallback(async () => {
    setLoading(true);

    try {
      const results = await Promise.all(CONNECTION_TESTS.map((test) => testConnection(test)));

      setServices(results);
      setLastRefresh(new Date());
    } catch (error) {
      logger.error("Failed to check services", { error });
    } finally {
      setLoading(false);
    }
  }, []); // Empty deps - testConnection is defined inline

  useEffect(() => {
    checkAllServices();
  }, [checkAllServices]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      checkAllServices();
    }, 30000);

    return () => clearInterval(interval);
  }, [autoRefresh, checkAllServices]);

  const handleRefresh = () => {
    checkAllServices();
  };

  const handleToggleAutoRefresh = () => {
    setAutoRefresh((prev) => !prev);
  };

  // Calculate overall system health
  const getOverallHealth = (): ServiceStatus["status"] => {
    if (services.length === 0) return "unknown";

    const unhealthyCount = services.filter((s) => s.status === "unhealthy").length;
    const degradedCount = services.filter((s) => s.status === "degraded").length;

    if (unhealthyCount > 0) return "unhealthy";
    if (degradedCount > 0) return "degraded";
    if (services.every((s) => s.status === "healthy")) return "healthy";

    return "unknown";
  };

  const overallHealth = getOverallHealth();

  // Group services by category
  const coreServices = services.filter(
    (s) =>
      s.name.includes("Backend API Health") ||
      s.name.includes("Health Summary") ||
      s.name.includes("Health Services")
  );
  const pipelineServices = services.filter(
    (s) =>
      (s.name.includes("Pipeline") ||
        s.name.includes("Jobs") ||
        s.name.includes("Batch") ||
        s.name.includes("Stage")) &&
      !s.name.includes("ABSURD")
  );
  const dataServices = services.filter(
    (s) =>
      s.name.includes("Measurement Sets") ||
      s.name.includes("Images") ||
      s.name.includes("Data Instances") ||
      s.name.includes("Mosaics") ||
      s.name.includes("Sources") ||
      s.name.includes("UVH5")
  );
  const streamingServices = services.filter(
    (s) => s.name.includes("Streaming") || s.name.includes("Pointing")
  );
  const operationsServices = services.filter(
    (s) =>
      s.name.includes("DLQ") ||
      s.name.includes("Circuit") ||
      s.name.includes("Event") ||
      s.name.includes("Cache")
  );
  const calibrationServices = services.filter(
    (s) => s.name.includes("Calibration") || s.name.includes("Cal Tables")
  );
  const metricsServices = services.filter(
    (s) => s.name.includes("System Metrics") || s.name.includes("Database Metrics")
  );
  const qaServices = services.filter(
    (s) =>
      s.name.includes("Alerts") ||
      s.name.includes("Directory") ||
      s.name.includes("FITS") ||
      s.name.includes("Casa Table") ||
      s.name.includes("CARTA Status")
  );
  const catalogServices = services.filter(
    (s) => s.name.includes("Catalog") || s.name.includes("Regions")
  );
  const absurdServices = services.filter(
    (s) => s.name.includes("ABSURD") && !s.name.includes("Workflow Manager")
  );
  const realTimeServices = services.filter(
    (s) => s.name.includes("WebSocket") || s.name.includes("ESE Candidates")
  );
  const externalServices = services.filter((s) => s.name.includes("CARTA Frontend"));

  const healthyCount = services.filter((s) => s.status === "healthy").length;
  const unhealthyCount = services.filter((s) => s.status === "unhealthy").length;
  const degradedCount = services.filter((s) => s.status === "degraded").length;

  return (
    <>
      <PageBreadcrumbs />
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ mb: 3, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Box>
            <Typography variant="h2" component="h1" gutterBottom>
              System Status
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Monitor health and connectivity of all services and APIs
            </Typography>
          </Box>
          <Stack direction="row" spacing={2}>
            <Button
              variant={autoRefresh ? "contained" : "outlined"}
              onClick={handleToggleAutoRefresh}
              size="small"
            >
              {autoRefresh ? "Auto-Refresh ON" : "Auto-Refresh OFF"}
            </Button>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
              disabled={loading}
            >
              Refresh Now
            </Button>
          </Stack>
        </Box>

        {loading && <LinearProgress sx={{ mb: 2 }} />}

        {/* Overall Status Card */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={3}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <Box sx={{ fontSize: 48 }}>
                  <StatusIcon status={overallHealth} />
                </Box>
                <Box>
                  <Typography variant="h4" component="div">
                    {overallHealth === "healthy"
                      ? "All Systems Operational"
                      : overallHealth === "degraded"
                        ? "Degraded Performance"
                        : overallHealth === "unhealthy"
                          ? "Service Issues Detected"
                          : "Status Unknown"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Last updated: {lastRefresh.toLocaleTimeString()}
                  </Typography>
                </Box>
              </Box>
            </Grid>
            <Grid item xs={12} md={9}>
              <Grid container spacing={2}>
                <Grid item xs={4}>
                  <Card variant="outlined" sx={{ bgcolor: "success.50" }}>
                    <CardContent>
                      <Typography variant="h3" color="success.main">
                        {healthyCount}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Healthy Services
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={4}>
                  <Card variant="outlined" sx={{ bgcolor: "warning.50" }}>
                    <CardContent>
                      <Typography variant="h3" color="warning.main">
                        {degradedCount}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Degraded Services
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={4}>
                  <Card variant="outlined" sx={{ bgcolor: "error.50" }}>
                    <CardContent>
                      <Typography variant="h3" color="error.main">
                        {unhealthyCount}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Unhealthy Services
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        </Paper>

        {/* Core Health Services */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            Core Health Services
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            System health and monitoring endpoints
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Stack spacing={1}>
            {coreServices.map((service) => (
              <ServiceCard
                key={service.name}
                service={service}
                expanded={expandedServices}
                onToggle={toggleExpanded}
              />
            ))}
          </Stack>
        </Paper>

        {/* Pipeline Services */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            Pipeline Services
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Pipeline execution, job management, and workflow orchestration
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Stack spacing={1}>
            {pipelineServices.map((service) => (
              <ServiceCard
                key={service.name}
                service={service}
                expanded={expandedServices}
                onToggle={toggleExpanded}
              />
            ))}
          </Stack>
        </Paper>

        {/* Data Services */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            Data Services
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Measurement sets, images, mosaics, and source catalogs
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Stack spacing={1}>
            {dataServices.map((service) => (
              <ServiceCard
                key={service.name}
                service={service}
                expanded={expandedServices}
                onToggle={toggleExpanded}
              />
            ))}
          </Stack>
        </Paper>

        {/* Streaming & Pointing Services */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            Streaming & Pointing Services
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Real-time data streaming and telescope pointing monitoring
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Stack spacing={1}>
            {streamingServices.map((service) => (
              <ServiceCard
                key={service.name}
                service={service}
                expanded={expandedServices}
                onToggle={toggleExpanded}
              />
            ))}
          </Stack>
        </Paper>

        {/* Metrics Services */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            Metrics & Monitoring
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            System and database performance metrics
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Stack spacing={1}>
            {metricsServices.map((service) => (
              <ServiceCard
                key={service.name}
                service={service}
                expanded={expandedServices}
                onToggle={toggleExpanded}
              />
            ))}
          </Stack>
        </Paper>

        {/* Operations Services */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            Operations Services
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Dead letter queue, circuit breakers, events, and caching
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Stack spacing={1}>
            {operationsServices.map((service) => (
              <ServiceCard
                key={service.name}
                service={service}
                expanded={expandedServices}
                onToggle={toggleExpanded}
              />
            ))}
          </Stack>
        </Paper>

        {/* Calibration Services */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            Calibration Services
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Calibration status and calibration tables
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Stack spacing={1}>
            {calibrationServices.map((service) => (
              <ServiceCard
                key={service.name}
                service={service}
                expanded={expandedServices}
                onToggle={toggleExpanded}
              />
            ))}
          </Stack>
        </Paper>

        {/* QA Services */}
        {qaServices.length > 0 && (
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h5" gutterBottom>
              QA & Visualization Services
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Quality assurance, file system access, and data visualization
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Stack spacing={1}>
              {qaServices.map((service) => (
                <ServiceCard
                  key={service.name}
                  service={service}
                  expanded={expandedServices}
                  onToggle={toggleExpanded}
                />
              ))}
            </Stack>
          </Paper>
        )}

        {/* Catalog & Region Services */}
        {catalogServices.length > 0 && (
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h5" gutterBottom>
              Catalog & Region Services
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Sky catalog queries and region management
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Stack spacing={1}>
              {catalogServices.map((service) => (
                <ServiceCard
                  key={service.name}
                  service={service}
                  expanded={expandedServices}
                  onToggle={toggleExpanded}
                />
              ))}
            </Stack>
          </Paper>
        )}

        {/* ABSURD Task Services */}
        {absurdServices.length > 0 && (
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h5" gutterBottom>
              ABSURD Task Management
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Distributed task queue and workflow orchestration
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Stack spacing={1}>
              {absurdServices.map((service) => (
                <ServiceCard
                  key={service.name}
                  service={service}
                  expanded={expandedServices}
                  onToggle={toggleExpanded}
                />
              ))}
            </Stack>
          </Paper>
        )}

        {/* Real-time Services */}
        {realTimeServices.length > 0 && (
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h5" gutterBottom>
              Real-time Communication
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              WebSocket connections and live data streams (ESE candidates)
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Stack spacing={1}>
              {realTimeServices.map((service) => (
                <ServiceCard
                  key={service.name}
                  service={service}
                  expanded={expandedServices}
                  onToggle={toggleExpanded}
                />
              ))}
            </Stack>
          </Paper>
        )}

        {/* External Services */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            External Services
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Third-party integrations and visualization tools
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Stack spacing={1}>
            {externalServices.map((service) => (
              <ServiceCard
                key={service.name}
                service={service}
                expanded={expandedServices}
                onToggle={toggleExpanded}
              />
            ))}
          </Stack>
        </Paper>

        {/* Configuration Info */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>
            Configuration
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                API Configuration
              </Typography>
              <Box
                sx={{
                  fontFamily: "monospace",
                  fontSize: "0.85em",
                  p: 2,
                  bgcolor: "grey.50",
                  borderRadius: 1,
                }}
              >
                <div>API Base URL: {env.VITE_API_URL || "/api"}</div>
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                CARTA Configuration
              </Typography>
              <Box
                sx={{
                  fontFamily: "monospace",
                  fontSize: "0.85em",
                  p: 2,
                  bgcolor: "grey.50",
                  borderRadius: 1,
                }}
              >
                <div>Backend: {env.VITE_CARTA_BACKEND_URL || "http://localhost:9002"}</div>
                <div>Frontend: {env.VITE_CARTA_FRONTEND_URL || "http://localhost:9003"}</div>
              </Box>
            </Grid>
          </Grid>
        </Paper>

        {/* Help Alert */}
        <Alert severity="info" sx={{ mt: 3 }}>
          <Typography variant="body2">
            <strong>Troubleshooting Tips:</strong>
          </Typography>
          <ul style={{ marginTop: 8, marginBottom: 0, paddingLeft: 20 }}>
            <li>
              If Backend API services are down, check if the FastAPI server is running on port 8000
            </li>
            <li>
              If CARTA is unavailable, verify the docker container is running:{" "}
              <code>docker ps | grep carta</code>
            </li>
            <li>
              If ABSURD is degraded, check the workflow manager logs and database connectivity
            </li>
            <li>Use the Refresh button to manually re-test all connections</li>
          </ul>
        </Alert>
      </Box>
    </>
  );
}
