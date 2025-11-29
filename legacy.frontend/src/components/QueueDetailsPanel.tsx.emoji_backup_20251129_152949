/**
 * Queue Details Panel Component
 * Displays detailed information about queue items filtered by status
 */
import React from "react";
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Alert,
  CircularProgress,
} from "@mui/material";
import type { QueueGroup } from "../api/types";

interface QueueDetailsPanelProps {
  selectedStatus: "total" | "pending" | "in_progress" | "completed" | "failed" | "collecting";
  queueGroups: QueueGroup[];
  isLoading?: boolean;
}

const statusLabels: Record<string, string> = {
  total: "All Queue Items",
  pending: "Pending Items",
  in_progress: "In Progress Items",
  completed: "Completed Items",
  failed: "Failed Items",
  collecting: "Collecting Items",
};

const statusColors: Record<
  string,
  "default" | "primary" | "success" | "warning" | "error" | "info"
> = {
  total: "default",
  pending: "info",
  in_progress: "warning",
  completed: "success",
  failed: "error",
  collecting: "info",
};

export default function QueueDetailsPanel({
  selectedStatus,
  queueGroups,
  isLoading = false,
}: QueueDetailsPanelProps) {
  // Filter groups by selected status
  // Map status names to actual queue states
  const statusToStateMap: Record<string, string> = {
    total: "", // Empty string means show all
    pending: "pending",
    in_progress: "in_progress",
    completed: "completed",
    failed: "failed",
    collecting: "collecting",
  };

  const filteredGroups = React.useMemo(() => {
    if (selectedStatus === "total") {
      return queueGroups;
    }
    const targetState = statusToStateMap[selectedStatus];
    return queueGroups.filter((group) => group.state === targetState);
  }, [queueGroups, selectedStatus]);

  if (isLoading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
          <CircularProgress />
        </Box>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2, height: "100%" }}>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          {statusLabels[selectedStatus]}
        </Typography>
        <Chip
          label={`${filteredGroups.length} item${filteredGroups.length !== 1 ? "s" : ""}`}
          color={statusColors[selectedStatus]}
          size="small"
        />
      </Box>

      {filteredGroups.length === 0 ? (
        <Alert severity="info" sx={{ mt: 2 }}>
          No {statusLabels[selectedStatus].toLowerCase()} found.
        </Alert>
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Group ID</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>State</TableCell>
                <TableCell sx={{ fontWeight: 600 }} align="right">
                  Subbands
                </TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Calibrator</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Last Update</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredGroups.slice(0, 10).map((group) => (
                <TableRow key={group.group_id} hover>
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
                              ? "warning"
                              : "default"
                      }
                    />
                  </TableCell>
                  <TableCell align="right">
                    {group.subbands_present}/{group.expected_subbands}
                  </TableCell>
                  <TableCell>{group.has_calibrator ? "✓" : "—"}</TableCell>
                  <TableCell>
                    {group.last_update ? new Date(group.last_update).toLocaleString() : "N/A"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {filteredGroups.length > 10 && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
          Showing 10 of {filteredGroups.length} items
        </Typography>
      )}
    </Paper>
  );
}
