import { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";

interface ClassifyDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (classification: string, classifiedBy: string, notes?: string) => void;
  candidateId?: number;
  currentClassification?: string | null;
}

export function ClassifyDialog({
  open,
  onClose,
  onConfirm,
  candidateId,
  currentClassification,
}: ClassifyDialogProps) {
  const [classification, setClassification] = useState(currentClassification || "");
  const [classifiedBy, setClassifiedBy] = useState("");
  const [notes, setNotes] = useState("");

  const handleSubmit = () => {
    if (!classification || !classifiedBy.trim()) return;
    onConfirm(classification, classifiedBy.trim(), notes.trim() || undefined);
    setClassification("");
    setClassifiedBy("");
    setNotes("");
  };

  const handleClose = () => {
    setClassification(currentClassification || "");
    setClassifiedBy("");
    setNotes("");
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Classify Candidate #{candidateId}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 2 }}>
          <FormControl fullWidth required>
            <InputLabel>Classification</InputLabel>
            <Select
              value={classification}
              label="Classification"
              onChange={(e) => setClassification(e.target.value)}
            >
              <MenuItem value="real">Real</MenuItem>
              <MenuItem value="artifact">Artifact</MenuItem>
              <MenuItem value="variable">Variable</MenuItem>
              <MenuItem value="uncertain">Uncertain</MenuItem>
            </Select>
          </FormControl>

          <TextField
            label="Classified By"
            value={classifiedBy}
            onChange={(e) => setClassifiedBy(e.target.value)}
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
            helperText="Justification or additional details"
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={!classification || !classifiedBy.trim()}
        >
          Classify
        </Button>
      </DialogActions>
    </Dialog>
  );
}
