/**
 * ScheduleManager - UI for managing scheduled tasks.
 *
 * Features:
 * - List all scheduled tasks with their status
 * - Create new schedules with cron expression validation
 * - Edit, pause/resume, and delete schedules
 * - Trigger schedules manually
 * - Visual cron expression builder hints
 */

import React, { useState } from "react";
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
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Tooltip,
  useTheme,
  alpha,
  Stack,
  Alert,
  Collapse,
} from "@mui/material";
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Schedule as ScheduleIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
} from "@mui/icons-material";
import { format, parseISO } from "date-fns";
import {
  useSchedules,
  useCreateSchedule,
  useUpdateSchedule,
  useDeleteSchedule,
  useTriggerSchedule,
} from "../../api/absurdQueries";
import type { ScheduledTask, ScheduleCreateRequest } from "../../api/absurd";

interface ScheduleManagerProps {
  queueName?: string;
}

// Common cron expression presets
const CRON_PRESETS = [
  { label: "Every minute", value: "* * * * *" },
  { label: "Every 5 minutes", value: "*/5 * * * *" },
  { label: "Every 15 minutes", value: "*/15 * * * *" },
  { label: "Every hour", value: "0 * * * *" },
  { label: "Every 6 hours", value: "0 */6 * * *" },
  { label: "Daily at midnight", value: "0 0 * * *" },
  { label: "Daily at 6 AM", value: "0 6 * * *" },
  { label: "Weekly (Sunday)", value: "0 0 * * 0" },
  { label: "Monthly (1st)", value: "0 0 1 * *" },
];

