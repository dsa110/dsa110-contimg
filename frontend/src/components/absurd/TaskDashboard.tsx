/**
 * Absurd Task Dashboard
 * Main UI for viewing and managing Absurd workflow tasks
 */

import { useState } from "react";
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  useTheme,
  alpha,
  CircularProgress,
} from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import { Refresh, PlayArrow, CheckCircle, Error, Cancel, Schedule } from "@mui/icons-material";
import { useAbsurdTasks, useQueueStats, useAbsurdHealth } from "../../api/absurdQueries";
import { TaskList } from "./TaskList";
import { TaskInspector } from "./TaskInspector";
import type { TaskInfo } from "../../api/absurd";

interface TaskDashboardProps {
  queueName?: string;
}

export function TaskDashboard({ queueName = "dsa110-pipeline" }: TaskDashboardProps) {
  const theme = useTheme();
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedTask, setSelectedTask] = useState<TaskInfo | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);

  // Fetch data
  const {
    data: tasks,
    isLoading: tasksLoading,
    refetch: refetchTasks,
  } = useAbsurdTasks(queueName, statusFilter === "all" ? undefined : statusFilter, 100);

  const { data: stats, refetch: refetchStats } = useQueueStats(queueName);
  const { data: health } = useAbsurdHealth();

  // Handle task selection
  const handleTaskClick = (task: TaskInfo) => {
    setSelectedTask(task);
    setInspectorOpen(true);
  };

  // Handle inspector close
  const handleInspectorClose = () => {
    setInspectorOpen(false);
    setSelectedTask(null);
  };

  // Handle refresh
  const handleRefresh = () => {
    refetchTasks();
    refetchStats();
  };

  // Get health status color
  const getHealthColor = () => {
    if (!health) return theme.palette.grey[500];
    switch (health.status) {
      case "healthy":
        return theme.palette.success.main;
      case "degraded":
        return theme.palette.warning.main;
      case "critical":
      case "down":
        return theme.palette.error.main;
      default:
        return theme.palette.grey[500];
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography variant="h4" component="h1">
          Absurd Task Manager
        </Typography>
        <Button startIcon={<Refresh />} onClick={handleRefresh} variant="outlined" size="small">
          Refresh
        </Button>
      </Box>

      {/* Health Status Card */}
      {health && (
        <Paper
          sx={{
            p: 2,
            mb: 3,
            bgcolor: alpha(getHealthColor(), 0.1),
            borderLeft: `4px solid ${getHealthColor()}`,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <Box
              sx={{
                width: 12,
                height: 12,
                borderRadius: "50%",
                bgcolor: getHealthColor(),
              }}
            />
            <Typography variant="h6" sx={{ textTransform: "capitalize" }}>
              {health.status}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {health.message}
            </Typography>
          </Box>
        </Paper>
      )}

      {/* Queue Statistics */}
      {stats && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={2}>
            <Card sx={{ bgcolor: alpha(theme.palette.warning.main, 0.1) }}>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                  <Schedule sx={{ color: theme.palette.warning.main }} />
                  <Typography variant="h4" sx={{ color: theme.palette.warning.main }}>
                    {stats.pending}
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Pending
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={2}>
            <Card sx={{ bgcolor: alpha(theme.palette.info.main, 0.1) }}>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                  <PlayArrow sx={{ color: theme.palette.info.main }} />
                  <Typography variant="h4" sx={{ color: theme.palette.info.main }}>
                    {stats.claimed}
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  In Progress
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={2}>
            <Card sx={{ bgcolor: alpha(theme.palette.success.main, 0.1) }}>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                  <CheckCircle sx={{ color: theme.palette.success.main }} />
                  <Typography variant="h4" sx={{ color: theme.palette.success.main }}>
                    {stats.completed}
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Completed
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={2}>
            <Card sx={{ bgcolor: alpha(theme.palette.error.main, 0.1) }}>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                  <Error sx={{ color: theme.palette.error.main }} />
                  <Typography variant="h4" sx={{ color: theme.palette.error.main }}>
                    {stats.failed}
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Failed
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={2}>
            <Card sx={{ bgcolor: alpha(theme.palette.grey[500], 0.1) }}>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                  <Cancel sx={{ color: theme.palette.grey[500] }} />
                  <Typography variant="h4" sx={{ color: theme.palette.grey[500] }}>
                    {stats.cancelled}
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Cancelled
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={2}>
            <Card sx={{ bgcolor: alpha(theme.palette.primary.main, 0.1) }}>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                  <Typography variant="h4" sx={{ color: theme.palette.primary.main }}>
                    {stats.total}
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Total
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Status Filter</InputLabel>
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                label="Status Filter"
              >
                <MenuItem value="all">All Tasks</MenuItem>
                <MenuItem value="pending">Pending</MenuItem>
                <MenuItem value="claimed">In Progress</MenuItem>
                <MenuItem value="completed">Completed</MenuItem>
                <MenuItem value="failed">Failed</MenuItem>
                <MenuItem value="cancelled">Cancelled</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Chip label={`Queue: ${queueName}`} color="primary" variant="outlined" />
          </Grid>
        </Grid>
      </Paper>

      {/* Task List */}
      <TaskList tasks={tasks?.tasks || []} loading={tasksLoading} onTaskClick={handleTaskClick} />

      {/* Task Inspector Drawer */}
      {selectedTask && (
        <TaskInspector task={selectedTask} open={inspectorOpen} onClose={handleInspectorClose} />
      )}
    </Box>
  );
}
