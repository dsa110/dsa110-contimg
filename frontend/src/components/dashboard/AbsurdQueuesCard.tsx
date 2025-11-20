/**
 * Absurd Queues Card for Dashboard
 * Displays real-time queue statistics with health indicator
 */
import React from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  Stack,
  Chip,
  Button,
  CircularProgress,
  Alert,
} from "@mui/material";
import { AccountTree, CheckCircle, Warning, Error as ErrorIcon } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { useQueueStats, useAbsurdHealth } from "../../api/absurdQueries";

interface StatItemProps {
  label: string;
  value: number;
  color: string;
}

function StatItem({ label, value, color }: StatItemProps) {
  return (
    <Box sx={{ textAlign: "center" }}>
      <Typography variant="h4" sx={{ fontWeight: 700, color }}>
        {value}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
    </Box>
  );
}

export function AbsurdQueuesCard() {
  const navigate = useNavigate();
  const { data: queueStats, isLoading: statsLoading, error: statsError } = useQueueStats("default");
  const { data: health, isLoading: healthLoading } = useAbsurdHealth();

  // Determine health status and color
  const getHealthColor = () => {
    if (!health || !queueStats) return "default";

    const failureRate = queueStats.failed / (queueStats.completed + queueStats.failed || 1);
    const activeLoad = queueStats.active + queueStats.pending;

    // Red: system unhealthy or high failure rate (>20%)
    if (health.status !== "healthy" || failureRate > 0.2) return "error";

    // Yellow: high load (>50 tasks) or moderate failures (>10%)
    if (activeLoad > 50 || failureRate > 0.1) return "warning";

    // Green: healthy
    return "success";
  };

  const getHealthIcon = () => {
    const color = getHealthColor();
    if (color === "error") return <ErrorIcon fontSize="small" />;
    if (color === "warning") return <Warning fontSize="small" />;
    return <CheckCircle fontSize="small" />;
  };

  if (healthLoading || statsLoading) {
    return (
      <Card variant="outlined" sx={{ height: "100%" }}>
        <CardContent>
          <Box
            sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: 200 }}
          >
            <CircularProgress size={40} />
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (statsError) {
    return (
      <Card variant="outlined" sx={{ height: "100%" }}>
        <CardContent>
          <Stack spacing={2}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <AccountTree color="action" />
              <Typography variant="h6">Absurd Queues</Typography>
            </Box>
            <Alert severity="info" sx={{ mt: 2 }}>
              Absurd workflow manager is not available
            </Alert>
          </Stack>
        </CardContent>
      </Card>
    );
  }

  const healthColor = getHealthColor();

  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Stack spacing={2}>
          {/* Header with health indicator */}
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <AccountTree color="primary" />
              <Typography variant="h6">Absurd Queues</Typography>
            </Box>
            <Chip
              icon={getHealthIcon()}
              label={health?.status || "unknown"}
              color={healthColor}
              size="small"
              sx={{ textTransform: "capitalize" }}
            />
          </Box>

          {/* Queue statistics */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 2,
              py: 2,
            }}
          >
            <StatItem label="Active" value={queueStats?.active || 0} color="primary.main" />
            <StatItem label="Pending" value={queueStats?.pending || 0} color="warning.main" />
            <StatItem label="Failed" value={queueStats?.failed || 0} color="error.main" />
          </Box>

          {/* Summary text */}
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center" }}>
            {queueStats?.completed || 0} completed tasks
          </Typography>

          {/* Action button */}
          <Button
            variant="contained"
            fullWidth
            startIcon={<AccountTree />}
            onClick={() => navigate("/absurd")}
          >
            Open Absurd
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}
