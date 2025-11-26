/**
 * Alert Panel component for displaying Absurd health alerts and warnings.
 *
 * Shows system alerts, degraded health warnings, and failed task notifications.
 */

import React from "react";
import {
  Box,
  Paper,
  Typography,
  Alert,
  AlertTitle,
  Collapse,
  IconButton,
  Stack,
  Chip,
  CircularProgress,
} from "@mui/material";
import {
  Error as ErrorIcon,
  Warning as WarningIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Refresh as RefreshIcon,
} from "@mui/icons-material";
import { useDetailedHealth } from "../../api/absurdQueries";

interface AlertPanelProps {
  /** Whether to show in collapsed mode initially */
  defaultCollapsed?: boolean;
  /** Maximum alerts to show before "show more" */
  maxVisible?: number;
}

export const AlertPanel: React.FC<AlertPanelProps> = ({
  defaultCollapsed = false,
  maxVisible = 5,
}) => {
  const { data: health, isLoading, error, refetch } = useDetailedHealth();
  const [expanded, setExpanded] = React.useState(!defaultCollapsed);
  const [showAll, setShowAll] = React.useState(false);

  // Combine alerts and warnings
  const allAlerts = React.useMemo(() => {
    if (!health) return [];
    return [
      ...health.alerts.map((a) => ({ ...a, severity: "error" as const })),
      ...health.warnings.map((w) => ({ ...w, severity: "warning" as const })),
    ];
  }, [health]);

  const visibleAlerts = showAll ? allAlerts : allAlerts.slice(0, maxVisible);
  const hasMore = allAlerts.length > maxVisible;

  // Don't show panel if no alerts and healthy
  if (!isLoading && !error && allAlerts.length === 0 && health?.status === "healthy") {
    return null;
  }

  return (
    <Paper
      elevation={2}
      sx={{
        mb: 2,
        border: health?.status === "critical" ? "2px solid" : "1px solid",
        borderColor:
          health?.status === "critical"
            ? "error.main"
            : health?.status === "degraded"
              ? "warning.main"
              : "divider",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          p: 1.5,
          bgcolor:
            health?.status === "critical"
              ? "error.dark"
              : health?.status === "degraded"
                ? "warning.dark"
                : "grey.800",
          color: "white",
          cursor: "pointer",
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {health?.status === "critical" ? (
            <ErrorIcon color="inherit" />
          ) : health?.status === "degraded" ? (
            <WarningIcon color="inherit" />
          ) : null}
          <Typography variant="subtitle1" fontWeight="bold">
            System Status: {health?.status || "Unknown"}
          </Typography>
          {allAlerts.length > 0 && (
            <Chip
              size="small"
              label={`${allAlerts.length} ${allAlerts.length === 1 ? "alert" : "alerts"}`}
              color={health?.status === "critical" ? "error" : "warning"}
              sx={{ ml: 1 }}
            />
          )}
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <IconButton
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              refetch();
            }}
            sx={{ color: "white" }}
          >
            {isLoading ? <CircularProgress size={20} color="inherit" /> : <RefreshIcon />}
          </IconButton>
          {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </Box>
      </Box>

      {/* Content */}
      <Collapse in={expanded}>
        <Box sx={{ p: 2 }}>
          {/* Status message */}
          {health?.message && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {health.message}
            </Typography>
          )}

          {/* Status indicators */}
          <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
            <Chip
              label={`Database: ${health?.database_available ? "Available" : "Unavailable"}`}
              color={health?.database_available ? "success" : "error"}
              size="small"
            />
            <Chip
              label={`Workers: ${health?.worker_pool_healthy ? "Healthy" : "Unhealthy"}`}
              color={health?.worker_pool_healthy ? "success" : "warning"}
              size="small"
            />
            <Chip label={`Queue Depth: ${health?.queue_depth || 0}`} color="default" size="small" />
          </Stack>

          {/* Alerts list */}
          {visibleAlerts.length > 0 && (
            <Stack spacing={1}>
              {visibleAlerts.map((alert, index) => (
                <Alert
                  key={index}
                  severity={alert.severity}
                  sx={{ "& .MuiAlert-message": { width: "100%" } }}
                >
                  <AlertTitle sx={{ fontSize: "0.875rem" }}>
                    {alert.level === "alert" ? "Alert" : "Warning"}
                    {alert.timestamp && (
                      <Typography
                        component="span"
                        variant="caption"
                        sx={{ ml: 1, color: "text.secondary" }}
                      >
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </Typography>
                    )}
                  </AlertTitle>
                  <Typography variant="body2">{alert.message}</Typography>
                </Alert>
              ))}

              {hasMore && (
                <Box sx={{ display: "flex", justifyContent: "center" }}>
                  <Chip
                    label={showAll ? "Show Less" : `Show ${allAlerts.length - maxVisible} More`}
                    onClick={() => setShowAll(!showAll)}
                    variant="outlined"
                    size="small"
                    sx={{ cursor: "pointer" }}
                  />
                </Box>
              )}
            </Stack>
          )}

          {/* Error state */}
          {error && (
            <Alert severity="error">
              <AlertTitle>Failed to load health status</AlertTitle>
              {error instanceof Error ? error.message : "Unknown error"}
            </Alert>
          )}

          {/* Loading state with no data */}
          {isLoading && !health && (
            <Box sx={{ display: "flex", justifyContent: "center", p: 2 }}>
              <CircularProgress size={24} />
            </Box>
          )}
        </Box>
      </Collapse>
    </Paper>
  );
};

export default AlertPanel;
