import React from "react";
import { Box, Typography, LinearProgress, Button, Alert, Stack } from "@mui/material";
import { formatDateTime } from "../../utils/dateUtils";
import type { CalibrationStatus } from "../../api/types";

interface CalibrationMonitorProps {
  status: CalibrationStatus | null;
  onStop: () => void;
  onComplete: () => void;
}

export const CalibrationMonitor: React.FC<CalibrationMonitorProps> = ({
  status,
  onStop,
  onComplete,
}) => {
  // Mock progress if status is null/undefined
  const progress = status?.progress || 0;
  const isRunning = status?.status === "running";
  const isCompleted = status?.status === "completed";
  const isFailed = status?.status === "failed";

  return (
    <Box sx={{ mt: 2 }}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Status: {status?.status || "Idle"}
          </Typography>
          {status?.started_at && (
            <Typography variant="caption" display="block" color="text.secondary">
              Started: {formatDateTime(status.started_at)}
            </Typography>
          )}
        </Box>

        <Box sx={{ width: "100%" }}>
          <LinearProgress
            variant="determinate"
            value={progress}
            color={isFailed ? "error" : "primary"}
          />
          <Typography variant="body2" color="text.secondary" align="right" sx={{ mt: 1 }}>
            {progress.toFixed(1)}%
          </Typography>
        </Box>

        {status?.current_stage && (
          <Typography variant="body2">Current Stage: {status.current_stage}</Typography>
        )}

        {status?.error && <Alert severity="error">{status.error}</Alert>}

        <Stack direction="row" spacing={2}>
          {isRunning && (
            <Button variant="outlined" color="error" onClick={onStop}>
              Stop Calibration
            </Button>
          )}
          {isCompleted && (
            <Button variant="contained" onClick={onComplete}>
              Review Results
            </Button>
          )}
        </Stack>
      </Stack>
    </Box>
  );
};
