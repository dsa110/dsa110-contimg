/**
 * Bulk Task Operations Component
 * Allows selecting multiple tasks and performing bulk actions
 */

import { useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  Paper,
  Typography,
  Stack,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  useTheme,
  alpha,
} from "@mui/material";
import {
  Cancel as CancelIcon,
  Refresh,
  DeleteForever,
  CheckCircle,
  SelectAll,
  Clear,
} from "@mui/icons-material";
import { useCancelTask, useRetryTask } from "../../api/absurdQueries";
import type { TaskInfo } from "../../api/absurd";

interface BulkTaskOperationsProps {
  tasks: TaskInfo[];
  selectedTasks: string[];
  onSelectionChange: (taskIds: string[]) => void;
  onOperationComplete?: () => void;
}

export function BulkTaskOperations({
  tasks,
  selectedTasks,
  onSelectionChange,
  onOperationComplete,
}: BulkTaskOperationsProps) {
  const theme = useTheme();
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    operation: "cancel" | "retry" | "delete" | null;
    count: number;
  }>({
    open: false,
    operation: null,
    count: 0,
  });

  const cancelMutation = useCancelTask();
  const retryMutation = useRetryTask();

  // Handle select all
  const handleSelectAll = () => {
    if (selectedTasks.length === tasks.length) {
      onSelectionChange([]);
    } else {
      onSelectionChange(tasks.map((t) => t.task_id));
    }
  };

  // Handle clear selection
  const handleClearSelection = () => {
    onSelectionChange([]);
  };

  // Open confirmation dialog
  const openConfirmDialog = (operation: "cancel" | "retry" | "delete") => {
    setConfirmDialog({
      open: true,
      operation,
      count: selectedTasks.length,
    });
  };

  // Close confirmation dialog
  const closeConfirmDialog = () => {
    setConfirmDialog({
      open: false,
      operation: null,
      count: 0,
    });
  };

  // Execute bulk operation
  const executeBulkOperation = async () => {
    const { operation } = confirmDialog;
    if (!operation) return;

    try {
      const selectedTaskObjects = tasks.filter((t) => selectedTasks.includes(t.task_id));

      switch (operation) {
        case "cancel":
          await Promise.all(selectedTasks.map((id) => cancelMutation.mutateAsync(id)));
          break;
        case "retry":
          await Promise.all(selectedTaskObjects.map((task) => retryMutation.mutateAsync(task)));
          break;
        case "delete":
          // TODO: Implement delete mutation
          console.warn("Delete operation not yet implemented");
          break;
      }

      // Clear selection and close dialog
      onSelectionChange([]);
      closeConfirmDialog();

      // Notify parent
      onOperationComplete?.();
    } catch (error) {
      console.error("Bulk operation failed:", error);
    }
  };

  // Calculate selected task statuses
  const selectedTaskStatuses = tasks
    .filter((t) => selectedTasks.includes(t.task_id))
    .reduce(
      (acc, task) => {
        acc[task.status] = (acc[task.status] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );

  // Check if bulk operations are available
  const canCancel = selectedTasks.some((id) => {
    const task = tasks.find((t) => t.task_id === id);
    return task && (task.status === "pending" || task.status === "claimed");
  });

  const canRetry = selectedTasks.some((id) => {
    const task = tasks.find((t) => t.task_id === id);
    return task && task.status === "failed";
  });

  if (selectedTasks.length === 0) {
    return null;
  }

  return (
    <>
      <Paper
        sx={{
          p: 2,
          mb: 2,
          bgcolor: alpha(theme.palette.primary.main, 0.05),
          border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          flexWrap="wrap"
          gap={2}
        >
          {/* Selection info */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <Checkbox checked={selectedTasks.length === tasks.length} onChange={handleSelectAll} />
            <Box>
              <Typography variant="body1" sx={{ fontWeight: 600 }}>
                {selectedTasks.length} {selectedTasks.length === 1 ? "task" : "tasks"} selected
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
                {Object.entries(selectedTaskStatuses).map(([status, count]) => (
                  <Chip key={status} label={`${count} ${status}`} size="small" />
                ))}
              </Stack>
            </Box>
          </Box>

          {/* Actions */}
          <Stack direction="row" spacing={1}>
            <Button
              size="small"
              variant="outlined"
              startIcon={<Clear />}
              onClick={handleClearSelection}
            >
              Clear
            </Button>

            {canCancel && (
              <Button
                size="small"
                variant="outlined"
                color="warning"
                startIcon={<CancelIcon />}
                onClick={() => openConfirmDialog("cancel")}
              >
                Cancel Selected
              </Button>
            )}

            {canRetry && (
              <Button
                size="small"
                variant="outlined"
                color="info"
                startIcon={<Refresh />}
                onClick={() => openConfirmDialog("retry")}
              >
                Retry Selected
              </Button>
            )}

            {/* Uncomment when delete is implemented
            <Button
              size="small"
              variant="outlined"
              color="error"
              startIcon={<DeleteForever />}
              onClick={() => openConfirmDialog("delete")}
              disabled
            >
              Delete Selected
            </Button>
            */}
          </Stack>
        </Stack>
      </Paper>

      {/* Confirmation Dialog */}
      <Dialog open={confirmDialog.open} onClose={closeConfirmDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          Confirm Bulk {confirmDialog.operation?.charAt(0).toUpperCase()}
          {confirmDialog.operation?.slice(1)}
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            You are about to {confirmDialog.operation} {confirmDialog.count}{" "}
            {confirmDialog.count === 1 ? "task" : "tasks"}. This action cannot be undone.
          </Alert>

          <Typography variant="body2" color="text.secondary" paragraph>
            Selected tasks by status:
          </Typography>
          <Stack spacing={1}>
            {Object.entries(selectedTaskStatuses).map(([status, count]) => (
              <Box key={status} sx={{ display: "flex", justifyContent: "space-between" }}>
                <Typography variant="body2" sx={{ fontWeight: 600, textTransform: "capitalize" }}>
                  {status}:
                </Typography>
                <Typography variant="body2">{count}</Typography>
              </Box>
            ))}
          </Stack>

          {confirmDialog.operation === "cancel" && (
            <Alert severity="info" sx={{ mt: 2 }}>
              Cancelled tasks can be retried later if needed.
            </Alert>
          )}

          {confirmDialog.operation === "retry" && (
            <Alert severity="info" sx={{ mt: 2 }}>
              Failed tasks will be re-queued with their original parameters.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeConfirmDialog}>Cancel</Button>
          <Button
            onClick={executeBulkOperation}
            variant="contained"
            color={
              confirmDialog.operation === "delete"
                ? "error"
                : confirmDialog.operation === "cancel"
                  ? "warning"
                  : "primary"
            }
            startIcon={
              confirmDialog.operation === "cancel" ? (
                <CancelIcon />
              ) : confirmDialog.operation === "retry" ? (
                <Refresh />
              ) : (
                <DeleteForever />
              )
            }
          >
            {confirmDialog.operation?.charAt(0).toUpperCase()}
            {confirmDialog.operation?.slice(1)} {confirmDialog.count}{" "}
            {confirmDialog.count === 1 ? "Task" : "Tasks"}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

/**
 * Task Selection Checkbox Component
 * Used in TaskList to allow individual task selection
 */

interface TaskSelectionCheckboxProps {
  taskId: string;
  selected: boolean;
  onToggle: (taskId: string, selected: boolean) => void;
}

export function TaskSelectionCheckbox({ taskId, selected, onToggle }: TaskSelectionCheckboxProps) {
  return (
    <Checkbox
      checked={selected}
      onChange={(e) => onToggle(taskId, e.target.checked)}
      onClick={(e) => e.stopPropagation()} // Prevent row click
      size="small"
    />
  );
}
