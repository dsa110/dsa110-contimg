import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Stack,
  Grid,
  FormControlLabel,
  Switch,
} from "@mui/material";
import type { StreamingConfig } from "../../api/queries";

interface StreamingConfigDialogProps {
  open: boolean;
  onClose: () => void;
  config: StreamingConfig | null;
  onSave: (config: StreamingConfig) => void;
  isSaving: boolean;
}

export const StreamingConfigDialog: React.FC<StreamingConfigDialogProps> = ({
  open,
  onClose,
  config,
  onSave,
  isSaving,
}) => {
  const [editedConfig, setEditedConfig] = React.useState<StreamingConfig | null>(null);

  React.useEffect(() => {
    if (config) {
      setEditedConfig({ ...config });
    }
  }, [config]);

  if (!editedConfig) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Streaming Service Configuration</DialogTitle>
      <DialogContent>
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
            <Grid item xs={6}>
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
            <Grid item xs={6}>
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
            <Grid item xs={6}>
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
            <Grid item xs={6}>
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
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={() => onSave(editedConfig)} variant="contained" disabled={isSaving}>
          {isSaving ? "Saving..." : "Save & Apply"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
