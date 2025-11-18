import React, { useState } from "react";
import {
  Container,
  Typography,
  Box,
  Alert,
  Stack,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Skeleton,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { usePipelineStatus, useSystemMetrics, useHealthSummary } from "../api/queries";
import { useNavigate } from "react-router-dom";
import ESECandidatesPanel from "../components/ESECandidatesPanel";
import PointingVisualization from "../components/PointingVisualization";
import { env } from "../config/env";
import { StatusIndicator } from "../components/StatusIndicator";
import { MetricWithSparkline } from "../components/Sparkline";
import { SkeletonLoader } from "../components/SkeletonLoader";
import CollapsibleSection from "../components/CollapsibleSection";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import QueueDetailsPanel from "../components/QueueDetailsPanel";
import { useMetricHistory } from "../hooks/useMetricHistory";
import { QueueOverviewCard } from "../components/QueueOverviewCard";
import { DeadLetterQueueStats } from "../components/DeadLetterQueue";
import { CircuitBreakerStatus } from "../components/CircuitBreaker";
import { PointingSummaryCard } from "../components/PointingSummaryCard";

type QueueStatusType = "total" | "pending" | "in_progress" | "completed" | "failed" | "collecting";
type HealthCheckRecord = Record<string, { healthy: boolean; error?: string }>;

export default function DashboardPage() {
  const { data: status, isLoading: statusLoading, error: statusError } = usePipelineStatus();
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useSystemMetrics();
  const { data: healthSummary, isLoading: healthSummaryLoading } = useHealthSummary();
  const navigate = useNavigate();
  const [selectedQueueStatus, setSelectedQueueStatus] = useState<QueueStatusType>("in_progress");

  const healthChecks = (healthSummary?.checks as HealthCheckRecord | undefined) ?? undefined;
  const healthSummaryTimestampValue = (healthSummary as { timestamp?: number } | undefined)
    ?.timestamp;
  const healthSummaryTimestamp =
    typeof healthSummaryTimestampValue === "number"
      ? new Date(healthSummaryTimestampValue * 1000)
      : undefined;

  // Track metric history for sparklines
  const cpuHistory = useMetricHistory(metrics?.cpu_percent ?? undefined);
  const memHistory = useMetricHistory(metrics?.mem_percent ?? undefined);

  // Use new disks array format (supports multiple mount points)
  // Track history for all available disks
  // Note: / (SSD) is the root filesystem which includes /stage directory
  const ssdDisk = metrics?.disks?.find((d) => d.mount_point.startsWith("/ (SSD)"));
  const hddDisk = metrics?.disks?.find((d) => d.mount_point.startsWith("/data/"));
  const ssdDiskHistory = useMetricHistory(ssdDisk?.percent ?? undefined);
  const hddDiskHistory = useMetricHistory(hddDisk?.percent ?? undefined);

  const loadHistory = useMetricHistory(metrics?.load_1 ?? undefined);

  if (statusLoading || metricsLoading) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <SkeletonLoader variant="cards" rows={4} />
      </Container>
    );
  }

  if (statusError || metricsError) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert severity="error">
          Failed to connect to DSA-110 pipeline API.{" "}
          {env.VITE_API_URL ? `Using API URL: ${env.VITE_API_URL}` : "Using Vite proxy (/api)."} Is
          the backend running?
        </Alert>
      </Container>
    );
  }

  return (
    <>
      <PageBreadcrumbs />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="h3" component="h1" gutterBottom sx={{ fontWeight: 700, mb: 1 }}>
            DSA-110 Continuum Imaging Pipeline
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Real-time monitoring and control dashboard
          </Typography>
        </Box>

        <Stack spacing={3}>
          {/* Row 1: Pipeline Status + Queue Details + System Health */}
          <Stack direction={{ xs: "column", md: "row" }} spacing={3}>
            <CollapsibleSection title="Pipeline Status" defaultExpanded={true} variant="outlined">
              <Box sx={{ mt: 2 }}>
                <QueueOverviewCard
                  queue={status?.queue}
                  selectedStatus={selectedQueueStatus}
                  onSelectStatus={setSelectedQueueStatus}
                  helperText="Select a queue state to filter the details panel."
                  variant="inline"
                />

                <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
                  Calibration Sets
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Active: <strong>{status?.calibration_sets?.length || 0}</strong>
                </Typography>
              </Box>
            </CollapsibleSection>

            {/* Queue Details Panel */}
            <CollapsibleSection title="Queue Details" defaultExpanded={true} variant="outlined">
              <QueueDetailsPanel
                selectedStatus={selectedQueueStatus}
                queueGroups={status?.recent_groups || []}
                isLoading={statusLoading}
              />
            </CollapsibleSection>

            {/* System Health */}
            <CollapsibleSection title="System Health" defaultExpanded={true} variant="outlined">
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Resource Usage
                </Typography>
                <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 2 }}>
                  {metrics?.cpu_percent != null && typeof metrics.cpu_percent === "number" && (
                    <StatusIndicator
                      value={metrics.cpu_percent}
                      thresholds={{ good: 70, warning: 50 }}
                      label="CPU"
                      size="medium"
                      showTrend={cpuHistory.length > 1}
                      previousValue={
                        cpuHistory.length > 1 ? cpuHistory[cpuHistory.length - 2] : undefined
                      }
                    />
                  )}
                  {metrics?.mem_percent != null && typeof metrics.mem_percent === "number" && (
                    <StatusIndicator
                      value={metrics.mem_percent}
                      thresholds={{ good: 80, warning: 60 }}
                      label="Memory"
                      size="medium"
                      showTrend={memHistory.length > 1}
                      previousValue={
                        memHistory.length > 1 ? memHistory[memHistory.length - 2] : undefined
                      }
                    />
                  )}
                  {ssdDisk && typeof ssdDisk.percent === "number" && (
                    <StatusIndicator
                      value={ssdDisk.percent}
                      thresholds={{ good: 75, warning: 90 }}
                      label="SSD (root)"
                      size="medium"
                      showTrend={ssdDiskHistory.length > 1}
                      previousValue={
                        ssdDiskHistory.length > 1
                          ? ssdDiskHistory[ssdDiskHistory.length - 2]
                          : undefined
                      }
                    />
                  )}
                  {hddDisk && typeof hddDisk.percent === "number" && (
                    <StatusIndicator
                      value={hddDisk.percent}
                      thresholds={{ good: 75, warning: 90 }}
                      label="HDD (/data/)"
                      size="medium"
                      showTrend={hddDiskHistory.length > 1}
                      previousValue={
                        hddDiskHistory.length > 1
                          ? hddDiskHistory[hddDiskHistory.length - 2]
                          : undefined
                      }
                    />
                  )}
                  {metrics?.load_1 != null && typeof metrics.load_1 === "number" && (
                    <MetricWithSparkline
                      label="Load (1m)"
                      value={metrics.load_1.toFixed(2)}
                      color="info"
                      trend={loadHistory.length > 1 ? loadHistory : undefined}
                    />
                  )}
                </Box>

                <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
                  Last Updated
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  {metrics?.ts ? new Date(metrics.ts).toLocaleString() : "N/A"}
                </Typography>
              </Box>
            </CollapsibleSection>
          </Stack>

          {/* Diagnostics & Alerts */}
          <CollapsibleSection
            title="Diagnostics & Alerts"
            defaultExpanded={true}
            variant="outlined"
          >
            <Stack spacing={3} sx={{ mt: 2 }}>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" },
                  gap: 3,
                }}
              >
                <QueueOverviewCard
                  queue={status?.queue}
                  title="Queue Snapshot"
                  helperText="Monitor pipeline throughput at a glance."
                />
                <PointingSummaryCard />
              </Box>

              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" },
                  gap: 3,
                }}
              >
                <DeadLetterQueueStats />
                <Card>
                  <CardHeader
                    title="Health Checks"
                    subheader={
                      healthSummaryTimestamp
                        ? `Updated ${healthSummaryTimestamp.toLocaleString()}`
                        : undefined
                    }
                    action={
                      <Button size="small" onClick={() => navigate("/health")}>
                        Open Health Page
                      </Button>
                    }
                  />
                  <CardContent>
                    {healthSummaryLoading && <Skeleton variant="rectangular" height={96} />}
                    {!healthSummaryLoading &&
                      healthChecks &&
                      Object.keys(healthChecks).length > 0 && (
                        <Stack spacing={1.5}>
                          {Object.entries(healthChecks).map(([name, check]) => (
                            <Stack
                              key={name}
                              direction="row"
                              spacing={2}
                              alignItems="center"
                              flexWrap="wrap"
                            >
                              <Chip
                                label={check.healthy ? "Healthy" : "Investigate"}
                                color={check.healthy ? "success" : "error"}
                                size="small"
                              />
                              <Typography variant="body2" sx={{ textTransform: "capitalize" }}>
                                {name.replace(/_/g, " ")}
                              </Typography>
                              {!check.healthy && check.error && (
                                <Typography variant="body2" color="text.secondary">
                                  {check.error}
                                </Typography>
                              )}
                            </Stack>
                          ))}
                        </Stack>
                      )}
                    {!healthSummaryLoading &&
                      (!healthChecks || Object.keys(healthChecks).length === 0) && (
                        <Typography variant="body2" color="text.secondary">
                          Health summary data is not available right now.
                        </Typography>
                      )}
                  </CardContent>
                </Card>
              </Box>

              <Box>
                <CircuitBreakerStatus />
              </Box>

              <ESECandidatesPanel />

              <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
                <Button variant="outlined" onClick={() => navigate("/health")}>
                  View detailed diagnostics
                </Button>
              </Box>
            </Stack>
          </CollapsibleSection>

          {/* Recent Observations */}
          <CollapsibleSection title="Recent Observations" defaultExpanded={true} variant="outlined">
            <Box sx={{ mt: 2 }}>
              {status?.recent_groups &&
              Array.isArray(status.recent_groups) &&
              status.recent_groups.length > 0 ? (
                <Box sx={{ overflowX: "auto" }}>
                  <Box
                    component="table"
                    sx={{
                      width: "100%",
                      borderCollapse: "collapse",
                      "& thead tr": {
                        borderBottom: "1px solid",
                        borderColor: "divider",
                      },
                      "& th": {
                        textAlign: "left",
                        padding: "8px",
                        fontWeight: 600,
                        color: "text.secondary",
                      },
                      "& tbody tr": {
                        borderBottom: "1px solid",
                        borderColor: "divider",
                        transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
                        "&:hover": {
                          backgroundColor: "action.hover",
                          transform: "translateX(2px)",
                          boxShadow: (theme) =>
                            `0 2px 4px ${alpha(theme.palette.common.black, 0.1)}`,
                        },
                        "&:nth-of-type(even)": {
                          backgroundColor: alpha("#fff", 0.02),
                        },
                      },
                      "& td": {
                        padding: "8px",
                      },
                    }}
                  >
                    <thead>
                      <tr>
                        <th>Group ID</th>
                        <th>State</th>
                        <th style={{ textAlign: "right" }}>Subbands</th>
                        <th>Calibrator</th>
                      </tr>
                    </thead>
                    <tbody>
                      {status?.recent_groups?.slice(0, 10).map((group) => (
                        <tr key={group.group_id}>
                          <td>{group.group_id}</td>
                          <td>{group.state}</td>
                          <td style={{ textAlign: "right" }}>
                            {group.subbands_present}/{group.expected_subbands}
                          </td>
                          <td>{group.has_calibrator ? "✓" : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </Box>
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No recent observations
                </Typography>
              )}
            </Box>
          </CollapsibleSection>

          {/* Pointing Visualization */}
          <CollapsibleSection
            title="Pointing Visualization"
            defaultExpanded={true}
            variant="outlined"
          >
            <PointingVisualization height={500} showHistory={true} />
          </CollapsibleSection>

          {/* Status Summary */}
          <Alert severity="success">
            DSA-110 Frontend v0.2.0 - Enhanced dashboard with ESE monitoring, mosaic gallery, source
            tracking, and interactive visualizations now available!
          </Alert>
        </Stack>
      </Container>
    </>
  );
}
