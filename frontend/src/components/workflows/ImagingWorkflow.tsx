/**
 * Imaging Workflow Component
 * Handles MS imaging using CASA tclean
 */
import { useState, useCallback } from "react";
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  FormControlLabel,
  Checkbox,
  Switch,
  Tooltip,
  CircularProgress,
} from "@mui/material";
import { PlayArrow } from "@mui/icons-material";
import { useCreateImageJob, useMSMetadata } from "../../api/queries";
import { useNotifications } from "../../contexts/NotificationContext";
import type { JobParams } from "../../api/types";

interface ImagingWorkflowProps {
  selectedMS: string;
  onJobCreated?: (jobId: number) => void;
  onRefreshJobs?: () => void;
}

export function ImagingWorkflow({ selectedMS, onJobCreated, onRefreshJobs }: ImagingWorkflowProps) {
  const { showError, showSuccess } = useNotifications();

  // Imaging parameters state
  const [imageParams, setImageParams] = useState<JobParams>({
    gridder: "wproject",
    wprojplanes: -1,
    datacolumn: "corrected",
    quick: false,
    skip_fits: true,
    use_nvss_mask: true,
    mask_radius_arcsec: 60.0,
  });

  // Queries and mutations
  const imageMutation = useCreateImageJob();
  const { data: msMetadata } = useMSMetadata(selectedMS);

  // Helper function to extract error message from API error
  const getErrorMessage = (error: unknown): string => {
    if (error && typeof error === "object") {
      if ("response" in error) {
        const apiError = error as {
          response?: { data?: { detail?: unknown; message?: string } };
        };
        if (apiError.response?.data?.detail) {
          return typeof apiError.response.data.detail === "string"
            ? apiError.response.data.detail
            : JSON.stringify(apiError.response.data.detail);
        }
        if (apiError.response?.data?.message) {
          return apiError.response.data.message;
        }
      }
      if ("message" in error && typeof error.message === "string") {
        return error.message;
      }
    }
    return "An unknown error occurred";
  };

  // Imaging submit handler
  const handleImageSubmit = useCallback(() => {
    if (!selectedMS) return;
    imageMutation.mutate(
      { ms_path: selectedMS, params: imageParams },
      {
        onSuccess: (job) => {
          onJobCreated?.(job.id);
          onRefreshJobs?.();
          showSuccess(`Imaging job #${job.id} started successfully`);
        },
        onError: (error: unknown) => {
          const message = `Imaging failed: ${getErrorMessage(error)}`;
          showError(message);
        },
      }
    );
  }, [selectedMS, imageParams, imageMutation, onJobCreated, onRefreshJobs, showError, showSuccess]);

  return (
    <Box>
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Image Measurement Set
        </Typography>
        <Typography variant="body2" sx={{ mb: 2, color: "text.secondary" }}>
          Image the selected MS using CASA tclean:
        </Typography>
        <Box
          sx={{
            mb: 2,
            p: 1.5,
            bgcolor: "#1e1e1e",
            borderRadius: 1,
            fontFamily: "monospace",
            fontSize: "0.75rem",
            color: "#ffffff",
          }}
        >
          <Box sx={{ mb: 0.5 }}>• Auto-detects pixel size and image dimensions</Box>
          <Box sx={{ mb: 0.5 }}>• Uses w-projection for wide-field imaging</Box>
          <Box>• Outputs .image, .residual, .psf, and optionally .fits</Box>
        </Box>

        <Typography variant="subtitle2" gutterBottom>
          Imaging Parameters
        </Typography>
        <FormControl fullWidth sx={{ mb: 2 }} size="small">
          <InputLabel>Gridder</InputLabel>
          <Select
            value={imageParams.gridder}
            onChange={(e) =>
              setImageParams({
                ...imageParams,
                gridder: e.target.value,
              })
            }
            label="Gridder"
          >
            <MenuItem value="wproject">W-projection (recommended)</MenuItem>
            <MenuItem value="standard">Standard</MenuItem>
            <MenuItem value="widefield">Widefield</MenuItem>
          </Select>
        </FormControl>

        <TextField
          fullWidth
          label="W-projection planes"
          type="number"
          value={imageParams.wprojplanes}
          onChange={(e) => {
            const val = parseInt(e.target.value, 10);
            if (!isNaN(val) && val >= -1) {
              setImageParams({ ...imageParams, wprojplanes: val });
            }
          }}
          sx={{ mb: 2 }}
          size="small"
          helperText="-1 for auto, or specify number of planes"
        />

        <FormControl fullWidth sx={{ mb: 2 }} size="small">
          <InputLabel>Data Column</InputLabel>
          <Select
            value={imageParams.datacolumn}
            onChange={(e) =>
              setImageParams({
                ...imageParams,
                datacolumn: e.target.value,
              })
            }
            label="Data Column"
          >
            <MenuItem value="corrected">CORRECTED_DATA (after calibration)</MenuItem>
            <MenuItem value="data">DATA (raw visibilities)</MenuItem>
          </Select>
        </FormControl>

        {selectedMS && msMetadata && (
          <>
            {(() => {
              const hasCorrectedData = msMetadata.data_columns.includes("CORRECTED_DATA");
              const usingDataColumn = imageParams.datacolumn === "data";

              if (hasCorrectedData && usingDataColumn) {
                return (
                  <Box
                    sx={{
                      mb: 2,
                      p: 1.5,
                      bgcolor: "#3e2723",
                      borderRadius: 1,
                      border: "1px solid #ff9800",
                    }}
                  >
                    <Typography variant="caption" sx={{ color: "#ffccbc", fontWeight: "bold" }}>
                      Warning: CORRECTED_DATA column exists but you're imaging DATA column. Consider
                      using CORRECTED_DATA for calibrated data.
                    </Typography>
                  </Box>
                );
              }

              if (!hasCorrectedData && !usingDataColumn) {
                return (
                  <Box
                    sx={{
                      mb: 2,
                      p: 1.5,
                      bgcolor: "#3e2723",
                      borderRadius: 1,
                      border: "1px solid #d32f2f",
                    }}
                  >
                    <Typography variant="caption" sx={{ color: "#ffccbc", fontWeight: "bold" }}>
                      Error: CORRECTED_DATA column does not exist. Please apply calibration first or
                      use DATA column.
                    </Typography>
                  </Box>
                );
              }

              return null;
            })()}
          </>
        )}

        <FormControlLabel
          control={
            <Checkbox
              checked={imageParams.quick || false}
              onChange={(e) =>
                setImageParams({
                  ...imageParams,
                  quick: e.target.checked,
                })
              }
            />
          }
          label="Quick mode (fewer iterations)"
          sx={{ mb: 1 }}
        />

        <FormControlLabel
          control={
            <Checkbox
              checked={imageParams.skip_fits !== false}
              onChange={(e) =>
                setImageParams({
                  ...imageParams,
                  skip_fits: e.target.checked,
                })
              }
            />
          }
          label="Skip FITS export (faster)"
          sx={{ mb: 2 }}
        />

        <FormControlLabel
          control={
            <Switch
              checked={imageParams.use_nvss_mask ?? true}
              onChange={(e) =>
                setImageParams({
                  ...imageParams,
                  use_nvss_mask: e.target.checked,
                })
              }
              color="primary"
            />
          }
          label={
            <Box>
              <Typography variant="body2">Use NVSS Masking</Typography>
              <Typography variant="caption" color="text.secondary" display="block">
                Enable masked imaging (2-4x faster, recommended)
              </Typography>
            </Box>
          }
          sx={{ mb: 2 }}
        />

        {imageParams.use_nvss_mask && (
          <TextField
            fullWidth
            label="Mask Radius (arcsec)"
            type="number"
            value={imageParams.mask_radius_arcsec ?? 60.0}
            onChange={(e) => {
              const val = parseFloat(e.target.value);
              if (!isNaN(val) && val >= 10 && val <= 300) {
                setImageParams({
                  ...imageParams,
                  mask_radius_arcsec: val,
                });
              }
            }}
            sx={{ mb: 2 }}
            size="small"
            helperText="Radius around NVSS sources (default: 60 arcsec, ~2-3× beam)"
            inputProps={{ min: 10, max: 300, step: 5 }}
          />
        )}

        <Tooltip
          title={
            !selectedMS
              ? "Select a measurement set first"
              : imageMutation.isPending
                ? "Imaging job in progress..."
                : "Create image (Ctrl/Cmd + Enter)"
          }
        >
          <span>
            <Button
              variant="contained"
              startIcon={
                imageMutation.isPending ? (
                  <CircularProgress size={20} color="inherit" />
                ) : (
                  <PlayArrow />
                )
              }
              onClick={handleImageSubmit}
              disabled={!selectedMS || imageMutation.isPending}
              fullWidth
            >
              {imageMutation.isPending ? "Running..." : "Create Image"}
            </Button>
          </span>
        </Tooltip>
      </Paper>
    </Box>
  );
}
