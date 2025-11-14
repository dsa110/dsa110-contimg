// import React from "react";
import {
  Box,
  Card,
  CardContent,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Chip,
  Paper,
} from "@mui/material";
import { PlayArrow } from "@mui/icons-material";
// import { alpha } from "@mui/material/styles";
import { formatDistanceToNow } from "date-fns";
import { useActivePipelineExecutions } from "../../api/queries";
import ExecutionDetails from "./ExecutionDetails";
import { SkeletonLoader } from "../SkeletonLoader";
import { EmptyState } from "../EmptyState";

export default function ActiveExecutions() {
  const { data: executions, isLoading, error } = useActivePipelineExecutions();

  if (isLoading) {
    return <SkeletonLoader variant="cards" rows={2} />;
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="error">Error loading active executions: {error.message}</Typography>
      </Box>
    );
  }

  if (!executions || executions.length === 0) {
    return (
      <EmptyState
        icon={<PlayArrow sx={{ fontSize: 64, color: "text.secondary" }} />}
        title="No active executions"
        description="There are no active pipeline executions. Start a new workflow from the Control page to begin processing."
      />
    );
  }

  return (
    <Box>
      {executions.map((execution) => (
        <Card key={execution.id} sx={{ mb: 2 }}>
          <CardContent>
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                mb: 2,
              }}
            >
              <Box>
                <Typography variant="h6">Execution #{execution.id}</Typography>
                <Typography variant="body2" color="text.secondary">
                  Type: {execution.job_type} | Started:{" "}
                  {execution.started_at
                    ? formatDistanceToNow(new Date(execution.started_at * 1000), {
                        addSuffix: true,
                      })
                    : "N/A"}
                </Typography>
              </Box>
              <Chip
                label={execution.status.toUpperCase()}
                color={execution.status === "running" ? "primary" : "default"}
                size="small"
              />
            </Box>

            {execution.duration_seconds !== undefined && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Duration: {(execution.duration_seconds / 60).toFixed(1)} minutes
                </Typography>
                <LinearProgress variant="determinate" value={0} sx={{ mt: 1 }} />
              </Box>
            )}

            {execution.stages && execution.stages.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Stages ({execution.stages.length})
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Stage</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Duration</TableCell>
                        <TableCell>Attempt</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {execution.stages.map((stage) => (
                        <TableRow key={stage.name}>
                          <TableCell>{stage.name.replace(/_/g, " ")}</TableCell>
                          <TableCell>
                            <Chip
                              label={stage.status}
                              size="small"
                              color={
                                stage.status === "completed"
                                  ? "success"
                                  : stage.status === "failed"
                                    ? "error"
                                    : stage.status === "running"
                                      ? "primary"
                                      : "default"
                              }
                            />
                          </TableCell>
                          <TableCell>
                            {stage.duration_seconds
                              ? `${stage.duration_seconds.toFixed(1)}s`
                              : "N/A"}
                          </TableCell>
                          <TableCell>{stage.attempt}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}

            <ExecutionDetails execution={execution} />
          </CardContent>
        </Card>
      ))}
    </Box>
  );
}
