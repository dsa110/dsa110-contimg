/**
 * Workflow Builder Component
 * Visual builder for multi-stage Absurd pipeline workflows
 */

import { useState, useCallback } from "react";
import {
  Box,
  Typography,
  Button,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Chip,
  IconButton,
  Alert,
  CircularProgress,
  useTheme,
} from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import { Add, Delete, PlayArrow, ArrowDownward } from "@mui/icons-material";
import { useSpawnTask } from "../../api/absurdQueries";
import { useNotifications } from "../../contexts/NotificationContext";
import type { SpawnTaskRequest } from "../../api/absurd";

interface WorkflowStage {
  id: string;
  taskName: string;
  params: Record<string, any>;
  priority: number;
  timeoutSec?: number;
}

interface WorkflowBuilderProps {
  queueName?: string;
  onWorkflowSubmitted?: (taskIds: string[]) => void;
}

const AVAILABLE_TASKS = [
  { value: "catalog-setup", label: "Catalog Setup" },
  { value: "convert-uvh5-to-ms", label: "Convert UVH5 to MS" },
  { value: "calibration-solve", label: "Calibration Solve" },
  { value: "calibration-apply", label: "Apply Calibration" },
  { value: "imaging", label: "Imaging" },
  { value: "validation", label: "Validation" },
  { value: "crossmatch", label: "Crossmatch" },
  { value: "photometry", label: "Photometry" },
  { value: "organize-files", label: "Organize Files" },
];

const DEFAULT_PRIORITIES: Record<string, number> = {
  "catalog-setup": 10,
  "convert-uvh5-to-ms": 15,
  "calibration-solve": 12,
  "calibration-apply": 10,
  imaging: 8,
  validation: 5,
  crossmatch: 5,
  photometry: 5,
  "organize-files": 3,
};

