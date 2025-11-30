/**
 * WorkflowStatusPanel - Unified workflow status visualization
 *
 * Displays the complete streaming pipeline flow with queue depths,
 * bottleneck highlighting, and real-time status updates.
 *
 * Issue #53: Add Unified Workflow Status Visualization to Dashboard
 */
import React from "react";
import {
  Box,
  Paper,
  Typography,
  Stack,
  Chip,
  Tooltip,
  Skeleton,
  Alert,
  IconButton,
  useTheme,
} from "@mui/material";
import {
  ArrowForward as ArrowIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Schedule as ScheduleIcon,
} from "@mui/icons-material";
import { useWorkflowStatus } from "../../api/queries";
import type { WorkflowStageStatus } from "../../api/types";

interface StageCardProps {
  stage: WorkflowStageStatus;
  isBottleneck: boolean;
  onClick?: () => void;
}

/**
 * Individual stage card showing queue depth and status
 */
function StageCard({ stage, isBottleneck, onClick }: StageCardProps) {
  const theme = useTheme();

  // Determine color based on status
  const getStatusColor = () => {
    if (stage.failed_today > 0) return theme.palette.error.main;
    if (isBottleneck) return theme.palette.warning.main;
    if (stage.pending > 10) return theme.palette.warning.light;
    if (stage.processing > 0) return theme.palette.info.main;
    return theme.palette.success.main;
  };

  const statusColor = getStatusColor();
  const hasActivity = stage.pending > 0 || stage.processing > 0;

  return (
    <Tooltip
      title={
        <Box>
          <Typography variant="body2" fontWeight="bold">
            {stage.display_name}
          </Typography>
          <Typography variant="caption" display="block">
            Pending: {stage.pending}
          </Typography>
          <Typography variant="caption" display="block">
            Processing: {stage.processing}
          </Typography>
          <Typography variant="caption" display="block">
            Completed today: {stage.completed_today}
          </Typography>
          {stage.failed_today > 0 && (
            <Typography variant="caption" display="block" color="error">
              Failed today: {stage.failed_today}
            </Typography>
          )}
          {isBottleneck && (
            <Typography variant="caption" display="block" color="warning.main">
              :warning: Bottleneck detected
            </Typography>
          )}
        </Box>
      }
      arrow
    >
      <Paper
        elevation={isBottleneck ? 4 : 1}
        onClick={onClick}
        sx={{
          p: 1.5,
          minWidth: 100,
          textAlign: "center",
          cursor: onClick ? "pointer" : "default",
          borderLeft: `4px solid ${statusColor}`,
          bgcolor: isBottleneck ? "warning.50" : "background.paper",
          transition: "all 0.2s ease",
          "&:hover": onClick
            ? {
                transform: "translateY(-2px)",
                boxShadow: 3,
              }
            : {},
        }}
      >
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: 0.5 }}
        >
          {stage.display_name}
        </Typography>

        <Stack direction="row" spacing={0.5} justifyContent="center" alignItems="center" sx={{ mt: 0.5 }}>
          {stage.pending > 0 && (
            <Chip
              label={stage.pending}
              size="small"
              color="warning"
              sx={{ height: 20, fontSize: "0.7rem" }}
            />
          )}
          {stage.processing > 0 && (
            <Chip
              label={stage.processing}
              size="small"
              color="info"
              sx={{ height: 20, fontSize: "0.7rem" }}
            />
          )}
          {!hasActivity && stage.completed_today > 0 && (
            <Chip
              label={`:check_mark:${stage.completed_today}`}
              size="small"
              color="success"
              variant="outlined"
              sx={{ height: 20, fontSize: "0.7rem" }}
            />
          )}
          {!hasActivity && stage.completed_today === 0 && (
            <Typography variant="caption" color="text.disabled">
              —
            </Typography>
          )}
        </Stack>

        {isBottleneck && (
          <WarningIcon
            sx={{ fontSize: 14, color: "warning.main", mt: 0.5 }}
          />
        )}
      </Paper>
    </Tooltip>
  );
}

/**
 * Arrow connector between stages
 */
function StageConnector() {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        px: 0.5,
        color: "text.disabled",
      }}
    >
      <ArrowIcon sx={{ fontSize: 16 }} />
    </Box>
  );
}

/**
 * Health indicator badge
 */
function HealthBadge({ health }: { health: "healthy" | "degraded" | "stalled" }) {
  const config = {
    healthy: { icon: <CheckIcon />, color: "success" as const, label: "Healthy" },
    degraded: { icon: <WarningIcon />, color: "warning" as const, label: "Degraded" },
    stalled: { icon: <ErrorIcon />, color: "error" as const, label: "Stalled" },
  };

  const { icon, color, label } = config[health];

  return (
    <Chip
      icon={icon}
      label={label}
      color={color}
      size="small"
      variant="outlined"
    />
  );
}

