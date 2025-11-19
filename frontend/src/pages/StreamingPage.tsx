/**
 * Streaming Service Control Page
 * Full control panel for managing the streaming converter service
 */
import { useState } from "react";
import { Container, Typography, Box, Button, Alert, Stack } from "@mui/material";
import Grid from "@mui/material/Grid2";
import { PlayArrow, Stop, Refresh, Settings } from "@mui/icons-material";
import {
  useStreamingStatus,
  useStreamingHealth,
  useStreamingConfig,
  useStreamingMetrics,
  useStartStreaming,
  useStopStreaming,
  useRestartStreaming,
  useUpdateStreamingConfig,
  type StreamingConfig,
} from "../api/queries";
import { SkeletonLoader } from "../components/SkeletonLoader";
import { ConfirmationDialog } from "../components/ConfirmationDialog";
import { StreamingMetricsPanel } from "../components/metrics/StreamingMetricsPanel";
import { ServiceStatusCard } from "../components/streaming/ServiceStatusCard";
import { ResourceUsageCard } from "../components/streaming/ResourceUsageCard";
import { QueueStatsCard } from "../components/streaming/QueueStatsCard";
import { ConfigurationCard } from "../components/streaming/ConfigurationCard";
import { StreamingConfigDialog } from "../components/streaming/StreamingConfigDialog";

export default function StreamingPage() {
  const { data: status, isLoading: statusLoading } = useStreamingStatus();
  const { data: health } = useStreamingHealth();
  const { data: config, isLoading: configLoading } = useStreamingConfig();
  const { data: metrics } = useStreamingMetrics();

  const startMutation = useStartStreaming();
  const stopMutation = useStopStreaming();
  const restartMutation = useRestartStreaming();
  const updateConfigMutation = useUpdateStreamingConfig();

  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [stopDialogOpen, setStopDialogOpen] = useState(false);
  const [restartDialogOpen, setRestartDialogOpen] = useState(false);

  const handleStart = () => {
    startMutation.mutate(undefined, {
      onSuccess: (data) => {
        if (!data.success) {
          alert(`Failed to start: ${data.message}`);
        }
      },
    });
  };

  const handleStopClick = () => {
    setStopDialogOpen(true);
  };

  const handleStop = () => {
    stopMutation.mutate(undefined, {
      onSuccess: (data) => {
        if (!data.success) {
          alert(`Failed to stop: ${data.message}`);
        } else {
          setStopDialogOpen(false);
        }
      },
    });
  };

  const handleRestartClick = () => {
    setRestartDialogOpen(true);
  };

  const handleRestart = () => {
    restartMutation.mutate(undefined, {
      onSuccess: (data) => {
        if (!data.success) {
          alert(`Failed to restart: ${data.message}`);
        } else {
          setRestartDialogOpen(false);
        }
      },
    });
  };

  const handleSaveConfig = (editedConfig: StreamingConfig) => {
    updateConfigMutation.mutate(editedConfig, {
      onSuccess: (data) => {
        if (data.success) {
          setConfigDialogOpen(false);
        } else {
          alert(`Failed to update config: ${data.message}`);
        }
      },
    });
  };

  if (statusLoading || configLoading) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <SkeletonLoader variant="cards" rows={3} />
      </Container>
    );
  }

  const isRunning = status?.running ?? false;
  const isHealthy = health?.healthy ?? false;

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 4,
        }}
      >
        <Typography variant="h2" component="h2">
          Streaming Service Control
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<Settings />}
            onClick={() => setConfigDialogOpen(true)}
          >
            Configure
          </Button>
          {isRunning ? (
            <>
              <Button
                variant="outlined"
                color="warning"
                startIcon={<Refresh />}
                onClick={handleRestartClick}
                disabled={restartMutation.isPending}
              >
                Restart
              </Button>
              <Button
                variant="contained"
                color="error"
                startIcon={<Stop />}
                onClick={handleStopClick}
                disabled={stopMutation.isPending}
              >
                Stop
              </Button>
            </>
          ) : (
            <Button
              variant="contained"
              color="success"
              startIcon={<PlayArrow />}
              onClick={handleStart}
              disabled={startMutation.isPending}
            >
              Start
            </Button>
          )}
        </Stack>
      </Box>

      {/* Status Alert */}
      {status?.error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {status.error}
        </Alert>
      )}

      {startMutation.isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to start streaming service
        </Alert>
      )}

      {stopMutation.isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to stop streaming service
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Service Status Card */}
        <Grid item xs={12} md={6}>
          <ServiceStatusCard status={status} isRunning={isRunning} isHealthy={isHealthy} />
        </Grid>

        {/* Resource Usage Card */}
        <Grid item xs={12} md={6}>
          <ResourceUsageCard status={status} />
        </Grid>

        {/* Queue Statistics Card */}
        <Grid item xs={12} md={6}>
          <QueueStatsCard metrics={metrics} />
        </Grid>

        {/* Configuration Card */}
        <Grid item xs={12} md={6}>
          <ConfigurationCard config={config} />
        </Grid>

        {/* Grafana-style Streaming Metrics Panel */}
        <Grid item xs={12}>
          <StreamingMetricsPanel />
        </Grid>
      </Grid>

      {/* Stop Confirmation Dialog */}
      <ConfirmationDialog
        open={stopDialogOpen}
        onClose={() => setStopDialogOpen(false)}
        onConfirm={handleStop}
        title="Stop Streaming Service"
        message="Are you sure you want to stop the streaming service? This will halt all data ingestion."
        confirmText="Stop"
        severity="error"
        loading={stopMutation.isPending}
      />

      {/* Restart Confirmation Dialog */}
      <ConfirmationDialog
        open={restartDialogOpen}
        onClose={() => setRestartDialogOpen(false)}
        onConfirm={handleRestart}
        title="Restart Streaming Service"
        message="Are you sure you want to restart the streaming service? This will temporarily stop data ingestion."
        confirmText="Restart"
        severity="warning"
        loading={restartMutation.isPending}
      />

      {/* Configuration Dialog */}
      <StreamingConfigDialog
        open={configDialogOpen}
        onClose={() => setConfigDialogOpen(false)}
        config={config || null}
        onSave={handleSaveConfig}
        isSaving={updateConfigMutation.isPending}
      />
    </Container>
  );
}
