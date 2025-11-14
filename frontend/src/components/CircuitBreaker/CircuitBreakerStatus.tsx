/**
 * Circuit Breaker Status Component
 */
import { useState } from "react";
import {
  Card,
  CardContent,
  Typography,
  Box,
  Stack,
  Chip,
  IconButton,
  Tooltip,
  Grid,
} from "@mui/material";
import {
  Refresh as RefreshIcon,
  PowerSettingsNew as ResetIcon,
  CheckCircle as ClosedIcon,
  Cancel as OpenIcon,
  HourglassEmpty as HalfOpenIcon,
} from "@mui/icons-material";
import { useCircuitBreakers, useResetCircuitBreaker } from "../../api/queries";
import { SkeletonLoader } from "../SkeletonLoader";
import ConfirmationDialog from "../ConfirmationDialog";

export function CircuitBreakerStatus() {
  const { data, isLoading, refetch } = useCircuitBreakers();
  const resetMutation = useResetCircuitBreaker();
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [selectedBreaker, setSelectedBreaker] = useState<string | null>(null);

  const handleReset = async () => {
    if (!selectedBreaker) return;
    try {
      await resetMutation.mutateAsync(selectedBreaker);
      setResetDialogOpen(false);
      setSelectedBreaker(null);
      refetch();
    } catch (error) {
      console.error("Failed to reset circuit breaker:", error);
    }
  };

  const getStateIcon = (state: string) => {
    switch (state) {
      case "closed":
        return <ClosedIcon color="success" />;
      case "open":
        return <OpenIcon color="error" />;
      case "half_open":
        return <HalfOpenIcon color="warning" />;
      default:
        return null;
    }
  };

  const getStateColor = (state: string): "success" | "error" | "warning" | "default" => {
    switch (state) {
      case "closed":
        return "success";
      case "open":
        return "error";
      case "half_open":
        return "warning";
      default:
        return "default";
    }
  };

  const getStateLabel = (state: string) => {
    switch (state) {
      case "closed":
        return "CLOSED";
      case "open":
        return "OPEN";
      case "half_open":
        return "HALF-OPEN";
      default:
        return state.toUpperCase();
    }
  };

  if (isLoading || !data) {
    return <SkeletonLoader variant="cards" rows={3} />;
  }

  return (
    <>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h6">Circuit Breaker Status</Typography>
        <Tooltip title="Refresh">
          <IconButton size="small" onClick={() => refetch()}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Stack>

      <Grid container spacing={2}>
        {data.circuit_breakers.map((breaker) => (
          <Grid xs={12} md={6} lg={4} key={breaker.name}>
            <Card>
              <CardContent>
                <Stack spacing={2}>
                  <Stack direction="row" spacing={2} alignItems="center">
                    {getStateIcon(breaker.state)}
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="h6">
                        {breaker.name.replace("_", " ").toUpperCase()}
                      </Typography>
                      <Chip
                        label={getStateLabel(breaker.state)}
                        color={getStateColor(breaker.state)}
                        size="small"
                        sx={{ mt: 0.5 }}
                      />
                    </Box>
                    {breaker.state === "open" && (
                      <Tooltip title="Reset Circuit Breaker">
                        <IconButton
                          size="small"
                          onClick={() => {
                            setSelectedBreaker(breaker.name);
                            setResetDialogOpen(true);
                          }}
                        >
                          <ResetIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Stack>

                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Failure Count: <strong>{breaker.failure_count}</strong>
                    </Typography>
                    {breaker.last_failure_time && (
                      <Typography variant="body2" color="text.secondary">
                        Last Failure: {new Date(breaker.last_failure_time * 1000).toLocaleString()}
                      </Typography>
                    )}
                    <Typography variant="body2" color="text.secondary">
                      Recovery Timeout: <strong>{breaker.recovery_timeout}s</strong>
                    </Typography>
                  </Box>

                  {breaker.state === "open" && (
                    <Alert severity="error">
                      Circuit breaker is OPEN. Requests are being rejected.
                    </Alert>
                  )}
                  {breaker.state === "half_open" && (
                    <Alert severity="warning">
                      Circuit breaker is HALF-OPEN. Testing if service has recovered.
                    </Alert>
                  )}
                  {breaker.state === "closed" && (
                    <Alert severity="success">Circuit breaker is CLOSED. Normal operation.</Alert>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <ConfirmationDialog
        open={resetDialogOpen}
        title="Reset Circuit Breaker"
        message={`Are you sure you want to reset the circuit breaker for ${selectedBreaker}? This will close the circuit and allow requests to flow through again.`}
        confirmText="Reset"
        severity="warning"
        onConfirm={handleReset}
        onCancel={() => setResetDialogOpen(false)}
        loading={resetMutation.isPending}
      />
    </>
  );
}
