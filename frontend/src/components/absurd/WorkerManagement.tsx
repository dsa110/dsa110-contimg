/**
 * Worker Management component for viewing and monitoring Absurd workers.
 *
 * Displays worker pool status, individual worker health, and performance metrics.
 */

import React from "react";
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Stack,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Tooltip,
  LinearProgress,
} from "@mui/material";
import {
  CheckCircle as ActiveIcon,
  PauseCircle as IdleIcon,
  Warning as StaleIcon,
  Error as CrashedIcon,
  Person as WorkerIcon,
} from "@mui/icons-material";
import { useWorkers, useWorkerMetrics } from "../../api/absurdQueries";

interface WorkerManagementProps {
  /** Whether to show metrics cards */
  showMetrics?: boolean;
  /** Whether to show detailed worker list */
  showWorkerList?: boolean;
}

const formatDuration = (seconds: number): string => {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
};

const getStateIcon = (state: string) => {
  switch (state) {
    case "active":
      return <ActiveIcon color="success" fontSize="small" />;
    case "idle":
      return <IdleIcon color="info" fontSize="small" />;
    case "stale":
      return <StaleIcon color="warning" fontSize="small" />;
    case "crashed":
      return <CrashedIcon color="error" fontSize="small" />;
    default:
      return <WorkerIcon color="disabled" fontSize="small" />;
  }
};

const getStateColor = (state: string): "success" | "info" | "warning" | "error" | "default" => {
  switch (state) {
    case "active":
      return "success";
    case "idle":
      return "info";
    case "stale":
      return "warning";
    case "crashed":
      return "error";
    default:
      return "default";
  }
};

export const WorkerManagement: React.FC<WorkerManagementProps> = ({
  showMetrics = true,
  showWorkerList = true,
}) => {
  const { data: workers, isLoading: workersLoading, error: workersError } = useWorkers();
  const { data: metrics, isLoading: metricsLoading } = useWorkerMetrics();

  const isLoading = workersLoading || metricsLoading;

  return (
    <Box>
      {/* Worker Pool Metrics */}
      {showMetrics && (
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 3 }}>
          {/* Total Workers Card */}
          <Card sx={{ flex: 1, minWidth: 150 }}>
            <CardContent>
              <Typography color="text.secondary" variant="caption">
                Total Workers
              </Typography>
              <Typography variant="h4">
                {metricsLoading ? <CircularProgress size={24} /> : metrics?.total_workers || 0}
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                <Chip
                  size="small"
                  icon={<ActiveIcon />}
                  label={`${metrics?.active_workers || 0} active`}
                  color="success"
                  variant="outlined"
                />
                <Chip
                  size="small"
                  icon={<IdleIcon />}
                  label={`${metrics?.idle_workers || 0} idle`}
                  color="info"
                  variant="outlined"
                />
              </Stack>
            </CardContent>
          </Card>

          {/* Worker Health Card */}
          <Card sx={{ flex: 1, minWidth: 150 }}>
            <CardContent>
              <Typography color="text.secondary" variant="caption">
                Worker Health
              </Typography>
              <Box sx={{ mt: 1 }}>
                {metricsLoading ? (
                  <CircularProgress size={24} />
                ) : (
                  <>
                    {(metrics?.crashed_workers || 0) > 0 ? (
                      <Chip
                        icon={<CrashedIcon />}
                        label={`${metrics?.crashed_workers} crashed`}
                        color="error"
                        sx={{ mr: 1, mb: 1 }}
                      />
                    ) : null}
                    {(metrics?.timed_out_workers || 0) > 0 ? (
                      <Chip
                        icon={<StaleIcon />}
                        label={`${metrics?.timed_out_workers} stale`}
                        color="warning"
                        sx={{ mr: 1, mb: 1 }}
                      />
                    ) : null}
                    {(metrics?.crashed_workers || 0) === 0 &&
                      (metrics?.timed_out_workers || 0) === 0 && (
                        <Chip icon={<ActiveIcon />} label="All workers healthy" color="success" />
                      )}
                  </>
                )}
              </Box>
            </CardContent>
          </Card>

          {/* Performance Card */}
          <Card sx={{ flex: 1, minWidth: 150 }}>
            <CardContent>
              <Typography color="text.secondary" variant="caption">
                Avg Tasks/Worker
              </Typography>
              <Typography variant="h4">
                {metricsLoading ? (
                  <CircularProgress size={24} />
                ) : (
                  (metrics?.avg_tasks_per_worker || 0).toFixed(1)
                )}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Avg Uptime: {formatDuration(metrics?.avg_worker_uptime_sec || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Stack>
      )}

      {/* Worker List */}
      {showWorkerList && (
        <Paper elevation={1}>
          <Box sx={{ p: 2, borderBottom: 1, borderColor: "divider" }}>
            <Typography variant="h6">Workers</Typography>
          </Box>

          {workersError ? (
            <Alert severity="error" sx={{ m: 2 }}>
              Failed to load workers:{" "}
              {workersError instanceof Error ? workersError.message : "Unknown error"}
            </Alert>
          ) : workersLoading ? (
            <Box sx={{ p: 4, display: "flex", justifyContent: "center" }}>
              <CircularProgress />
            </Box>
          ) : workers?.workers.length === 0 ? (
            <Box sx={{ p: 4, textAlign: "center" }}>
              <Typography color="text.secondary">
                No workers registered. Start a worker to begin processing tasks.
              </Typography>
            </Box>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Worker ID</TableCell>
                    <TableCell>State</TableCell>
                    <TableCell align="right">Tasks</TableCell>
                    <TableCell>Uptime</TableCell>
                    <TableCell>Last Seen</TableCell>
                    <TableCell>Current Task</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {workers?.workers.map((worker) => (
                    <TableRow
                      key={worker.worker_id}
                      sx={{
                        bgcolor:
                          worker.state === "crashed"
                            ? "error.dark"
                            : worker.state === "stale"
                              ? "warning.dark"
                              : "transparent",
                        opacity: worker.state === "crashed" ? 0.7 : 1,
                      }}
                    >
                      <TableCell>
                        <Tooltip title={worker.worker_id}>
                          <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                            {worker.worker_id.substring(0, 12)}...
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        <Chip
                          icon={getStateIcon(worker.state)}
                          label={worker.state}
                          size="small"
                          color={getStateColor(worker.state)}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">{worker.task_count}</Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {formatDuration(worker.uptime_seconds)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {worker.last_seen ? (
                          <Tooltip title={new Date(worker.last_seen).toLocaleString()}>
                            <Typography variant="body2">
                              {new Date(worker.last_seen).toLocaleTimeString()}
                            </Typography>
                          </Tooltip>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            -
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {worker.current_task_id ? (
                          <Tooltip title={worker.current_task_id}>
                            <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                              {worker.current_task_id.substring(0, 8)}...
                            </Typography>
                          </Tooltip>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            -
                          </Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {/* Summary Footer */}
          {workers && workers.workers.length > 0 && (
            <Box
              sx={{
                p: 1.5,
                borderTop: 1,
                borderColor: "divider",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <Stack direction="row" spacing={2}>
                <Typography variant="caption" color="text.secondary">
                  Active: {workers.active}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Idle: {workers.idle}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Stale: {workers.stale}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Crashed: {workers.crashed}
                </Typography>
              </Stack>
              <Typography variant="caption" color="text.secondary">
                Total: {workers.total}
              </Typography>
            </Box>
          )}
        </Paper>
      )}
    </Box>
  );
};

export default WorkerManagement;
