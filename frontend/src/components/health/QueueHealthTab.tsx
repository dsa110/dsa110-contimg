import React, { useMemo } from "react";
import {
  Alert,
  Box,
  Grid,
  Card,
  CardHeader,
  CardContent,
  Stack,
  Typography,
  LinearProgress,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Chip,
  CircularProgress,
} from "@mui/material";
import { usePipelineStatus } from "../../api/queries";

export const QueueHealthTab: React.FC = () => {
  const { data: status, isLoading: statusLoading } = usePipelineStatus();

  const queueDistribution = useMemo(() => {
    if (!status) return null;

    const states = [
      { name: "Completed", value: status.queue.completed, color: "#4caf50" },
      { name: "Pending", value: status.queue.pending, color: "#ff9800" },
      { name: "In Progress", value: status.queue.in_progress, color: "#2196f3" },
      { name: "Failed", value: status.queue.failed, color: "#f44336" },
      { name: "Collecting", value: status.queue.collecting, color: "#9e9e9e" },
    ].filter((s) => s.value > 0);

    return states;
  }, [status]);

  if (statusLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <>
      <Alert severity="info" sx={{ mb: 3 }}>
        Queue overview has moved to the Dashboard diagnostics section for faster access.
      </Alert>
      <Grid container spacing={3}>
        {/* State Distribution */}
        {queueDistribution && queueDistribution.length > 0 && (
          <Grid size={{ xs: 12, md: 6 }}>
            <Card>
              <CardHeader title="State Distribution" />
              <CardContent>
                <Stack spacing={2}>
                  {queueDistribution.map((state) => (
                    <Box key={state.name}>
                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          mb: 0.5,
                        }}
                      >
                        <Typography variant="body2">{state.name}</Typography>
                        <Typography variant="body2">
                          {state.value} (
                          {status?.queue.total
                            ? ((state.value / status.queue.total) * 100).toFixed(1)
                            : 0}
                          %)
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={status?.queue.total ? (state.value / status.queue.total) * 100 : 0}
                        sx={{
                          height: 8,
                          borderRadius: 4,
                          backgroundColor: "rgba(255, 255, 255, 0.1)",
                          "& .MuiLinearProgress-bar": {
                            backgroundColor: state.color,
                          },
                        }}
                      />
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Recent Groups */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardHeader title="Recent Groups" />
            <CardContent>
              {status?.recent_groups && status.recent_groups.length > 0 ? (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Group ID</TableCell>
                        <TableCell>State</TableCell>
                        <TableCell>Subbands</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {status.recent_groups.slice(0, 10).map((group) => (
                        <TableRow key={group.group_id}>
                          <TableCell>{group.group_id}</TableCell>
                          <TableCell>
                            <Chip
                              label={group.state}
                              size="small"
                              color={
                                group.state === "completed"
                                  ? "success"
                                  : group.state === "failed"
                                    ? "error"
                                    : group.state === "in_progress"
                                      ? "info"
                                      : "warning"
                              }
                            />
                          </TableCell>
                          <TableCell>
                            {group.subbands_present}/{group.expected_subbands}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No recent groups
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </>
  );
};
