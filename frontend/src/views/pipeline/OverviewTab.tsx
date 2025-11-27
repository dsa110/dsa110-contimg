/**
 * Pipeline Overview Tab
 *
 * Quick status dashboard showing:
 * - Workflow stage status (Ingest → Convert → Calibrate → Image → QA)
 * - Recent observations
 * - Queue summary
 * - System health at a glance
 */
import React from "react";
import { Alert, Stack } from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import { usePipelineStatus, useSystemMetrics, useHealthSummary } from "../../api/queries";
import { SkeletonLoader } from "../../components/SkeletonLoader";
import { WorkflowStatusPanel } from "../../components/dashboard/WorkflowStatusPanel";
import { PipelineStatusSection } from "../../components/dashboard/PipelineStatusSection";
import { RecentObservationsTable } from "../../components/dashboard/RecentObservationsTable";
import { SystemHealthSection } from "../../components/dashboard/SystemHealthSection";
import QueueDetailsPanel from "../../components/QueueDetailsPanel";
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

      {/* Queue & Pipeline Status */}
      <Grid container spacing={3}>
        <Grid item xs={12} lg={8}>
          <PipelineStatusSection status={status} isLoading={isLoading} />
        </Grid>
        <Grid item xs={12} lg={4}>
          <QueueDetailsPanel />
        </Grid>
      </Grid>

      {/* Recent Observations */}
      <RecentObservationsTable status={status} />

      {/* System Health Summary */}
      <Grid container spacing={3}>
        <Grid item xs={12} lg={8}>
          <SystemHealthSection
            metrics={metrics}
            isLoading={metricsLoading}
            healthSummary={healthSummary}
            healthLoading={healthLoading}
          />
        </Grid>
        <Grid item xs={12} lg={4}>
          <CircuitBreakerStatus />
        </Grid>
      </Grid>
    </Stack>
  );
}
