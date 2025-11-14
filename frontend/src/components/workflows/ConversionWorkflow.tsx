/**
 * Conversion Workflow Component
 * Handles UVH5 to MS conversion and full pipeline workflow
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
  Stack,
  Alert,
  Tooltip,
  CircularProgress,
} from "@mui/material";
import { PlayArrow } from "@mui/icons-material";
import {
  useCreateConvertJob,
  useCreateWorkflowJob,
  useUVH5Files,
  useMSMetadata,
} from "../../api/queries";
import { useNotifications } from "../../contexts/NotificationContext";
import { ValidatedTextField } from "../ValidatedTextField";
import { validationRules, validateTimeRange } from "../../utils/formValidation";
import type { ConversionJobParams } from "../../api/types";

interface ConversionWorkflowProps {
  selectedMS: string;
  onJobCreated?: (jobId: number) => void;
  onRefreshJobs?: () => void;
}

export function ConversionWorkflow({
  selectedMS,
  onJobCreated,
  onRefreshJobs,
}: ConversionWorkflowProps) {
  const { showError, showSuccess } = useNotifications();

  // Conversion parameters state
  const [convertParams, setConvertParams] = useState<ConversionJobParams>({
    input_dir: "/data/incoming",
    output_dir: "/scratch/dsa110-contimg/ms",
    start_time: "",
    end_time: "",
    writer: "auto",
    stage_to_tmpfs: true,
    max_workers: 4,
  });

  // Workflow parameters state (full pipeline)
  const [workflowParams, setWorkflowParams] = useState({
    start_time: "",
    end_time: "",
  });

  // Queries and mutations
  const convertMutation = useCreateConvertJob();
  const workflowMutation = useCreateWorkflowJob();
  const { data: uvh5Files } = useUVH5Files(convertParams.input_dir);
  const { data: msMetadata } = useMSMetadata(selectedMS);

  // Helper function to extract error message from API error
  const getErrorMessage = (error: unknown): string => {
    if (error && typeof error === "object") {
      // Handle axios errors
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
      // Handle standard Error objects
      if ("message" in error && typeof error.message === "string") {
        return error.message;
      }
    }
    return "An unknown error occurred";
  };

  // Conversion submit handler
  const handleConvertSubmit = useCallback(() => {
    convertMutation.mutate(
      { params: convertParams },
      {
        onSuccess: (job) => {
          onJobCreated?.(job.id);
          onRefreshJobs?.();
          showSuccess(`Conversion job #${job.id} started successfully`);
        },
        onError: (error: unknown) => {
          const message = `Conversion failed: ${getErrorMessage(error)}`;
          showError(message);
        },
      }
    );
  }, [convertParams, convertMutation, onJobCreated, onRefreshJobs, showError, showSuccess]);

  // Workflow submit handler (full pipeline)
  const handleWorkflowSubmit = useCallback(() => {
    if (!workflowParams.start_time || !workflowParams.end_time) return;
    workflowMutation.mutate(
      { params: workflowParams },
      {
        onSuccess: (job) => {
          onJobCreated?.(job.id);
          onRefreshJobs?.();
          showSuccess(`Pipeline workflow job #${job.id} started successfully`);
        },
        onError: (error: unknown) => {
          const message = `Pipeline workflow failed: ${getErrorMessage(error)}`;
          showError(message);
        },
      }
    );
  }, [workflowParams, workflowMutation, onJobCreated, onRefreshJobs, showError, showSuccess]);

  return (
    <Box>
      {/* Full Pipeline Workflow Form */}
      <Paper sx={{ p: 2, mb: 2, bgcolor: "#f5f5f5" }}>
        <Typography variant="h6" sx={{ mb: 2, color: "#1565c0" }}>
          Full Pipeline Workflow
        </Typography>
        <Stack direction="row" spacing={2} alignItems="center">
          <ValidatedTextField
            label="Start Time"
            value={workflowParams.start_time}
            onChange={(e) =>
              setWorkflowParams({
                ...workflowParams,
                start_time: e.target.value,
              })
            }
            size="small"
            placeholder="YYYY-MM-DD HH:MM:SS"
            validationRules={[
              validationRules.required("Start time is required"),
              validationRules.pattern(
                /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/,
                "Use format: YYYY-MM-DD HH:MM:SS"
              ),
            ]}
            sx={{
              bgcolor: "white",
              borderRadius: 1,
              "& .MuiInputBase-root": { color: "#000" },
              "& .MuiInputLabel-root": { color: "#666" },
            }}
          />
          <ValidatedTextField
            label="End Time"
            value={workflowParams.end_time}
            onChange={(e) =>
              setWorkflowParams({
                ...workflowParams,
                end_time: e.target.value,
              })
            }
            size="small"
            placeholder="YYYY-MM-DD HH:MM:SS"
            validationRules={[
              validationRules.required("End time is required"),
              validationRules.pattern(
                /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/,
                "Use format: YYYY-MM-DD HH:MM:SS"
              ),
              {
                validate: (value: string) => {
                  if (!workflowParams.start_time) return true;
                  const result = validateTimeRange(workflowParams.start_time, value);
                  return result.isValid;
                },
                message: "End time must be after start time",
              },
            ]}
            sx={{
              bgcolor: "white",
              borderRadius: 1,
              "& .MuiInputBase-root": { color: "#000" },
              "& .MuiInputLabel-root": { color: "#666" },
            }}
          />
          <Tooltip
            title={
              !workflowParams.start_time || !workflowParams.end_time
                ? "Enter start and end times to run the full pipeline"
                : workflowMutation.isPending
                  ? "Pipeline workflow in progress..."
                  : "Run full pipeline workflow (Ctrl/Cmd + Enter)"
            }
          >
            <span>
              <Button
                variant="contained"
                startIcon={
                  workflowMutation.isPending ? (
                    <CircularProgress size={20} color="inherit" />
                  ) : (
                    <PlayArrow />
                  )
                }
                onClick={handleWorkflowSubmit}
                disabled={
                  !workflowParams.start_time ||
                  !workflowParams.end_time ||
                  workflowMutation.isPending
                }
                sx={{
                  bgcolor: "#fff",
                  color: "#1565c0",
                  "&:hover": { bgcolor: "#f5f5f5" },
                  whiteSpace: "nowrap",
                }}
              >
                {workflowMutation.isPending ? "Running..." : "Run Full Pipeline"}
              </Button>
            </span>
          </Tooltip>
        </Stack>
      </Paper>

      {/* Conversion Form */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Convert UVH5 to Measurement Set
        </Typography>

        {selectedMS && msMetadata && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              An MS is currently selected: <strong>{selectedMS.split("/").pop()}</strong>
            </Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Switch to the <strong>Calibrate</strong> tab to use this MS for calibration.
            </Typography>
            {msMetadata.start_time && msMetadata.end_time && (
              <Button
                size="small"
                variant="outlined"
                onClick={() => {
                  setConvertParams({
                    ...convertParams,
                    start_time: msMetadata.start_time || "",
                    end_time: msMetadata.end_time || "",
                  });
                }}
                sx={{ mt: 1 }}
              >
                Use this MS's time range for conversion
              </Button>
            )}
          </Alert>
        )}

        <Typography variant="body2" sx={{ mb: 2, color: "text.secondary" }}>
          Convert UVH5 files to Measurement Set format:
        </Typography>

        <Typography variant="subtitle2" gutterBottom>
          Time Range
        </Typography>
        <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
          <ValidatedTextField
            fullWidth
            label="Start Time"
            value={convertParams.start_time}
            onChange={(e) =>
              setConvertParams({
                ...convertParams,
                start_time: e.target.value,
              })
            }
            size="small"
            placeholder="YYYY-MM-DD HH:MM:SS"
            validationRules={[
              validationRules.required("Start time is required"),
              validationRules.pattern(
                /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/,
                "Use format: YYYY-MM-DD HH:MM:SS"
              ),
            ]}
          />
          <ValidatedTextField
            fullWidth
            label="End Time"
            value={convertParams.end_time}
            onChange={(e) =>
              setConvertParams({
                ...convertParams,
                end_time: e.target.value,
              })
            }
            size="small"
            placeholder="YYYY-MM-DD HH:MM:SS"
            validationRules={[
              validationRules.required("End time is required"),
              validationRules.pattern(
                /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/,
                "Use format: YYYY-MM-DD HH:MM:SS"
              ),
              {
                validate: (value: string) => {
                  if (!convertParams.start_time) return true;
                  const result = validateTimeRange(convertParams.start_time, value);
                  return result.isValid;
                },
                message: "End time must be after start time",
              },
            ]}
          />
        </Stack>

        <Typography variant="subtitle2" gutterBottom>
          Directories
        </Typography>
        <TextField
          fullWidth
          label="Input Directory"
          value={convertParams.input_dir}
          onChange={(e) =>
            setConvertParams({
              ...convertParams,
              input_dir: e.target.value,
            })
          }
          sx={{ mb: 2 }}
          size="small"
        />
        <TextField
          fullWidth
          label="Output Directory"
          value={convertParams.output_dir}
          onChange={(e) =>
            setConvertParams({
              ...convertParams,
              output_dir: e.target.value,
            })
          }
          sx={{ mb: 2 }}
          size="small"
        />

        <FormControl fullWidth sx={{ mb: 2 }} size="small">
          <InputLabel>Writer Type</InputLabel>
          <Select
            value={convertParams.writer}
            onChange={(e) =>
              setConvertParams({
                ...convertParams,
                writer: e.target.value,
              })
            }
            label="Writer Type"
          >
            <MenuItem value="auto">Auto (recommended)</MenuItem>
            <MenuItem value="sequential">Sequential</MenuItem>
            <MenuItem value="parallel">Parallel</MenuItem>
            <MenuItem value="dask">Dask</MenuItem>
          </Select>
        </FormControl>

        <FormControlLabel
          control={
            <Checkbox
              checked={convertParams.stage_to_tmpfs}
              onChange={(e) =>
                setConvertParams({
                  ...convertParams,
                  stage_to_tmpfs: e.target.checked,
                })
              }
            />
          }
          label="Stage to tmpfs (faster but uses RAM)"
          sx={{ mb: 2 }}
        />

        <TextField
          fullWidth
          label="Max Workers"
          type="number"
          value={convertParams.max_workers}
          onChange={(e) => {
            const val = parseInt(e.target.value, 10);
            if (!isNaN(val) && val >= 1 && val <= 16) {
              setConvertParams({ ...convertParams, max_workers: val });
            }
          }}
          sx={{ mb: 2 }}
          size="small"
          inputProps={{ min: 1, max: 16 }}
        />

        {/* UVH5 File List */}
        {uvh5Files && uvh5Files.items.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Available UVH5 Files ({uvh5Files.items.length})
            </Typography>
            <Box
              sx={{
                maxHeight: 200,
                overflow: "auto",
                bgcolor: "#1e1e1e",
                p: 1,
                borderRadius: 1,
                fontFamily: "monospace",
                fontSize: "0.7rem",
              }}
            >
              {uvh5Files.items.map((file) => (
                <Box key={file.path} sx={{ color: "#ffffff", mb: 0.3 }}>
                  {file.path.split("/").pop()} ({file.size_mb?.toFixed(1)} MB)
                </Box>
              ))}
            </Box>
          </Box>
        )}

        <Tooltip
          title={
            !convertParams.start_time || !convertParams.end_time
              ? "Enter start and end times to run conversion"
              : convertMutation.isPending
                ? "Conversion job in progress..."
                : "Run conversion (Ctrl/Cmd + Enter)"
          }
        >
          <span>
            <Button
              variant="contained"
              startIcon={
                convertMutation.isPending ? (
                  <CircularProgress size={20} color="inherit" />
                ) : (
                  <PlayArrow />
                )
              }
              onClick={handleConvertSubmit}
              disabled={
                !convertParams.start_time || !convertParams.end_time || convertMutation.isPending
              }
              fullWidth
            >
              {convertMutation.isPending ? "Running..." : "Run Conversion"}
            </Button>
          </span>
        </Tooltip>
      </Paper>
    </Box>
  );
}
