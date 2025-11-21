import React from "react";
import {
  Box,
  Typography,
  Button,
  Paper,
  Divider,
  List,
  ListItem,
  ListItemText,
  Chip,
  Alert,
} from "@mui/material";
import type { CalibrationStatus } from "../../api/types";

interface CalibrationReviewProps {
  status: CalibrationStatus | null;
  onReset: () => void;
}

export const CalibrationReview: React.FC<CalibrationReviewProps> = ({ status, onReset }) => {
  return (
    <Box sx={{ mt: 2 }}>
      <Alert severity={status?.status === "completed" ? "success" : "warning"} sx={{ mb: 3 }}>
        Calibration{" "}
        {status?.status === "completed" ? "completed successfully" : "finished with issues"}.
      </Alert>

      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Summary
        </Typography>
        <Divider />
        <List dense>
          <ListItem>
            <ListItemText primary="Measurement Set" secondary={status?.config?.msPath || "N/A"} />
          </ListItem>
          <ListItem>
            <ListItemText
              primary="Duration"
              secondary={status?.duration ? `${status.duration} seconds` : "N/A"}
            />
          </ListItem>
          <ListItem>
            <ListItemText primary="Status" />
            <Chip
              label={status?.status || "Unknown"}
              color={status?.status === "completed" ? "success" : "default"}
              size="small"
            />
          </ListItem>
        </List>
      </Paper>

      <Box>
        <Button variant="contained" onClick={onReset}>
          Start New Calibration
        </Button>
      </Box>
    </Box>
  );
};
