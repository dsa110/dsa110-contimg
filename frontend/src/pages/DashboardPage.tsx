import { Container, Typography, Box, Alert, Stack } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { usePipelineStatus, useSystemMetrics } from "../api/queries";
import ESECandidatesPanel from "../components/ESECandidatesPanel";
import PointingVisualization from "../components/PointingVisualization";
import { StatusIndicator } from "../components/StatusIndicator";
import { MetricCard } from "../components/MetricCard";
import { MetricWithSparkline } from "../components/Sparkline";
import { SkeletonLoader } from "../components/SkeletonLoader";
import CollapsibleSection from "../components/CollapsibleSection";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import { useMetricHistory } from "../hooks/useMetricHistory";

export default function DashboardPage() {
  const { data: status, isLoading: statusLoading, error: statusError } = usePipelineStatus();
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useSystemMetrics();

  // Track metric history for sparklines
  const cpuHistory = useMetricHistory(metrics?.cpu_percent);
  const memHistory = useMetricHistory(metrics?.mem_percent);
  const diskHistory = useMetricHistory(
    metrics?.disk_total && metrics?.disk_used
      ? (metrics.disk_used / metrics.disk_total) * 100
      : undefined
  );
  const loadHistory = useMetricHistory(metrics?.load_1);

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
          {import.meta.env.VITE_API_URL
            ? `Using API URL: ${import.meta.env.VITE_API_URL}`
            : "Using Vite proxy (/api)."}{" "}
          Is the backend running?
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
          {/* Row 1: Pipeline Status + System Health */}
          <Stack direction={{ xs: "column", md: "row" }} spacing={3}>
            <CollapsibleSection title="Pipeline Status" defaultExpanded={true} variant="outlined">
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Queue Statistics
                </Typography>
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)" },
                    gap: 2,
                  }}
                >
                  <MetricCard
                    label="Total"
                    value={status?.queue.total || 0}
                    color="primary"
                    size="small"
                  />
                  <MetricCard
                    label="Pending"
                    value={status?.queue.pending || 0}
                    color="info"
                    size="small"
                  />
                  <MetricCard
                    label="In Progress"
                    value={status?.queue.in_progress || 0}
                    color="warning"
                    size="small"
                  />
                  <MetricCard
                    label="Completed"
                    value={status?.queue.completed || 0}
                    color="success"
                    size="small"
                  />
                  <MetricCard
                    label="Failed"
                    value={status?.queue.failed || 0}
                    color="error"
                    size="small"
                  />
                  <MetricCard
                    label="Collecting"
                    value={status?.queue.collecting || 0}
                    color="info"
                    size="small"
                  />
                </Box>

                <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
                  Calibration Sets
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Active: <strong>{status?.calibration_sets.length || 0}</strong>
                </Typography>
              </Box>
            </CollapsibleSection>

            {/* System Health */}
            <CollapsibleSection title="System Health" defaultExpanded={true} variant="outlined">
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Resource Usage
                </Typography>
                <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 2 }}>
                  {metrics?.cpu_percent !== undefined && (
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
                  {metrics?.mem_percent !== undefined && (
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
                  {metrics?.disk_total && metrics?.disk_used && (
                    <StatusIndicator
                      value={(metrics.disk_used / metrics.disk_total) * 100}
                      thresholds={{ good: 75, warning: 90 }}
                      label="Disk"
                      size="medium"
                      showTrend={diskHistory.length > 1}
                      previousValue={
                        diskHistory.length > 1 ? diskHistory[diskHistory.length - 2] : undefined
                      }
                    />
                  )}
                  {metrics?.load_1 !== undefined && (
                    <MetricWithSparkline
                      label="Load (1m)"
                      value={metrics.load_1.toFixed(2)}
                      color="info"
                      size="small"
                      sparklineData={loadHistory.length > 1 ? loadHistory : undefined}
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

          {/* Recent Observations */}
          <CollapsibleSection title="Recent Observations" defaultExpanded={true} variant="outlined">
            <Box sx={{ mt: 2 }}>
              {status?.recent_groups && status.recent_groups.length > 0 ? (
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
                      {status.recent_groups.slice(0, 10).map((group) => (
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
            <PointingVisualization height={500} showHistory={true} historyDays={7} />
          </CollapsibleSection>

          {/* ESE Candidates Panel */}
          <ESECandidatesPanel />

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
