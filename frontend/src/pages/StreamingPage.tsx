/**
 * Streaming Service Control Page
 * Full control panel for managing the streaming converter service
 */
import { useState } from "react";
import {
  Container,
  Typography,
  Box,
  Button,
  Alert,
  Grid,
  Card,
  CardContent,
  Chip,
  Stack,
  TextField,
  Switch,
  FormControlLabel,
  Divider,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import {
  PlayArrow,
  Stop,
  Refresh,
  Settings,
  CheckCircle,
  Error as ErrorIcon,
  Memory,
  Speed,
  Schedule,
} from "@mui/icons-material";
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
  const [editedConfig, setEditedConfig] = useState<StreamingConfig | null>(null);

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

  const handleOpenConfig = () => {
    if (config) {
      setEditedConfig({ ...config });
      setConfigDialogOpen(true);
    }
  };

  const handleSaveConfig = () => {
    if (editedConfig) {
      updateConfigMutation.mutate(editedConfig, {
        onSuccess: (data) => {
          if (data.success) {
            setConfigDialogOpen(false);
          } else {
            alert(`Failed to update config: ${data.message}`);
          }
        },
      });
    }
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
          <Button variant="outlined" startIcon={<Settings />} onClick={handleOpenConfig}>
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
        <Grid xs={12} md={6}>
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
                  {isHealthy && (
                    <Chip label="Healthy" color="success" size="small" variant="outlined" />
                  )}
                </Box>

                {status?.pid && (
                  <Typography variant="body2" color="text.secondary">
                    <strong>PID:</strong> {status.pid}
                  </Typography>
                )}

                {status?.started_at && (
                  <Typography variant="body2" color="text.secondary">
                    <strong>Started:</strong> {new Date(status.started_at).toLocaleString()}
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
        </Grid>

        {/* Resource Usage Card */}
        <Grid xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Resource Usage
              </Typography>
              <Stack spacing={2} sx={{ mt: 2 }}>
                {status?.cpu_percent != null && (
                  <Box>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        mb: 0.5,
                      }}
                    >
                      <Typography variant="body2" color="text.secondary">
                        <Speed
                          sx={{
                            fontSize: 16,
                            verticalAlign: "middle",
                            mr: 0.5,
                          }}
                        />
                        CPU
                      </Typography>
                      <Typography variant="body2">{status.cpu_percent.toFixed(1)}%</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={status.cpu_percent}
                      color={
                        status.cpu_percent > 80
                          ? "error"
                          : status.cpu_percent > 50
                            ? "warning"
                            : "primary"
                      }
                    />
                  </Box>
                )}

                {status?.memory_mb != null && (
                  <Box>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        mb: 0.5,
                      }}
                    >
                      <Typography variant="body2" color="text.secondary">
                        <Memory
                          sx={{
                            fontSize: 16,
                            verticalAlign: "middle",
                            mr: 0.5,
                          }}
                        />
                        Memory
                      </Typography>
                      <Typography variant="body2">{status.memory_mb.toFixed(0)} MB</Typography>
                    </Box>
                  </Box>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Queue Statistics Card */}
        <Grid xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Queue Statistics
              </Typography>
              {metrics?.queue_stats ? (
                <Stack spacing={1} sx={{ mt: 2 }}>
                  {Object.entries(metrics.queue_stats).map(([state, count]) => (
                    <Box key={state} sx={{ display: "flex", justifyContent: "space-between" }}>
                      <Typography variant="body2" color="text.secondary">
                        {state}
                      </Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {count}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No queue data available
                </Typography>
              )}

              {metrics?.processing_rate_per_hour !== undefined && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="body2" color="text.secondary">
                    <Schedule sx={{ fontSize: 16, verticalAlign: "middle", mr: 0.5 }} />
                    Processing Rate: {metrics.processing_rate_per_hour} groups/hour
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Configuration Card */}
        <Grid xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Current Configuration
              </Typography>
              {config ? (
                <Stack spacing={1} sx={{ mt: 2 }}>
                  <Typography variant="body2">
                    <strong>Input Directory:</strong> {config.input_dir}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Output Directory:</strong> {config.output_dir}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Expected Subbands:</strong> {config.expected_subbands}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Chunk Duration:</strong> {config.chunk_duration} minutes
                  </Typography>
                  <Typography variant="body2">
                    <strong>Max Workers:</strong> {config.max_workers}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Log Level:</strong> {config.log_level}
                  </Typography>
                </Stack>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No configuration loaded
                </Typography>
              )}
            </CardContent>
          </Card>
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
      <Dialog
        open={configDialogOpen}
        onClose={() => setConfigDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Streaming Service Configuration</DialogTitle>
        <DialogContent>
          {editedConfig && (
            <Stack spacing={3} sx={{ mt: 1 }}>
              <TextField
                label="Input Directory"
                value={editedConfig.input_dir}
                onChange={(e) =>
                  setEditedConfig({
                    ...editedConfig,
                    input_dir: e.target.value,
                  })
                }
                fullWidth
                required
              />
              <TextField
                label="Output Directory"
                value={editedConfig.output_dir}
                onChange={(e) =>
                  setEditedConfig({
                    ...editedConfig,
                    output_dir: e.target.value,
                  })
                }
                fullWidth
                required
              />
              <TextField
                label="Scratch Directory"
                value={editedConfig.scratch_dir || ""}
                onChange={(e) =>
                  setEditedConfig({
                    ...editedConfig,
                    scratch_dir: e.target.value,
                  })
                }
                fullWidth
              />
              <Grid container spacing={2}>
                <Grid xs={6}>
                  <TextField
                    label="Expected Subbands"
                    type="number"
                    value={editedConfig.expected_subbands}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        expected_subbands: parseInt(e.target.value) || 16,
                      })
                    }
                    fullWidth
                  />
                </Grid>
                <Grid xs={6}>
                  <TextField
                    label="Chunk Duration (minutes)"
                    type="number"
                    value={editedConfig.chunk_duration}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        chunk_duration: parseFloat(e.target.value) || 5.0,
                      })
                    }
                    fullWidth
                  />
                </Grid>
                <Grid xs={6}>
                  <TextField
                    label="Max Workers"
                    type="number"
                    value={editedConfig.max_workers}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        max_workers: parseInt(e.target.value) || 4,
                      })
                    }
                    fullWidth
                  />
                </Grid>
                <Grid xs={6}>
                  <TextField
                    label="Log Level"
                    select
                    value={editedConfig.log_level}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        log_level: e.target.value,
                      })
                    }
                    fullWidth
                    SelectProps={{ native: true }}
                  >
                    <option value="DEBUG">DEBUG</option>
                    <option value="INFO">INFO</option>
                    <option value="WARNING">WARNING</option>
                    <option value="ERROR">ERROR</option>
                  </TextField>
                </Grid>
              </Grid>
              <FormControlLabel
                control={
                  <Switch
                    checked={editedConfig.use_subprocess}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        use_subprocess: e.target.checked,
                      })
                    }
                  />
                }
                label="Use Subprocess"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={editedConfig.monitoring}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        monitoring: e.target.checked,
                      })
                    }
                  />
                }
                label="Enable Monitoring"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={editedConfig.stage_to_tmpfs}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        stage_to_tmpfs: e.target.checked,
                      })
                    }
                  />
                }
                label="Stage to TMPFS"
              />
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfigDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleSaveConfig}
            variant="contained"
            disabled={updateConfigMutation.isPending}
          >
            {updateConfigMutation.isPending ? "Saving..." : "Save & Apply"}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
