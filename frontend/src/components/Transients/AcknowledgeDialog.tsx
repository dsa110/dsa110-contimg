import { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
} from "@mui/material";

interface AcknowledgeDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (acknowledgedBy: string, notes?: string) => void;
  alertId?: number;
}

export function AcknowledgeDialog({ open, onClose, onConfirm, alertId }: AcknowledgeDialogProps) {
  const [acknowledgedBy, setAcknowledgedBy] = useState("");
  const [notes, setNotes] = useState("");

  const handleSubmit = () => {
    if (!acknowledgedBy.trim()) return;
    onConfirm(acknowledgedBy.trim(), notes.trim() || undefined);
    setAcknowledgedBy("");
    setNotes("");
  };

  const handleClose = () => {
    setAcknowledgedBy("");
    setNotes("");
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Acknowledge Alert #{alertId}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 2 }}>
          <TextField
            label="Acknowledged By"
            value={acknowledgedBy}
            onChange={(e) => setAcknowledgedBy(e.target.value)}
            required
            fullWidth
            helperText="Your name or username"
          />
          <TextField
            label="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            multiline
            rows={3}
            fullWidth
            helperText="Any additional comments or context"
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button onClick={handleSubmit} variant="contained" disabled={!acknowledgedBy.trim()}>
          Acknowledge
        </Button>
      </DialogActions>
    </Dialog>
  );
}
