/**
 * Health Page
 * Deep diagnostics for pipeline and data quality monitoring
 */
import { useState, useMemo } from "react";
import {
  Container,
  Typography,
  Paper,
  Box,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Stack,
  Chip,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import {
  Memory as MemoryIcon,
  Speed as SpeedIcon,
  Storage as StorageIcon,
  Assessment as AssessmentIcon,
} from "@mui/icons-material";
import {
  usePipelineStatus,
  useSystemMetrics,
  useESECandidates,
  useHealthSummary,
} from "../api/queries";
import Plot from "react-plotly.js";
import type { Data, Layout } from "plotly.js";
import { useNavigate } from "react-router-dom";
import { DeadLetterQueueStats } from "../components/DeadLetterQueue";
import { CircuitBreakerStatus } from "../components/CircuitBreaker";
import type { HealthSummary } from "../api/types";
import PageBreadcrumbs from "../components/PageBreadcrumbs";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

function MetricCard({
  label,
  value,
  unit = "",
  threshold = { warning: 75, critical: 90 },
  icon,
}: {
  label: string;
  value: number | undefined;
  unit?: string;
  threshold?: { warning: number; critical: number };
  icon?: React.ReactNode;
}) {
  const percentage = value || 0;
  const severity =
    percentage >= threshold.critical
      ? "error"
      : percentage >= threshold.warning
        ? "warning"
        : "success";

  return (
    <Card>
      <CardContent>
        <Stack direction="row" spacing={2} alignItems="center">
          {icon && <Box sx={{ color: "text.secondary" }}>{icon}</Box>}
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="body2" color="text.secondary">
              {label}
            </Typography>
            <Typography variant="h5">
              {value !== undefined ? `${value.toFixed(1)}${unit}` : "N/A"}
            </Typography>
            <LinearProgress
              variant="determinate"
              value={percentage}
              color={severity}
              sx={{ mt: 1 }}
            />
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

function OperationsHealthTab() {
  const { data: healthSummary, isLoading } = useHealthSummary();

  if (isLoading || !healthSummary) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
        return "success";
      case "degraded":
        return "warning";
      case "unhealthy":
        return "error";
      default:
        return "default";
    }
  };

  return (
    <Grid container spacing={3}>
      {/* Overall Status */}
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Stack direction="row" spacing={2} alignItems="center">
              <Chip
                label={`Overall Status: ${healthSummary.status.toUpperCase()}`}
                color={getStatusColor(healthSummary.status) as any}
                size="large"
              />
              <Typography variant="body2" color="text.secondary">
                Last updated: {new Date(healthSummary.timestamp * 1000).toLocaleString()}
              </Typography>
            </Stack>
          </CardContent>
        </Card>
      </Grid>

      {/* Health Checks */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardHeader title="Health Checks" />
          <CardContent>
            <Stack spacing={2}>
              {Object.entries(healthSummary.checks).map(([name, check]) => (
                <Box key={name}>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Chip
                      label={check.healthy ? "Healthy" : "Unhealthy"}
                      color={check.healthy ? "success" : "error"}
                      size="small"
                    />
                    <Typography variant="body2">
                      <strong>{name.replace(/_/g, " ")}</strong>
                    </Typography>
                  </Stack>
                  {check.error && (
                    <Typography variant="caption" color="error" sx={{ ml: 5 }}>
                      {check.error}
                    </Typography>
                  )}
                </Box>
              ))}
            </Stack>
          </CardContent>
        </Card>
      </Grid>

      {/* DLQ Stats */}
      <Grid item xs={12} md={6}>
        <DeadLetterQueueStats />
      </Grid>

      {/* Circuit Breakers */}
      <Grid item xs={12}>
        <CircuitBreakerStatus />
      </Grid>
    </Grid>
  );
}

export default function HealthPage() {
  const [tabValue, setTabValue] = useState(0);
  const navigate = useNavigate();

  const { data: status, isLoading: statusLoading } = usePipelineStatus();
  const { data: metrics, isLoading: metricsLoading } = useSystemMetrics();
  const { data: eseCandidates } = useESECandidates();

  // Prepare system metrics plot data
  const metricsPlotData = useMemo(() => {
    if (!metrics) return { data: [], layout: {} };

    const data: Data[] = [
      {
        type: "scatter",
        mode: "lines",
        name: "CPU %",
        x: [new Date()],
        y: [metrics.cpu_percent],
        line: { color: "#90caf9" },
      },
      {
        type: "scatter",
        mode: "lines",
        name: "Memory %",
        x: [new Date()],
        y: [metrics.mem_percent],
        line: { color: "#a5d6a7" },
      },
    ];

    const layout: Partial<Layout> = {
      title: "System Resource Usage",
      xaxis: { title: "Time" },
      yaxis: { title: "Usage (%)", range: [0, 100] },
      hovermode: "closest",
      template: "plotly_dark",
    };

    return { data, layout };
  }, [metrics]);

  // Prepare queue state distribution
  const queueDistribution = useMemo(() => {
    if (!status) return null;

    const states = [
      { name: "Completed", value: status.queue.completed, color: "#4caf50" },
      { name: "Pending", value: status.queue.pending, color: "#ff9800" },
      { name: "In Progress", value: status.queue.in_progress, color: "#2196f3" },
      { name: "Failed", value: status.queue.failed, color: "#f44336" },
      { name: "Collecting", value: status.queue.collecting, color: "#9e9e9e" },
    ].filter((s) => s.value > 0);

    return states;
  }, [status]);

  return (
    <>
      <PageBreadcrumbs />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Typography variant="h3" gutterBottom sx={{ mb: 4 }}>
          System Health & Diagnostics
        </Typography>

        <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ mb: 3 }}>
          <Tab label="System Monitoring" />
          <Tab label="Queue Status" />
          <Tab label="Operations Health" />
          <Tab label="QA Diagnostics" />
        </Tabs>

        {/* System Monitoring Tab */}
        <TabPanel value={tabValue} index={0}>
          {metricsLoading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Grid container spacing={3}>
              {/* Current Metrics */}
              <Grid item xs={12}>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6} md={3}>
                    <MetricCard
                      label="CPU Usage"
                      value={metrics?.cpu_percent}
                      unit="%"
                      icon={<SpeedIcon />}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <MetricCard
                      label="Memory Usage"
                      value={metrics?.mem_percent}
                      unit="%"
                      icon={<MemoryIcon />}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <MetricCard
                      label="Disk Usage"
                      value={
                        metrics?.disk_total && metrics?.disk_used
                          ? (metrics.disk_used / metrics.disk_total) * 100
                          : undefined
                      }
                      unit="%"
                      icon={<StorageIcon />}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Card>
                      <CardContent>
                        <Stack direction="row" spacing={2} alignItems="center">
                          <SpeedIcon sx={{ color: "text.secondary" }} />
                          <Box>
                            <Typography variant="body2" color="text.secondary">
                              Load Average (1m)
                            </Typography>
                            <Typography variant="h5">
                              {metrics?.load_1?.toFixed(2) || "N/A"}
                            </Typography>
                          </Box>
                        </Stack>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </Grid>

              {/* Metrics Plot */}
              {metricsPlotData.data.length > 0 && (
                <Grid item xs={12}>
                  <Card>
                    <CardHeader title="Resource Usage Over Time" />
                    <CardContent>
                      <Plot
                        data={metricsPlotData.data}
                        layout={metricsPlotData.layout}
                        style={{ width: "100%", height: "400px" }}
                      />
                    </CardContent>
                  </Card>
                </Grid>
              )}

              {/* Detailed Metrics */}
              <Grid item xs={12} md={6}>
                <Card>
                  <CardHeader title="Memory Details" />
                  <CardContent>
                    <Stack spacing={2}>
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Total Memory
                        </Typography>
                        <Typography variant="h6">
                          {metrics?.mem_total
                            ? `${(metrics.mem_total / 1024 / 1024 / 1024).toFixed(2)} GB`
                            : "N/A"}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Used Memory
                        </Typography>
                        <Typography variant="h6">
                          {metrics?.mem_used
                            ? `${(metrics.mem_used / 1024 / 1024 / 1024).toFixed(2)} GB`
                            : "N/A"}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Load Averages
                        </Typography>
                        <Typography variant="body1">
                          1m: {metrics?.load_1?.toFixed(2) || "N/A"}
                        </Typography>
                        <Typography variant="body1">
                          5m: {metrics?.load_5?.toFixed(2) || "N/A"}
                        </Typography>
                        <Typography variant="body1">
                          15m: {metrics?.load_15?.toFixed(2) || "N/A"}
                        </Typography>
                      </Box>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={6}>
                <Card>
                  <CardHeader title="Disk Details" />
                  <CardContent>
                    <Stack spacing={2}>
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Total Disk Space
                        </Typography>
                        <Typography variant="h6">
                          {metrics?.disk_total
                            ? `${(metrics.disk_total / 1024 / 1024 / 1024).toFixed(2)} GB`
                            : "N/A"}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Used Disk Space
                        </Typography>
                        <Typography variant="h6">
                          {metrics?.disk_used
                            ? `${(metrics.disk_used / 1024 / 1024 / 1024).toFixed(2)} GB`
                            : "N/A"}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Available Disk Space
                        </Typography>
                        <Typography variant="h6">
                          {metrics?.disk_total && metrics?.disk_used
                            ? `${((metrics.disk_total - metrics.disk_used) / 1024 / 1024 / 1024).toFixed(2)} GB`
                            : "N/A"}
                        </Typography>
                      </Box>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
        </TabPanel>

        {/* Queue Status Tab */}
        <TabPanel value={tabValue} index={1}>
          {statusLoading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Grid container spacing={3}>
              {/* Queue Statistics */}
              <Grid item xs={12}>
                <Card>
                  <CardHeader title="Queue Statistics" />
                  <CardContent>
                    <Grid container spacing={2}>
                      <Grid item xs={12} sm={6} md={2.4}>
                        <Box textAlign="center">
                          <Typography variant="h4">{status?.queue.total || 0}</Typography>
                          <Typography variant="body2" color="text.secondary">
                            Total Groups
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={12} sm={6} md={2.4}>
                        <Box textAlign="center">
                          <Typography variant="h4" color="warning.main">
                            {status?.queue.pending || 0}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Pending
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={12} sm={6} md={2.4}>
                        <Box textAlign="center">
                          <Typography variant="h4" color="info.main">
                            {status?.queue.in_progress || 0}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            In Progress
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={12} sm={6} md={2.4}>
                        <Box textAlign="center">
                          <Typography variant="h4" color="success.main">
                            {status?.queue.completed || 0}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Completed
                          </Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={12} sm={6} md={2.4}>
                        <Box textAlign="center">
                          <Typography variant="h4" color="error.main">
                            {status?.queue.failed || 0}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Failed
                          </Typography>
                        </Box>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>

              {/* State Distribution */}
              {queueDistribution && queueDistribution.length > 0 && (
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardHeader title="State Distribution" />
                    <CardContent>
                      <Stack spacing={2}>
                        {queueDistribution.map((state) => (
                          <Box key={state.name}>
                            <Box
                              sx={{
                                display: "flex",
                                justifyContent: "space-between",
                                mb: 0.5,
                              }}
                            >
                              <Typography variant="body2">{state.name}</Typography>
                              <Typography variant="body2">
                                {state.value} (
                                {status?.queue.total
                                  ? ((state.value / status.queue.total) * 100).toFixed(1)
                                  : 0}
                                %)
                              </Typography>
                            </Box>
                            <LinearProgress
                              variant="determinate"
                              value={
                                status?.queue.total ? (state.value / status.queue.total) * 100 : 0
                              }
                              sx={{
                                height: 8,
                                borderRadius: 4,
                                backgroundColor: "rgba(255, 255, 255, 0.1)",
                                "& .MuiLinearProgress-bar": {
                                  backgroundColor: state.color,
                                },
                              }}
                            />
                          </Box>
                        ))}
                      </Stack>
                    </CardContent>
                  </Card>
                </Grid>
              )}

              {/* Recent Groups */}
              <Grid item xs={12} md={6}>
                <Card>
                  <CardHeader title="Recent Groups" />
                  <CardContent>
                    {status?.recent_groups && status.recent_groups.length > 0 ? (
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>Group ID</TableCell>
                              <TableCell>State</TableCell>
                              <TableCell>Subbands</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {status.recent_groups.slice(0, 10).map((group) => (
                              <TableRow key={group.group_id}>
                                <TableCell>{group.group_id}</TableCell>
                                <TableCell>
                                  <Chip
                                    label={group.state}
                                    size="small"
                                    color={
                                      group.state === "completed"
                                        ? "success"
                                        : group.state === "failed"
                                          ? "error"
                                          : group.state === "in_progress"
                                            ? "info"
                                            : "warning"
                                    }
                                  />
                                </TableCell>
                                <TableCell>
                                  {group.subbands_present}/{group.expected_subbands}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        No recent groups
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
        </TabPanel>

        {/* Operations Health Tab */}
        <TabPanel value={tabValue} index={2}>
          <OperationsHealthTab />
        </TabPanel>

        {/* QA Diagnostics Tab */}
        <TabPanel value={tabValue} index={3}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Alert severity="info">
                QA diagnostics and gallery features are available on the{" "}
                <strong
                  onClick={() => navigate("/qa")}
                  style={{ cursor: "pointer", textDecoration: "underline" }}
                >
                  QA Visualization page
                </strong>
                .
              </Alert>
            </Grid>

            <Grid item xs={12}>
              <Card>
                <CardHeader title="ESE Candidates" avatar={<AssessmentIcon />} />
                <CardContent>
                  {eseCandidates?.candidates && eseCandidates.candidates.length > 0 ? (
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Source ID</TableCell>
                            <TableCell>Max σ</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Last Detection</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {eseCandidates.candidates.slice(0, 10).map((candidate) => (
                            <TableRow key={candidate.source_id}>
                              <TableCell>{candidate.source_id}</TableCell>
                              <TableCell>{candidate.max_sigma_dev.toFixed(2)}</TableCell>
                              <TableCell>
                                <Chip
                                  label={candidate.status}
                                  size="small"
                                  color={
                                    candidate.status === "active"
                                      ? "error"
                                      : candidate.status === "resolved"
                                        ? "success"
                                        : "default"
                                  }
                                />
                              </TableCell>
                              <TableCell>
                                {dayjs(candidate.last_detection_at).format("YYYY-MM-DD HH:mm")}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      No ESE candidates detected
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>
      </Container>
    </>
  );
}