export function WorkflowBuilder({
  queueName = "dsa110-pipeline",
  onWorkflowSubmitted,
}: WorkflowBuilderProps) {
  const theme = useTheme();
  const { showSuccess, showError } = useNotifications();
  const spawnMutation = useSpawnTask();

  const [stages, setStages] = useState<WorkflowStage[]>([
    {
      id: "1",
      taskName: "convert-uvh5-to-ms",
      params: {},
      priority: 15,
    },
  ]);

  const [activeStep, setActiveStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  // Add new stage
  const handleAddStage = useCallback(() => {
    const newStage: WorkflowStage = {
      id: Date.now().toString(),
      taskName: "",
      params: {},
      priority: 5,
    };
    setStages([...stages, newStage]);
    setActiveStep(stages.length);
  }, [stages]);

  // Remove stage
  const handleRemoveStage = useCallback(
    (index: number) => {
      const newStages = stages.filter((_, i) => i !== index);
      setStages(newStages);
      if (activeStep >= newStages.length) {
        setActiveStep(Math.max(0, newStages.length - 1));
      }
    },
    [stages, activeStep]
  );

  // Update stage
  const handleUpdateStage = useCallback(
    (index: number, updates: Partial<WorkflowStage>) => {
      const newStages = [...stages];
      newStages[index] = { ...newStages[index], ...updates };
      setStages(newStages);
    },
    [stages]
  );

  // Update stage params
  const handleUpdateParams = useCallback(
    (index: number, key: string, value: any) => {
      const newStages = [...stages];
      newStages[index] = {
        ...newStages[index],
        params: {
          ...newStages[index].params,
          [key]: value,
        },
      };
      setStages(newStages);
    },
    [stages]
  );

  // Submit workflow
  const handleSubmit = useCallback(async () => {
    // Validate stages
    for (let i = 0; i < stages.length; i++) {
      const stage = stages[i];
      if (!stage.taskName) {
        showError(`Stage ${i + 1} must have a task name`);
        setActiveStep(i);
        return;
      }
    }

    setSubmitting(true);
    const taskIds: string[] = [];

    try {
      // Spawn tasks in sequence (lower priority = later execution)
      // Higher priority tasks will be claimed first
      for (const stage of stages) {
        const request: SpawnTaskRequest = {
          queue_name: queueName,
          task_name: stage.taskName,
          params: stage.params,
          priority: stage.priority,
          timeout_sec: stage.timeoutSec,
        };

        const taskId = await spawnMutation.mutateAsync(request);
        taskIds.push(taskId);
      }

      showSuccess(`Workflow submitted: ${taskIds.length} tasks created`);
      onWorkflowSubmitted?.(taskIds);

      // Reset workflow
      setStages([
        {
          id: Date.now().toString(),
          taskName: "convert-uvh5-to-ms",
          params: {},
          priority: 15,
        },
      ]);
      setActiveStep(0);
    } catch (error: any) {
      showError(`Failed to submit workflow: ${error.message}`);
    } finally {
      setSubmitting(false);
    }
  }, [stages, queueName, spawnMutation, showSuccess, showError, onWorkflowSubmitted]);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Workflow Builder
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Build multi-stage pipeline workflows. Tasks are executed in priority order (higher priority
        first).
      </Typography>

      {stages.length === 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Click "Add Stage" to start building your workflow.
        </Alert>
      )}

      <Stepper activeStep={activeStep} orientation="vertical">
        {stages.map((stage, index) => (
          <Step key={stage.id}>
            <StepLabel
              optional={
                <Chip
                  label={`Priority: ${stage.priority}`}
                  size="small"
                  sx={{
                    bgcolor:
                      stage.priority >= 15
                        ? theme.palette.error.main
                        : stage.priority >= 10
                          ? theme.palette.warning.main
                          : theme.palette.info.main,
                    color: "white",
                  }}
                />
              }
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Typography variant="h6">Stage {index + 1}</Typography>
                {stages.length > 1 && (
                  <IconButton size="small" color="error" onClick={() => handleRemoveStage(index)}>
                    <Delete fontSize="small" />
                  </IconButton>
                )}
              </Box>
            </StepLabel>
            <StepContent>
              <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Task Type</InputLabel>
                    <Select
                      value={stage.taskName}
                      onChange={(e) => {
                        const taskName = e.target.value;
                        handleUpdateStage(index, {
                          taskName,
                          priority: DEFAULT_PRIORITIES[taskName] || 5,
                        });
                      }}
                      label="Task Type"
                    >
                      {AVAILABLE_TASKS.map((task) => (
                        <MenuItem key={task.value} value={task.value}>
                          {task.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={3}>
                  <TextField
                    fullWidth
                    label="Priority"
                    type="number"
                    size="small"
                    value={stage.priority}
                    onChange={(e) =>
                      handleUpdateStage(index, {
                        priority: parseInt(e.target.value, 10) || 5,
                      })
                    }
                    inputProps={{ min: 1, max: 20 }}
                  />
                </Grid>

                <Grid item xs={12} sm={3}>
                  <TextField
                    fullWidth
                    label="Timeout (sec)"
                    type="number"
                    size="small"
                    value={stage.timeoutSec || ""}
                    onChange={(e) =>
                      handleUpdateStage(index, {
                        timeoutSec: e.target.value ? parseInt(e.target.value, 10) : undefined,
                      })
                    }
                    inputProps={{ min: 1 }}
                  />
                </Grid>

                {/* Task-specific parameters */}
                {stage.taskName === "convert-uvh5-to-ms" && (
                  <>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="Start Time"
                        size="small"
                        value={stage.params.start_time || ""}
                        onChange={(e) => handleUpdateParams(index, "start_time", e.target.value)}
                        placeholder="YYYY-MM-DD HH:MM:SS"
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="End Time"
                        size="small"
                        value={stage.params.end_time || ""}
                        onChange={(e) => handleUpdateParams(index, "end_time", e.target.value)}
                        placeholder="YYYY-MM-DD HH:MM:SS"
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="Input Directory"
                        size="small"
                        value={stage.params.input_dir || "/data/incoming"}
                        onChange={(e) => handleUpdateParams(index, "input_dir", e.target.value)}
                      />
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="Output Directory"
                        size="small"
                        value={stage.params.output_dir || "/stage/dsa110-contimg/ms"}
                        onChange={(e) => handleUpdateParams(index, "output_dir", e.target.value)}
                      />
                    </Grid>
                  </>
                )}

                {stage.taskName === "calibration-solve" && (
                  <>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="MS Path"
                        size="small"
                        value={stage.params.ms_path || ""}
                        onChange={(e) => handleUpdateParams(index, "ms_path", e.target.value)}
                        placeholder="/stage/dsa110-contimg/ms/science/..."
                      />
                    </Grid>
                  </>
                )}

                {stage.taskName === "imaging" && (
                  <>
                    <Grid item xs={12} sm={6}>
                      <TextField
                        fullWidth
                        label="MS Path"
                        size="small"
                        value={stage.params.ms_path || ""}
                        onChange={(e) => handleUpdateParams(index, "ms_path", e.target.value)}
                        placeholder="/stage/dsa110-contimg/ms/science/..."
                      />
                    </Grid>
                    <Grid item xs={12} sm={3}>
                      <TextField
                        fullWidth
                        label="Image Size"
                        type="number"
                        size="small"
                        value={stage.params.imsize || 2048}
                        onChange={(e) =>
                          handleUpdateParams(index, "imsize", parseInt(e.target.value, 10) || 2048)
                        }
                      />
                    </Grid>
                    <Grid item xs={12} sm={3}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Backend</InputLabel>
                        <Select
                          value={stage.params.backend || "wsclean"}
                          onChange={(e) => handleUpdateParams(index, "backend", e.target.value)}
                          label="Backend"
                        >
                          <MenuItem value="wsclean">WSClean</MenuItem>
                          <MenuItem value="tclean">CASA tclean</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                  </>
                )}

                {/* Generic params JSON editor */}
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Additional Parameters (JSON)"
                    size="small"
                    multiline
                    rows={3}
                    value={JSON.stringify(stage.params, null, 2)}
                    onChange={(e) => {
                      try {
                        const params = JSON.parse(e.target.value);
                        handleUpdateStage(index, { params });
                      } catch {
                        // Invalid JSON, ignore
                      }
                    }}
                    sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}
                  />
                </Grid>
              </Grid>

              {index < stages.length - 1 && (
                <Box sx={{ display: "flex", justifyContent: "center", my: 2 }}>
                  <ArrowDownward sx={{ color: theme.palette.text.secondary }} />
                </Box>
              )}
            </StepContent>
          </Step>
        ))}
      </Stepper>

      {/* Actions */}
      <Box sx={{ display: "flex", gap: 2, mt: 3 }}>
        <Button variant="outlined" startIcon={<Add />} onClick={handleAddStage}>
          Add Stage
        </Button>

        <Button
          variant="contained"
          startIcon={submitting ? <CircularProgress size={20} /> : <PlayArrow />}
          onClick={handleSubmit}
          disabled={submitting || stages.length === 0}
        >
          {submitting ? "Submitting..." : "Submit Workflow"}
        </Button>
      </Box>
    </Box>
  );
}
