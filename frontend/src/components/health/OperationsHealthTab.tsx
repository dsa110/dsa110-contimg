import React from "react";
import {
  Box,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  Stack,
  Chip,
  Typography,
  CardHeader,
} from "@mui/material";
import { useHealthSummary } from "../../api/queries";
import { DeadLetterQueueStats } from "../DeadLetterQueue";
import { CircuitBreakerStatus } from "../CircuitBreaker";
import { formatDateTime } from "../../utils/dateUtils";

export const OperationsHealthTab: React.FC = () => {
  const { data: healthSummary, isLoading } = useHealthSummary();

  if (isLoading || !healthSummary) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
        return "success";
      case "degraded":
        return "warning";
      case "unhealthy":
        return "error";
      default:
        return "default";
    }
  };

  return (
    <Grid container spacing={3}>
      {/* Overall Status */}
      <Grid size={12}>
        <Card>
          <CardContent>
            <Stack direction="row" spacing={2} alignItems="center">
              <Chip
                label={`Overall Status: ${healthSummary.status.toUpperCase()}`}
                color={getStatusColor(healthSummary.status) as any}
                size="large"
              />
              <Typography variant="body2" color="text.secondary">
                Last updated: {formatDateTime(healthSummary.timestamp * 1000)}
              </Typography>
            </Stack>
          </CardContent>
        </Card>
      </Grid>
      {/* Health Checks */}
      <Grid size={{ xs: 12, md: 6 }}>
        <Card>
          <CardHeader title="Health Checks" />
          <CardContent>
            <Stack spacing={2}>
              {Object.entries(healthSummary.checks).map(([name, check]) => (
                <Box key={name}>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Chip
                      label={check.healthy ? "Healthy" : "Unhealthy"}
                      color={check.healthy ? "success" : "error"}
                      size="small"
                    />
                    <Typography variant="body2">
                      <strong>{name.replace(/_/g, " ")}</strong>
                    </Typography>
                  </Stack>
                  {check.error && (
                    <Typography variant="caption" color="error" sx={{ ml: 5 }}>
                      {check.error}
                    </Typography>
                  )}
                </Box>
              ))}
            </Stack>
          </CardContent>
        </Card>
      </Grid>
      {/* DLQ Stats */}
      <Grid size={{ xs: 12, md: 6 }}>
        <DeadLetterQueueStats />
      </Grid>
      {/* Circuit Breakers */}
      <Grid size={12}>
        <CircuitBreakerStatus />
      </Grid>
    </Grid>
  );
};
