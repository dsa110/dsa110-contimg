/**
 * Task Inspector Component
 * Detailed view of a single Absurd task with actions (retry, cancel)
 */

import { useState } from "react";
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Divider,
  Chip,
  Button,
  Paper,
  Grid,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  useTheme,
  alpha,
} from "@mui/material";
import {
  Close,
  Refresh,
  Cancel as CancelIcon,
  CheckCircle,
  Error,
  Schedule,
  PlayArrow,
  ExpandMore,
  Code,
} from "@mui/icons-material";
import { useAbsurdTask, useCancelTask, useRetryTask } from "../../api/absurdQueries";
import type { TaskInfo } from "../../api/absurd";

interface TaskInspectorProps {
  task: TaskInfo;
  open: boolean;
  onClose: () => void;
}

export function TaskInspector({ task: initialTask, open, onClose }: TaskInspectorProps) {
  const theme = useTheme();
  const [expandedSection, setExpandedSection] = useState<string | false>("details");

  // Fetch latest task data
  const { data: task = initialTask, isLoading } = useAbsurdTask(initialTask.task_id);

  // Mutations
  const cancelMutation = useCancelTask();
  const retryMutation = useRetryTask();

  // Handle cancel
  const handleCancel = async () => {
    if (window.confirm(`Cancel task ${task.task_id.substring(0, 8)}...?`)) {
      await cancelMutation.mutateAsync(task.task_id);
    }
  };

  // Handle retry
  const handleRetry = async () => {
    if (window.confirm(`Retry task ${task.task_id.substring(0, 8)}...?`)) {
      await retryMutation.mutateAsync(task);
    }
  };

  // Get status chip
  const getStatusChip = () => {
    switch (task.status) {
      case "pending":
        return { label: "Pending", color: "warning" as const, icon: <Schedule /> };
      case "claimed":
        return { label: "In Progress", color: "info" as const, icon: <PlayArrow /> };
      case "completed":
        return { label: "Completed", color: "success" as const, icon: <CheckCircle /> };
      case "failed":
        return { label: "Failed", color: "error" as const, icon: <Error /> };
      case "cancelled":
        return { label: "Cancelled", color: "default" as const, icon: <CancelIcon /> };
      default:
        return { label: task.status, color: "default" as const };
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string | null) => {
    if (!timestamp) return "Not set";
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  // Format duration
  const formatDuration = (start: string | null, end: string | null) => {
    if (!start) return "N/A";
    const startTime = new Date(start).getTime();
    const endTime = end ? new Date(end).getTime() : Date.now();
    const durationSec = (endTime - startTime) / 1000;

    if (durationSec < 60) return `${durationSec.toFixed(0)} seconds`;
    if (durationSec < 3600) return `${(durationSec / 60).toFixed(1)} minutes`;
    return `${(durationSec / 3600).toFixed(1)} hours`;
  };

  const statusChip = getStatusChip();

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: { width: { xs: "100%", sm: 600, md: 800 } },
      }}
    >
      <Box sx={{ p: 3, height: "100%", overflow: "auto" }}>
        {/* Header */}
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h5">Task Details</Typography>
          <IconButton onClick={onClose} size="small">
            <Close />
          </IconButton>
        </Box>

        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {!isLoading && (
          <>
            {/* Status Alert */}
            {task.status === "failed" && task.error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Error:
                </Typography>
                <Typography variant="body2">{task.error}</Typography>
              </Alert>
            )}

            {task.status === "completed" && task.result && (
              <Alert severity="success" sx={{ mb: 2 }}>
                Task completed successfully
              </Alert>
            )}

            {/* Action Buttons */}
            <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
              {task.status === "pending" && (
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<CancelIcon />}
                  onClick={handleCancel}
                  disabled={cancelMutation.isPending}
                >
                  Cancel Task
                </Button>
              )}

              {task.status === "failed" && (
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<Refresh />}
                  onClick={handleRetry}
                  disabled={retryMutation.isPending}
                >
                  Retry Task
                </Button>
              )}

              {(task.status === "pending" || task.status === "claimed") && (
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<CancelIcon />}
                  onClick={handleCancel}
                  disabled={cancelMutation.isPending}
                >
                  Cancel
                </Button>
              )}
            </Box>

            {/* Basic Information */}
            <Accordion
              expanded={expandedSection === "details"}
              onChange={(_, isExpanded) => setExpandedSection(isExpanded ? "details" : false)}
            >
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="h6">Task Information</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <Typography variant="caption" color="text.secondary">
                      Task ID
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{ fontFamily: "monospace", wordBreak: "break-all" }}
                    >
                      {task.task_id}
                    </Typography>
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">
                      Task Name
                    </Typography>
                    <Typography variant="body2">{task.task_name}</Typography>
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">
                      Queue Name
                    </Typography>
                    <Typography variant="body2">{task.queue_name}</Typography>
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">
                      Status
                    </Typography>
                    <Box sx={{ mt: 0.5 }}>
                      <Chip
                        label={statusChip.label}
                        color={statusChip.color}
                        icon={statusChip.icon}
                        size="small"
                      />
                    </Box>
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">
                      Priority
                    </Typography>
                    <Box sx={{ mt: 0.5 }}>
                      <Chip
                        label={task.priority}
                        size="small"
                        sx={{
                          bgcolor:
                            task.priority >= 15
                              ? theme.palette.error.main
                              : task.priority >= 10
                                ? theme.palette.warning.main
                                : theme.palette.info.main,
                          color: "white",
                          fontWeight: "bold",
                        }}
                      />
                    </Box>
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">
                      Retry Count
                    </Typography>
                    <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                      {task.retry_count}
                    </Typography>
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>

            {/* Timeline */}
            <Accordion
              expanded={expandedSection === "timeline"}
              onChange={(_, isExpanded) => setExpandedSection(isExpanded ? "timeline" : false)}
              sx={{ mt: 2 }}
            >
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="h6">Timeline</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <Paper sx={{ p: 2, bgcolor: alpha(theme.palette.primary.main, 0.05) }}>
                      <Typography variant="caption" color="text.secondary">
                        Created At
                      </Typography>
                      <Typography variant="body2">{formatTimestamp(task.created_at)}</Typography>
                    </Paper>
                  </Grid>

                  {task.claimed_at && (
                    <Grid item xs={12}>
                      <Paper sx={{ p: 2, bgcolor: alpha(theme.palette.info.main, 0.05) }}>
                        <Typography variant="caption" color="text.secondary">
                          Claimed At
                        </Typography>
                        <Typography variant="body2">{formatTimestamp(task.claimed_at)}</Typography>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ mt: 1, display: "block" }}
                        >
                          Wait Time: {formatDuration(task.created_at, task.claimed_at)}
                        </Typography>
                      </Paper>
                    </Grid>
                  )}

                  {task.completed_at && (
                    <Grid item xs={12}>
                      <Paper sx={{ p: 2, bgcolor: alpha(theme.palette.success.main, 0.05) }}>
                        <Typography variant="caption" color="text.secondary">
                          Completed At
                        </Typography>
                        <Typography variant="body2">
                          {formatTimestamp(task.completed_at)}
                        </Typography>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ mt: 1, display: "block" }}
                        >
                          Execution Time: {formatDuration(task.claimed_at, task.completed_at)}
                        </Typography>
                      </Paper>
                    </Grid>
                  )}
                </Grid>
              </AccordionDetails>
            </Accordion>

            {/* Parameters */}
            <Accordion
              expanded={expandedSection === "params"}
              onChange={(_, isExpanded) => setExpandedSection(isExpanded ? "params" : false)}
              sx={{ mt: 2 }}
            >
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="h6">Task Parameters</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Paper
                  sx={{
                    p: 2,
                    bgcolor: theme.palette.background.paper,
                    maxHeight: 400,
                    overflow: "auto",
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                    <Code fontSize="small" />
                    <Typography variant="caption" color="text.secondary">
                      JSON
                    </Typography>
                  </Box>
                  <Typography
                    variant="body2"
                    component="pre"
                    sx={{
                      fontFamily: "monospace",
                      fontSize: "0.75rem",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                    }}
                  >
                    {JSON.stringify(task.params, null, 2)}
                  </Typography>
                </Paper>
              </AccordionDetails>
            </Accordion>

            {/* Result */}
            {task.result && (
              <Accordion
                expanded={expandedSection === "result"}
                onChange={(_, isExpanded) => setExpandedSection(isExpanded ? "result" : false)}
                sx={{ mt: 2 }}
              >
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="h6">Result</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Paper
                    sx={{
                      p: 2,
                      bgcolor: alpha(theme.palette.success.main, 0.05),
                      maxHeight: 400,
                      overflow: "auto",
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                      <CheckCircle fontSize="small" color="success" />
                      <Typography variant="caption" color="text.secondary">
                        JSON
                      </Typography>
                    </Box>
                    <Typography
                      variant="body2"
                      component="pre"
                      sx={{
                        fontFamily: "monospace",
                        fontSize: "0.75rem",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                      }}
                    >
                      {JSON.stringify(task.result, null, 2)}
                    </Typography>
                  </Paper>
                </AccordionDetails>
              </Accordion>
            )}

            {/* Error Details */}
            {task.error && (
              <Accordion
                expanded={expandedSection === "error"}
                onChange={(_, isExpanded) => setExpandedSection(isExpanded ? "error" : false)}
                sx={{ mt: 2 }}
              >
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="h6" color="error">
                    Error Details
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Paper
                    sx={{
                      p: 2,
                      bgcolor: alpha(theme.palette.error.main, 0.05),
                      maxHeight: 400,
                      overflow: "auto",
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                      <Error fontSize="small" color="error" />
                      <Typography variant="caption" color="text.secondary">
                        Error Message
                      </Typography>
                    </Box>
                    <Typography
                      variant="body2"
                      component="pre"
                      sx={{
                        fontFamily: "monospace",
                        fontSize: "0.75rem",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        color: theme.palette.error.main,
                      }}
                    >
                      {task.error}
                    </Typography>
                  </Paper>
                </AccordionDetails>
              </Accordion>
            )}
          </>
        )}
      </Box>
    </Drawer>
  );
}
