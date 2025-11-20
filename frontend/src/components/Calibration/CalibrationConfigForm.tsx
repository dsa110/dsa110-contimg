import React, { useState } from "react";
import { Box, Button, TextField } from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import type { CalibrationConfig } from "../../api/types";

interface CalibrationConfigFormProps {
  onSubmit: (config: CalibrationConfig) => void;
  isSubmitting: boolean;
  initialValues?: Partial<CalibrationConfig>;
}

export const CalibrationConfigForm: React.FC<CalibrationConfigFormProps> = ({
  onSubmit,
  isSubmitting,
  initialValues,
}) => {
  const [msPath, setMsPath] = useState(initialValues?.msPath || "");
  const [calibrator, setCalibrator] = useState(initialValues?.calibrator || "");
  const [refAnt, setRefAnt] = useState(initialValues?.refAnt || "");

  // Update state if initialValues change
  React.useEffect(() => {
    if (initialValues) {
      if (initialValues.msPath) setMsPath(initialValues.msPath);
      if (initialValues.calibrator) setCalibrator(initialValues.calibrator);
      if (initialValues.refAnt) setRefAnt(initialValues.refAnt);
    }
  }, [initialValues]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      msPath,
      calibrator,
      refAnt,
    });
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Measurement Set Path"
            value={msPath}
            onChange={(e) => setMsPath(e.target.value)}
            required
            helperText="Path to the .ms directory"
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Calibrator Source"
            value={calibrator}
            onChange={(e) => setCalibrator(e.target.value)}
            helperText="e.g., 3C286 (optional)"
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Reference Antenna"
            value={refAnt}
            onChange={(e) => setRefAnt(e.target.value)}
            helperText="e.g., ea01 (optional)"
          />
        </Grid>
        <Grid item xs={12}>
          <Button type="submit" variant="contained" disabled={isSubmitting || !msPath}>
            {isSubmitting ? "Starting..." : "Start Calibration"}
          </Button>
        </Grid>
      </Grid>
    </Box>
  );
};
