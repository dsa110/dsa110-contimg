import { useState } from "react";
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Typography,
  IconButton,
  Tooltip,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import NoteAddIcon from "@mui/icons-material/NoteAdd";
import AssignmentIcon from "@mui/icons-material/Assignment";
import { useTransientAlerts, useAcknowledgeAlert } from "../../api/queries";
import { AcknowledgeDialog } from "./AcknowledgeDialog";
import type { TransientAlert } from "../../api/types";

export function TransientAlertsTable() {
  const [alertLevel, setAlertLevel] = useState<string>("");
  const [showAcknowledged, setShowAcknowledged] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState<TransientAlert | null>(null);
  const [ackDialogOpen, setAckDialogOpen] = useState(false);

  const {
    data: alerts,
    isLoading,
    error,
    refetch,
  } = useTransientAlerts(alertLevel || undefined, showAcknowledged, 50);

  const acknowledgeMutation = useAcknowledgeAlert();

  const handleAcknowledge = (alert: TransientAlert) => {
    setSelectedAlert(alert);
    setAckDialogOpen(true);
  };

  const handleAcknowledgeConfirm = async (acknowledgedBy: string, notes?: string) => {
    if (!selectedAlert) return;

    try {
      await acknowledgeMutation.mutateAsync({
        alertId: String(selectedAlert.id),
        data: { acknowledged_by: acknowledgedBy, notes },
      });
      setAckDialogOpen(false);
      setSelectedAlert(null);
      refetch();
    } catch (error) {
      console.error("Failed to acknowledge alert:", error);
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="error">Failed to load alerts: {String(error)}</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 2, display: "flex", gap: 2, alignItems: "center" }}>
        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel>Alert Level</InputLabel>
          <Select
            value={alertLevel}
            label="Alert Level"
            onChange={(e) => setAlertLevel(e.target.value)}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="CRITICAL">Critical</MenuItem>
            <MenuItem value="HIGH">High</MenuItem>
            <MenuItem value="MEDIUM">Medium</MenuItem>
          </Select>
        </FormControl>

        <Button
          variant={showAcknowledged ? "contained" : "outlined"}
          onClick={() => setShowAcknowledged(!showAcknowledged)}
        >
          {showAcknowledged ? "Show Unacknowledged" : "Show Acknowledged"}
        </Button>

        <Typography sx={{ ml: "auto" }}>
          {alerts?.length || 0} alert{alerts?.length !== 1 ? "s" : ""}
        </Typography>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Level</TableCell>
              <TableCell>Message</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {alerts?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="textSecondary">No alerts found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              alerts?.map((alert) => (
                <TableRow key={alert.id}>
                  <TableCell>{alert.id}</TableCell>
                  <TableCell>
                    <Chip
                      label={alert.alert_level}
                      color={
                        alert.alert_level === "CRITICAL"
                          ? "error"
                          : alert.alert_level === "HIGH"
                            ? "warning"
                            : "info"
                      }
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{alert.alert_message}</TableCell>
                  <TableCell>{new Date(alert.created_at * 1000).toLocaleString()}</TableCell>
                  <TableCell>
                    {alert.acknowledged ? (
                      <Chip
                        icon={<CheckCircleIcon />}
                        label={`By ${alert.acknowledged_by}`}
                        size="small"
                        color="success"
                      />
                    ) : (
                      <Chip label="Pending" size="small" color="default" />
                    )}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", gap: 1 }}>
                      {!alert.acknowledged && (
                        <Tooltip title="Acknowledge">
                          <IconButton
                            size="small"
                            onClick={() => handleAcknowledge(alert)}
                            color="primary"
                          >
                            <CheckCircleIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                      <Tooltip title="Follow-up Status">
                        <IconButton size="small" color="default">
                          <AssignmentIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Add Notes">
                        <IconButton size="small" color="default">
                          <NoteAddIcon />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <AcknowledgeDialog
        open={ackDialogOpen}
        onClose={() => {
          setAckDialogOpen(false);
          setSelectedAlert(null);
        }}
        onConfirm={handleAcknowledgeConfirm}
        alertId={
          typeof selectedAlert?.id === "string" ? parseInt(selectedAlert.id, 10) : selectedAlert?.id
        }
      />
    </Box>
  );
}
