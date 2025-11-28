/**
 * Task List Component
 * Displays Absurd tasks in a table format
 */

import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  Box,
  Typography,
  CircularProgress,
  useTheme,
} from "@mui/material";
import { Visibility, AccessTime, CheckCircle, Error, Cancel } from "@mui/icons-material";
import type { TaskInfo } from "../../api/absurd";

interface TaskListProps {
  tasks: TaskInfo[];
  loading?: boolean;
  onTaskClick: (task: TaskInfo) => void;
}

export function TaskList({ tasks, loading, onTaskClick }: TaskListProps) {
  const theme = useTheme();

  // Get status chip props
  const getStatusChip = (status: string) => {
    switch (status) {
      case "pending":
        return { label: "Pending", color: "warning" as const, icon: <AccessTime /> };
      case "claimed":
        return {
          label: "In Progress",
          color: "info" as const,
          icon: <CircularProgress size={16} />,
        };
      case "completed":
        return { label: "Completed", color: "success" as const, icon: <CheckCircle /> };
      case "failed":
        return { label: "Failed", color: "error" as const, icon: <Error /> };
      case "cancelled":
        return { label: "Cancelled", color: "default" as const, icon: <Cancel /> };
      default:
        return { label: status, color: "default" as const };
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string | null) => {
    if (!timestamp) return "-";
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  // Format duration
  const formatDuration = (start: string | null, end: string | null) => {
    if (!start) return "-";
    const startTime = new Date(start).getTime();
    const endTime = end ? new Date(end).getTime() : Date.now();
    const durationSec = (endTime - startTime) / 1000;

    if (durationSec < 60) return `${durationSec.toFixed(0)}s`;
    if (durationSec < 3600) return `${(durationSec / 60).toFixed(1)}m`;
    return `${(durationSec / 3600).toFixed(1)}h`;
  };

  // Get priority color
  const getPriorityColor = (priority: number) => {
    if (priority >= 15) return theme.palette.error.main;
    if (priority >= 10) return theme.palette.warning.main;
    if (priority >= 5) return theme.palette.info.main;
    return theme.palette.grey[500];
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (tasks.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: "center" }}>
        <Typography variant="body1" color="text.secondary">
          No tasks found
        </Typography>
      </Paper>
    );
  }

  return (
    <TableContainer component={Paper}>
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell>Task ID</TableCell>
            <TableCell>Task Name</TableCell>
            <TableCell>Status</TableCell>
            <TableCell align="center">Priority</TableCell>
            <TableCell align="center">Retry</TableCell>
            <TableCell>Created</TableCell>
            <TableCell>Duration</TableCell>
            <TableCell align="center">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {tasks.map((task) => {
            const statusChip = getStatusChip(task.status);
            return (
              <TableRow
                key={task.task_id}
                hover
                onClick={() => onTaskClick(task)}
                sx={{ cursor: "pointer" }}
              >
                <TableCell>
                  <Tooltip title={task.task_id}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontFamily: "monospace",
                        fontSize: "0.75rem",
                      }}
                    >
                      {task.task_id.substring(0, 8)}...
                    </Typography>
                  </Tooltip>
                </TableCell>

                <TableCell>
                  <Typography variant="body2">{task.task_name}</Typography>
                </TableCell>

                <TableCell>
                  <Chip
                    label={statusChip.label}
                    color={statusChip.color}
                    size="small"
                    icon={statusChip.icon}
                  />
                </TableCell>

                <TableCell align="center">
                  <Chip
                    label={task.priority}
                    size="small"
                    sx={{
                      bgcolor: getPriorityColor(task.priority),
                      color: "white",
                      fontWeight: "bold",
                    }}
                  />
                </TableCell>

                <TableCell align="center">
                  <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                    {task.retry_count}
                  </Typography>
                </TableCell>

                <TableCell>
                  <Typography variant="body2" sx={{ fontSize: "0.75rem" }}>
                    {formatTimestamp(task.created_at)}
                  </Typography>
                </TableCell>

                <TableCell>
                  <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                    {formatDuration(task.claimed_at, task.completed_at)}
                  </Typography>
                </TableCell>

                <TableCell align="center">
                  <Tooltip title="View Details">
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        onTaskClick(task);
                      }}
                    >
                      <Visibility fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