export function ScheduleManager({ queueName }: ScheduleManagerProps) {
  const theme = useTheme();
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState<ScheduledTask | null>(null);
  const [showCronHelp, setShowCronHelp] = useState(false);

  // Form state for create/edit
  const [formData, setFormData] = useState<Partial<ScheduleCreateRequest>>({
    name: "",
    task_name: "",
    queue_name: queueName || "dsa110-pipeline",
    cron_expression: "0 * * * *",
    params: {},
    priority: 0,
    description: "",
  });

  // Queries and mutations
  const { data: schedulesData, isLoading, refetch } = useSchedules(queueName);
  const createMutation = useCreateSchedule();
  const updateMutation = useUpdateSchedule();
  const deleteMutation = useDeleteSchedule();
  const triggerMutation = useTriggerSchedule();

  const schedules = schedulesData?.schedules || [];

  // Format timestamp for display
  const formatTime = (timestamp: string | null) => {
    if (!timestamp) return "N/A";
    try {
      return format(parseISO(timestamp), "MMM d, HH:mm");
    } catch {
      return timestamp;
    }
  };

  // Get state color
  const getStateColor = (state: string) => {
    switch (state) {
      case "active":
        return "success";
      case "paused":
        return "warning";
      case "disabled":
        return "error";
      default:
        return "default";
    }
  };

  // Handle create schedule
  const handleCreate = () => {
    if (!formData.name || !formData.task_name || !formData.cron_expression) return;

    createMutation.mutate(formData as ScheduleCreateRequest, {
      onSuccess: () => {
        setCreateDialogOpen(false);
        resetForm();
        refetch();
      },
    });
  };

  // Handle update schedule
  const handleUpdate = () => {
    if (!selectedSchedule) return;

    updateMutation.mutate(
      {
        name: selectedSchedule.name,
        request: {
          cron_expression: formData.cron_expression,
          priority: formData.priority,
          description: formData.description,
        },
      },
      {
        onSuccess: () => {
          setEditDialogOpen(false);
          setSelectedSchedule(null);
          resetForm();
          refetch();
        },
      }
    );
  };

  // Handle toggle state
  const handleToggleState = (schedule: ScheduledTask) => {
    const newState = schedule.state === "active" ? "paused" : "active";
    updateMutation.mutate(
      {
        name: schedule.name,
        request: { state: newState },
      },
      {
        onSuccess: () => refetch(),
      }
    );
  };

  // Handle delete
  const handleDelete = (name: string) => {
    if (window.confirm(`Delete schedule "${name}"?`)) {
      deleteMutation.mutate(name, {
        onSuccess: () => refetch(),
      });
    }
  };

  // Handle trigger
  const handleTrigger = (name: string) => {
    triggerMutation.mutate(name, {
      onSuccess: () => refetch(),
    });
  };

  // Reset form
  const resetForm = () => {
    setFormData({
      name: "",
      task_name: "",
      queue_name: queueName || "dsa110-pipeline",
      cron_expression: "0 * * * *",
      params: {},
      priority: 0,
      description: "",
    });
  };

  // Open edit dialog
  const openEditDialog = (schedule: ScheduledTask) => {
    setSelectedSchedule(schedule);
    setFormData({
      name: schedule.name,
      task_name: schedule.task_name,
      queue_name: schedule.queue_name,
      cron_expression: schedule.cron_expression,
      priority: schedule.priority,
      description: schedule.description || "",
    });
    setEditDialogOpen(true);
  };

  return (
    <Box>
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <ScheduleIcon sx={{ fontSize: 28, color: theme.palette.primary.main }} />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Scheduled Tasks
          </Typography>
          <Chip label={schedules.length} size="small" />
        </Box>

        <Stack direction="row" spacing={1}>
          <IconButton onClick={() => refetch()} size="small">
            <RefreshIcon />
          </IconButton>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
            size="small"
          >
            New Schedule
          </Button>
        </Stack>
      </Box>

      {/* Schedules Table */}
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: alpha(theme.palette.primary.main, 0.05) }}>
              <TableCell>Name</TableCell>
              <TableCell>Task</TableCell>
              <TableCell>Cron Expression</TableCell>
              <TableCell>State</TableCell>
              <TableCell>Last Run</TableCell>
              <TableCell>Next Run</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  Loading schedules...
                </TableCell>
              </TableRow>
            ) : schedules.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography color="text.secondary">
                    No scheduled tasks. Create one to get started.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              schedules.map((schedule) => (
                <TableRow key={schedule.schedule_id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {schedule.name}
                    </Typography>
                    {schedule.description && (
                      <Typography variant="caption" color="text.secondary">
                        {schedule.description}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip label={schedule.task_name} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <code
                      style={{
                        fontSize: "0.8rem",
                        backgroundColor: alpha(theme.palette.grey[500], 0.1),
                        padding: "2px 6px",
                        borderRadius: 4,
                      }}
                    >
                      {schedule.cron_expression}
                    </code>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={schedule.state}
                      size="small"
                      color={getStateColor(schedule.state) as any}
                    />
                  </TableCell>
                  <TableCell>{formatTime(schedule.last_run_at)}</TableCell>
                  <TableCell>{formatTime(schedule.next_run_at)}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="Trigger now">
                      <IconButton
                        size="small"
                        onClick={() => handleTrigger(schedule.name)}
                        disabled={triggerMutation.isPending}
                      >
                        <PlayIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title={schedule.state === "active" ? "Pause" : "Resume"}>
                      <IconButton size="small" onClick={() => handleToggleState(schedule)}>
                        {schedule.state === "active" ? (
                          <PauseIcon fontSize="small" />
                        ) : (
                          <PlayIcon fontSize="small" color="success" />
                        )}
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Edit">
                      <IconButton size="small" onClick={() => openEditDialog(schedule)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton
                        size="small"
                        onClick={() => handleDelete(schedule.name)}
                        color="error"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Create Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create Scheduled Task</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Schedule Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              fullWidth
              required
              helperText="Unique identifier for this schedule"
            />

            <TextField
              label="Task Name"
              value={formData.task_name}
              onChange={(e) => setFormData({ ...formData, task_name: e.target.value })}
              fullWidth
              required
              helperText="Task type to spawn (e.g., convert, calibrate, image)"
            />

            <TextField
              label="Queue Name"
              value={formData.queue_name}
              onChange={(e) => setFormData({ ...formData, queue_name: e.target.value })}
              fullWidth
            />

            <Box>
              <TextField
                label="Cron Expression"
                value={formData.cron_expression}
                onChange={(e) => setFormData({ ...formData, cron_expression: e.target.value })}
                fullWidth
                required
                helperText="minute hour day month weekday"
              />
              <Button
                size="small"
                onClick={() => setShowCronHelp(!showCronHelp)}
                endIcon={showCronHelp ? <CollapseIcon /> : <ExpandIcon />}
                sx={{ mt: 0.5 }}
              >
                {showCronHelp ? "Hide" : "Show"} presets
              </Button>
              <Collapse in={showCronHelp}>
                <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                  {CRON_PRESETS.map((preset) => (
                    <Chip
                      key={preset.value}
                      label={preset.label}
                      size="small"
                      onClick={() => setFormData({ ...formData, cron_expression: preset.value })}
                      variant={formData.cron_expression === preset.value ? "filled" : "outlined"}
                      color={formData.cron_expression === preset.value ? "primary" : "default"}
                    />
                  ))}
                </Box>
              </Collapse>
            </Box>

            <TextField
              label="Priority"
              type="number"
              value={formData.priority}
              onChange={(e) =>
                setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })
              }
              fullWidth
              helperText="Higher values = higher priority"
            />

            <TextField
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={
              createMutation.isPending ||
              !formData.name ||
              !formData.task_name ||
              !formData.cron_expression
            }
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit Schedule: {selectedSchedule?.name}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Alert severity="info">
              Name and task type cannot be changed. Create a new schedule if needed.
            </Alert>

            <Box>
              <TextField
                label="Cron Expression"
                value={formData.cron_expression}
                onChange={(e) => setFormData({ ...formData, cron_expression: e.target.value })}
                fullWidth
                required
              />
              <Button
                size="small"
                onClick={() => setShowCronHelp(!showCronHelp)}
                endIcon={showCronHelp ? <CollapseIcon /> : <ExpandIcon />}
                sx={{ mt: 0.5 }}
              >
                {showCronHelp ? "Hide" : "Show"} presets
              </Button>
              <Collapse in={showCronHelp}>
                <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                  {CRON_PRESETS.map((preset) => (
                    <Chip
                      key={preset.value}
                      label={preset.label}
                      size="small"
                      onClick={() => setFormData({ ...formData, cron_expression: preset.value })}
                      variant={formData.cron_expression === preset.value ? "filled" : "outlined"}
                      color={formData.cron_expression === preset.value ? "primary" : "default"}
                    />
                  ))}
                </Box>
              </Collapse>
            </Box>

            <TextField
              label="Priority"
              type="number"
              value={formData.priority}
              onChange={(e) =>
                setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })
              }
              fullWidth
            />

            <TextField
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleUpdate} disabled={updateMutation.isPending}>
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default ScheduleManager;
