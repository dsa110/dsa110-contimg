/**
 * Pipeline Overview Tab
 *
 * Quick status dashboard showing:
 * - Workflow stage status (Ingest → Convert → Calibrate → Image → QA)
 * - Recent observations
 * - System health at a glance
 */
import { useState } from "react";
import { Alert, Stack, Paper, Typography, Box, Chip } from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import { usePipelineStatus, useSystemMetrics, useHealthSummary } from "../../api/queries";
import { SkeletonLoader } from "../../components/SkeletonLoader";
import { WorkflowStatusPanel } from "../../components/dashboard/WorkflowStatusPanel";
import { RecentObservationsTable } from "../../components/dashboard/RecentObservationsTable";
import { SystemHealthSection } from "../../components/dashboard/SystemHealthSection";
import { CircuitBreakerStatus } from "../../components/CircuitBreaker";

export default function OverviewTab() {
  const { data: status, isLoading, error } = usePipelineStatus();
  const { data: metrics, isLoading: metricsLoading } = useSystemMetrics();
  const { data: healthSummary, isLoading: healthLoading } = useHealthSummary();

  if (isLoading) {
    return <SkeletonLoader variant="cards" rows={4} />;
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        Failed to load pipeline status: {error instanceof Error ? error.message : "Unknown error"}
      </Alert>
    );
  }

  return (
    <Stack spacing={3}>
      {/* Workflow Stages - Primary focus */}
      <WorkflowStatusPanel />

      {/* Queue Summary */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Queue Status
        </Typography>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <Chip
            label={`Total: ${String(status?.queue?.total ?? 0)}`}
            color="default"
            variant="outlined"
          />
          <Chip
            label={`Collecting: ${String(status?.queue?.collecting ?? 0)}`}
            color="secondary"
            variant="outlined"
          />
          <Chip
            label={`Pending: ${String(status?.queue?.pending ?? 0)}`}
            color="warning"
            variant="outlined"
          />
          <Chip
            label={`In Progress: ${String(status?.queue?.in_progress ?? 0)}`}
            color="info"
            variant="outlined"
          />
          <Chip
            label={`Completed: ${String(status?.queue?.completed ?? 0)}`}
            color="success"
            variant="outlined"
          />
          <Chip
            label={`Failed: ${String(status?.queue?.failed ?? 0)}`}
            color="error"
            variant="outlined"
          />
        </Box>
      </Paper>

      {/* Recent Observations */}
      <RecentObservationsTable status={status} />

      {/* System Health Summary */}
      <Grid container spacing={3}>
        <Grid item xs={12} lg={8}>
          <SystemHealthSection
            metrics={metrics}
            loading={metricsLoading || healthLoading}
            healthSummary={healthSummary}
          />
        </Grid>
        <Grid item xs={12} lg={4}>
          <CircuitBreakerStatus />
        </Grid>
      </Grid>
    </Stack>
  );
}