/**
 * Main WorkflowStatusPanel component
 */
export function WorkflowStatusPanel() {
  const { data, isLoading, error, refetch, isFetching } = useWorkflowStatus();
  const theme = useTheme();

  if (isLoading) {
    return (
      <Paper sx={{ p: 2 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <Skeleton variant="text" width={200} />
        </Stack>
        <Stack direction="row" spacing={1} alignItems="center" justifyContent="center">
          {[1, 2, 3, 4, 5, 6, 7].map((i) => (
            <React.Fragment key={i}>
              <Skeleton variant="rounded" width={100} height={60} />
              {i < 7 && <Skeleton variant="circular" width={16} height={16} />}
            </React.Fragment>
          ))}
        </Stack>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 2 }}>
        <Alert severity="error">
          Failed to load workflow status. The API may be unavailable.
        </Alert>
      </Paper>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <Paper sx={{ p: 2 }}>
      {/* Header */}
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 2 }}
      >
        <Stack direction="row" spacing={2} alignItems="center">
          <Typography variant="h6" component="h2">
            Pipeline Workflow Status
          </Typography>
          <HealthBadge health={data.overall_health} />
        </Stack>

        <Stack direction="row" spacing={1} alignItems="center">
          {data.estimated_completion && (
            <Tooltip title="Estimated completion time for pending items">
              <Chip
                icon={<ScheduleIcon />}
                label={new Date(data.estimated_completion).toLocaleTimeString()}
                size="small"
                variant="outlined"
              />
            </Tooltip>
          )}
          <Tooltip title="Refresh status">
            <IconButton size="small" onClick={() => refetch()} disabled={isFetching}>
              <RefreshIcon sx={{ fontSize: 18, animation: isFetching ? "spin 1s linear infinite" : "none" }} />
            </IconButton>
          </Tooltip>
        </Stack>
      </Stack>

      {/* Legend */}
      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <Stack direction="row" spacing={0.5} alignItems="center">
          <Chip label="3" size="small" color="warning" sx={{ height: 18, fontSize: "0.65rem" }} />
          <Typography variant="caption" color="text.secondary">
            Pending
          </Typography>
        </Stack>
        <Stack direction="row" spacing={0.5} alignItems="center">
          <Chip label="1" size="small" color="info" sx={{ height: 18, fontSize: "0.65rem" }} />
          <Typography variant="caption" color="text.secondary">
            Processing
          </Typography>
        </Stack>
        <Stack direction="row" spacing={0.5} alignItems="center">
          <Chip label=":check_mark:12" size="small" color="success" variant="outlined" sx={{ height: 18, fontSize: "0.65rem" }} />
          <Typography variant="caption" color="text.secondary">
            Completed today
          </Typography>
        </Stack>
      </Stack>

      {/* Pipeline Flow */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexWrap: "wrap",
          gap: 0.5,
          py: 1,
          overflowX: "auto",
        }}
      >
        {data.stages.map((stage, index) => (
          <React.Fragment key={stage.name}>
            <StageCard
              stage={stage}
              isBottleneck={stage.name === data.bottleneck}
            />
            {index < data.stages.length - 1 && <StageConnector />}
          </React.Fragment>
        ))}
      </Box>

      {/* Summary Stats */}
      <Stack
        direction="row"
        spacing={3}
        justifyContent="center"
        sx={{
          mt: 2,
          pt: 2,
          borderTop: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Typography variant="body2" color="text.secondary">
          Total Pending:{" "}
          <Typography component="span" fontWeight="bold" color="warning.main">
            {data.total_pending}
          </Typography>
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Completed Today:{" "}
          <Typography component="span" fontWeight="bold" color="success.main">
            {data.total_completed_today}
          </Typography>
        </Typography>
        {data.total_failed_today > 0 && (
          <Typography variant="body2" color="text.secondary">
            Failed Today:{" "}
            <Typography component="span" fontWeight="bold" color="error.main">
              {data.total_failed_today}
            </Typography>
          </Typography>
        )}
      </Stack>

      {/* Bottleneck Alert */}
      {data.bottleneck && data.overall_health !== "healthy" && (
        <Alert
          severity="warning"
          sx={{ mt: 2 }}
          icon={<WarningIcon />}
        >
          <Typography variant="body2">
            <strong>Bottleneck detected:</strong> The{" "}
            <em>{data.stages.find((s) => s.name === data.bottleneck)?.display_name || data.bottleneck}</em>{" "}
            stage has a high pending-to-completed ratio. Consider investigating or scaling resources.
          </Typography>
        </Alert>
      )}

      {/* CSS for spinner animation */}
      <style>
        {`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}
      </style>
    </Paper>
  );
}

export default WorkflowStatusPanel;
