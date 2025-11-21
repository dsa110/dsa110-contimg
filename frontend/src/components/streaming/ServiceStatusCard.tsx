import React from "react";
import { Card, CardContent, Typography, Stack, Box, Chip } from "@mui/material";
import { CheckCircle, Error as ErrorIcon } from "@mui/icons-material";
import type { StreamingStatus } from "../../api/queries";
import { formatDateTime } from "../../utils/dateUtils";

interface ServiceStatusCardProps {
  status?: StreamingStatus;
  isRunning: boolean;
  isHealthy: boolean;
}

function formatUptime(seconds?: number): string {
  if (!seconds) return "N/A";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`;
  }
  if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  }
  return `${secs}s`;
}

export const ServiceStatusCard: React.FC<ServiceStatusCardProps> = ({
  status,
  isRunning,
  isHealthy,
}) => {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Service Status
        </Typography>
        <Stack spacing={2} sx={{ mt: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip
              icon={isRunning ? <CheckCircle /> : <ErrorIcon />}
              label={isRunning ? "Running" : "Stopped"}
              color={isRunning ? "success" : "default"}
              size="small"
            />
            {isHealthy && <Chip label="Healthy" color="success" size="small" variant="outlined" />}
          </Box>

          {status?.pid && (
            <Typography variant="body2" color="text.secondary">
              <strong>PID:</strong> {status.pid}
            </Typography>
          )}

          {status?.started_at && (
            <Typography variant="body2" color="text.secondary">
              <strong>Started:</strong> {formatDateTime(status.started_at)}
            </Typography>
          )}

          {status?.uptime_seconds && (
            <Typography variant="body2" color="text.secondary">
              <strong>Uptime:</strong> {formatUptime(status.uptime_seconds)}
            </Typography>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};
