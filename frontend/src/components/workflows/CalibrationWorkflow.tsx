/**
 * Calibration Workflow Component
 * Handles calibration table generation and application
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
  RadioGroup,
  Radio,
  Divider,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip,
  CircularProgress,
  Chip,
  Tabs,
  Tab,
  useTheme,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { PlayArrow, ExpandMore } from "@mui/icons-material";
import {
  useCreateCalibrateJob,
  useCreateApplyJob,
  useExistingCalTables,
  useCalTables,
  useValidateCalTable,
  useCalibrationQA,
  useMSMetadata,
} from "../../api/queries";
import { useNotifications } from "../../contexts/NotificationContext";
import { CalibrationSPWPanel } from "../CalibrationSPWPanel";
import CalibrationQAPanel from "../CalibrationQAPanel";
import { ValidatedTextField } from "../ValidatedTextField";
import { validationRules } from "../../utils/formValidation";
import type { CalibrateJobParams, JobParams } from "../../api/types";

interface CalibrationWorkflowProps {
  selectedMS: string;
  selectedMSList: string[];
  onJobCreated?: (jobId: number) => void;
  onRefreshJobs?: () => void;
}

export function CalibrationWorkflow({
  selectedMS,
  selectedMSList,
  onJobCreated,
  onRefreshJobs,
}: CalibrationWorkflowProps) {
  const theme = useTheme();
  const { showError, showSuccess } = useNotifications();
  const [activeTab, setActiveTab] = useState(0); // 0 = Calibrate, 1 = Apply

  // Calibration parameters state
  const [calibParams, setCalibParams] = useState<CalibrateJobParams>({
    field: "",
    refant: "103",
    solve_delay: true,
    solve_bandpass: true,
    solve_gains: true,
    gain_solint: "inf",
    gain_calmode: "ap",
    auto_fields: true,
    min_pb: 0.5,
    do_flagging: false,
    use_existing_tables: "auto",
    existing_k_table: undefined,
    existing_bp_table: undefined,
    existing_g_table: undefined,
  });

  // Apply parameters state
  const [applyParams, setApplyParams] = useState<JobParams>({
    gaintables: [],
  });

  // Compatibility checks state
  const [compatibilityChecks, setCompatibilityChecks] = useState<
    Record<
      string,
      {
        is_compatible: boolean;
        issues: string[];
        warnings: string[];
      }
    >
  >({});

  // Queries and mutations
  const calibrateMutation = useCreateCalibrateJob();
  const applyMutation = useCreateApplyJob();
  const { data: existingTables } = useExistingCalTables(selectedMS);
  const { data: calTables } = useCalTables();
  const validateCalTable = useValidateCalTable();
  const { data: _calibrationQA } = useCalibrationQA(selectedMS);
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

  // Calibration submit handler
  const handleCalibrateSubmit = useCallback(() => {
    if (!selectedMS) return;
    calibrateMutation.mutate(
      { params: calibParams },
      {
        onSuccess: (job) => {
          onJobCreated?.(parseInt(job.id, 10));
          onRefreshJobs?.();
          showSuccess(`Calibration job #${job.id} started successfully`);
        },
        onError: (error: unknown) => {
          const message = `Calibration failed: ${getErrorMessage(error)}`;
          showError(message);
        },
      }
    );
  }, [
    selectedMS,
    calibParams,
    calibrateMutation,
    onJobCreated,
    onRefreshJobs,
    showError,
    showSuccess,
  ]);

  // Apply submit handler
  const handleApplySubmit = useCallback(() => {
    if (!selectedMS) return;
    applyMutation.mutate(
      { ms_path: selectedMS, params: applyParams },
      {
        onSuccess: (job) => {
          onJobCreated?.(job.id);
          onRefreshJobs?.();
          showSuccess(`Apply calibration job #${job.id} started successfully`);
        },
        onError: (error: unknown) => {
          const message = `Apply calibration failed: ${getErrorMessage(error)}`;
          showError(message);
        },
      }
    );
  }, [selectedMS, applyParams, applyMutation, onJobCreated, onRefreshJobs, showError, showSuccess]);

  return (
    <Box>
      <Paper sx={{ p: 2 }}>
        <Tabs value={activeTab} onChange={(_, val) => setActiveTab(val)}>
          <Tab label="Calibrate" />
          <Tab label="Apply" />
        </Tabs>

        {/* Calibrate Tab */}
        {activeTab === 0 && (
          <Box sx={{ mt: 2 }}>
            {!selectedMS && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                Please select an MS from the table above to calibrate.
              </Alert>
            )}
            {selectedMS && selectedMSList.length > 1 && (
              <Alert severity="error" sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ fontWeight: "bold", mb: 1 }}>
                  Multiple MSs selected ({selectedMSList.length})
                </Typography>
                <Typography variant="body2">
                  Only one MS can be calibrated at a time. Please deselect other MSs, keeping only
                  one selected.
                </Typography>
              </Alert>
            )}
            {selectedMS && selectedMSList.length === 1 && (
              <Alert severity="success" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  Selected MS: <strong>{selectedMS.split("/").pop()}</strong>
                </Typography>
                {msMetadata && msMetadata.start_time && (
                  <Typography variant="caption" sx={{ display: "block", mt: 0.5 }}>
                    Time range: {msMetadata.start_time} → {msMetadata.end_time}
                  </Typography>
                )}
              </Alert>
            )}
            <Typography variant="body2" sx={{ mb: 2, color: "text.secondary" }}>
              Generates calibration tables from a calibrator observation:
            </Typography>

            <Typography variant="subtitle2" gutterBottom>
              Calibration Tables to Generate
            </Typography>
            <Box sx={{ mb: 2 }}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={calibParams.solve_delay}
                    onChange={(e) =>
                      setCalibParams({
                        ...calibParams,
                        solve_delay: e.target.checked,
                      })
                    }
                  />
                }
                label={
                  <Box>
                    <Typography variant="body2">K (Delay calibration)</Typography>
                    <Typography variant="caption" sx={{ color: "text.secondary" }}>
                      Antenna-based delays
                    </Typography>
                  </Box>
                }
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={calibParams.solve_bandpass}
                    onChange={(e) =>
                      setCalibParams({
                        ...calibParams,
                        solve_bandpass: e.target.checked,
                      })
                    }
                  />
                }
                label={
                  <Box>
                    <Typography variant="body2">BP (Bandpass calibration)</Typography>
                    <Typography variant="caption" sx={{ color: "text.secondary" }}>
                      Frequency response per antenna
                    </Typography>
                  </Box>
                }
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={calibParams.solve_gains}
                    onChange={(e) =>
                      setCalibParams({
                        ...calibParams,
                        solve_gains: e.target.checked,
                      })
                    }
                  />
                }
                label={
                  <Box>
                    <Typography variant="body2">G (Gain calibration)</Typography>
                    <Typography variant="caption" sx={{ color: "text.secondary" }}>
                      Time-variable complex gains
                    </Typography>
                  </Box>
                }
              />
            </Box>

            <Typography variant="subtitle2" gutterBottom>
              Basic Parameters
            </Typography>
            <ValidatedTextField
              fullWidth
              label="Field ID"
              value={calibParams.field || ""}
              onChange={(e) => setCalibParams({ ...calibParams, field: e.target.value })}
              sx={{ mb: 2 }}
              size="small"
              helperText="Leave empty for auto-detect from catalog"
              validationRules={[
                {
                  validate: (value: string) => {
                    // Optional field - if provided, should be numeric or valid field name
                    if (!value.trim()) return true;
                    return /^[0-9]+$/.test(value.trim()) || /^[a-zA-Z0-9_-]+$/.test(value.trim());
                  },
                  message: "Field ID must be numeric or alphanumeric",
                },
              ]}
            />
            {selectedMS && (
              <>
                {!msMetadata || !msMetadata.antennas || msMetadata.antennas.length === 0 ? (
                  <TextField
                    fullWidth
                    label="Reference Antenna"
                    value={calibParams.refant || ""}
                    onChange={(e) =>
                      setCalibParams({
                        ...calibParams,
                        refant: e.target.value,
                      })
                    }
                    sx={{ mb: 2 }}
                    size="small"
                    helperText="Reference antenna ID (e.g., 103)"
                  />
                ) : (
                  (() => {
                    const refantValid =
                      !calibParams.refant ||
                      msMetadata.antennas.some(
                        (a) =>
                          String(a.antenna_id) === calibParams.refant ||
                          a.name === calibParams.refant
                      );

                    return (
                      <FormControl fullWidth sx={{ mb: 2 }} size="small">
                        <InputLabel>Reference Antenna</InputLabel>
                        <Select
                          value={calibParams.refant || ""}
                          onChange={(e) =>
                            setCalibParams({
                              ...calibParams,
                              refant: e.target.value,
                            })
                          }
                          label="Reference Antenna"
                          error={!refantValid}
                        >
                          {msMetadata.antennas.map((ant) => (
                            <MenuItem key={ant.antenna_id} value={String(ant.antenna_id)}>
                              {ant.name} ({ant.antenna_id})
                            </MenuItem>
                          ))}
                        </Select>
                        {!refantValid && calibParams.refant && (
                          <Typography
                            variant="caption"
                            sx={{
                              color: "error.main",
                              mt: 0.5,
                              display: "block",
                            }}
                          >
                            Warning: Antenna "{calibParams.refant}" not found in MS
                          </Typography>
                        )}
                        {refantValid && (
                          <Typography
                            variant="caption"
                            sx={{
                              color: "text.secondary",
                              mt: 0.5,
                              display: "block",
                            }}
                          >
                            Select reference antenna from {msMetadata.antennas.length} available
                            antennas
                          </Typography>
                        )}
                      </FormControl>
                    );
                  })()
                )}
              </>
            )}

            <Divider sx={{ my: 2 }} />

            {/* Existing Tables Section */}
            <Typography variant="subtitle2" gutterBottom>
              Existing Calibration Tables
            </Typography>

            {selectedMS && !existingTables && (
              <Box
                sx={{
                  mb: 2,
                  p: 1.5,
                  bgcolor: alpha(theme.palette.background.paper, 0.5),
                  borderRadius: 1,
                }}
              >
                <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                  Loading existing tables...
                </Typography>
              </Box>
            )}
            {selectedMS &&
              existingTables &&
              !existingTables.has_k &&
              !existingTables.has_bp &&
              !existingTables.has_g && (
                <Box
                  sx={{
                    mb: 2,
                    p: 1.5,
                    bgcolor: alpha(theme.palette.background.paper, 0.5),
                    borderRadius: 1,
                  }}
                >
                  <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                    No existing calibration tables found for this MS
                  </Typography>
                </Box>
              )}
            {selectedMS &&
              existingTables &&
              (existingTables.has_k || existingTables.has_bp || existingTables.has_g) && (
                <Box sx={{ mb: 2 }}>
                  <RadioGroup
                    value={calibParams.use_existing_tables || "auto"}
                    onChange={(e) =>
                      setCalibParams({
                        ...calibParams,
                        use_existing_tables: e.target.value as "auto" | "manual" | "none",
                      })
                    }
                  >
                    <FormControlLabel
                      value="auto"
                      control={<Radio size="small" />}
                      label="Auto-select (use latest)"
                    />
                    <FormControlLabel
                      value="manual"
                      control={<Radio size="small" />}
                      label="Manual select"
                    />
                    <FormControlLabel
                      value="none"
                      control={<Radio size="small" />}
                      label="Don't use existing tables"
                    />
                  </RadioGroup>

                  {calibParams.use_existing_tables === "auto" && (
                    <Box
                      sx={{
                        mt: 1,
                        p: 1.5,
                        bgcolor: alpha(theme.palette.background.paper, 0.5),
                        borderRadius: 1,
                      }}
                    >
                      <Typography variant="caption" sx={{ color: theme.palette.text.secondary }}>
                        Will automatically use the latest compatible tables
                      </Typography>
                    </Box>
                  )}

                  {calibParams.use_existing_tables === "manual" && existingTables && (
                    <Box sx={{ mt: 2 }}>
                      {existingTables.k_tables && existingTables.k_tables.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="caption" sx={{ fontWeight: "bold" }}>
                            K (Delay) Tables:
                          </Typography>
                          <RadioGroup
                            value={calibParams.existing_k_table || "none"}
                            onChange={(e) => {
                              const newValue =
                                e.target.value === "none" ? undefined : e.target.value;
                              setCalibParams({
                                ...calibParams,
                                existing_k_table: newValue,
                              });

                              if (newValue && selectedMS) {
                                validateCalTable.mutate(
                                  {
                                    msPath: selectedMS,
                                    caltablePath: newValue,
                                  },
                                  {
                                    onSuccess: (result) => {
                                      setCompatibilityChecks((prev) => ({
                                        ...prev,
                                        [newValue]: result,
                                      }));
                                    },
                                  }
                                );
                              }
                            }}
                          >
                            {existingTables.k_tables.map((table) => {
                              const compat = compatibilityChecks[table.path];
                              const isSelected = calibParams.existing_k_table === table.path;

                              return (
                                <Box key={table.path}>
                                  <FormControlLabel
                                    value={table.path}
                                    control={<Radio size="small" />}
                                    label={
                                      <Box>
                                        <Typography variant="caption">
                                          {table.filename} ({(table.size_mb ?? 0).toFixed(1)} MB,{" "}
                                          {table.age_hours?.toFixed(1)}h ago)
                                        </Typography>
                                        {isSelected && compat && (
                                          <Box sx={{ mt: 0.5 }}>
                                            {compat.is_compatible ? (
                                              <Chip
                                                label="✓ Compatible"
                                                size="small"
                                                color="success"
                                                sx={{ height: 16, fontSize: "0.6rem" }}
                                              />
                                            ) : (
                                              <Chip
                                                label="✗ Incompatible"
                                                size="small"
                                                color="error"
                                                sx={{ height: 16, fontSize: "0.6rem" }}
                                              />
                                            )}
                                          </Box>
                                        )}
                                      </Box>
                                    }
                                  />
                                  {isSelected && compat && (
                                    <Box sx={{ ml: 4, mb: 1 }}>
                                      {compat.issues.length > 0 && (
                                        <Box sx={{ mt: 0.5 }}>
                                          {compat.issues.map((issue: string, idx: number) => (
                                            <Typography
                                              key={idx}
                                              variant="caption"
                                              sx={{
                                                color: "error.main",
                                                display: "block",
                                                fontSize: "0.65rem",
                                              }}
                                            >
                                              ⚠ {issue}
                                            </Typography>
                                          ))}
                                        </Box>
                                      )}
                                      {compat.warnings.length > 0 && (
                                        <Box sx={{ mt: 0.5 }}>
                                          {compat.warnings.map((warning: string, idx: number) => (
                                            <Typography
                                              key={idx}
                                              variant="caption"
                                              sx={{
                                                color: "warning.main",
                                                display: "block",
                                                fontSize: "0.65rem",
                                              }}
                                            >
                                              ⚠ {warning}
                                            </Typography>
                                          ))}
                                        </Box>
                                      )}
                                      {compat.is_compatible &&
                                        compat.issues.length === 0 &&
                                        compat.warnings.length === 0 && (
                                          <Typography
                                            variant="caption"
                                            sx={{
                                              color: "success.main",
                                              display: "block",
                                              fontSize: "0.65rem",
                                            }}
                                          >
                                            ✓ All compatibility checks passed
                                          </Typography>
                                        )}
                                    </Box>
                                  )}
                                </Box>
                              );
                            })}
                            <FormControlLabel
                              value="none"
                              control={<Radio size="small" />}
                              label={<Typography variant="caption">None</Typography>}
                            />
                          </RadioGroup>
                        </Box>
                      )}

                      {existingTables.bp_tables && existingTables.bp_tables.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="caption" sx={{ fontWeight: "bold" }}>
                            BP (Bandpass) Tables:
                          </Typography>
                          <RadioGroup
                            value={calibParams.existing_bp_table || "none"}
                            onChange={(e) => {
                              const newValue =
                                e.target.value === "none" ? undefined : e.target.value;
                              setCalibParams({
                                ...calibParams,
                                existing_bp_table: newValue,
                              });

                              if (newValue && selectedMS) {
                                validateCalTable.mutate(
                                  {
                                    msPath: selectedMS,
                                    caltablePath: newValue,
                                  },
                                  {
                                    onSuccess: (result) => {
                                      setCompatibilityChecks((prev) => ({
                                        ...prev,
                                        [newValue]: result,
                                      }));
                                    },
                                  }
                                );
                              }
                            }}
                          >
                            {existingTables.bp_tables.map((table) => {
                              const compat = compatibilityChecks[table.path];
                              const isSelected = calibParams.existing_bp_table === table.path;

                              return (
                                <Box key={table.path}>
                                  <FormControlLabel
                                    value={table.path}
                                    control={<Radio size="small" />}
                                    label={
                                      <Box>
                                        <Typography variant="caption">
                                          {table.filename} ({(table.size_mb ?? 0).toFixed(1)} MB,{" "}
                                          {table.age_hours?.toFixed(1)}h ago)
                                        </Typography>
                                        {isSelected && compat && (
                                          <Box sx={{ mt: 0.5 }}>
                                            {compat.is_compatible ? (
                                              <Chip
                                                label="✓ Compatible"
                                                size="small"
                                                color="success"
                                                sx={{ height: 16, fontSize: "0.6rem" }}
                                              />
                                            ) : (
                                              <Chip
                                                label="✗ Incompatible"
                                                size="small"
                                                color="error"
                                                sx={{ height: 16, fontSize: "0.6rem" }}
                                              />
                                            )}
                                          </Box>
                                        )}
                                      </Box>
                                    }
                                  />
                                  {isSelected && compat && (
                                    <Box sx={{ ml: 4, mb: 1 }}>
                                      {compat.issues.length > 0 && (
                                        <Box sx={{ mt: 0.5 }}>
                                          {compat.issues.map((issue: string, idx: number) => (
                                            <Typography
                                              key={idx}
                                              variant="caption"
                                              sx={{
                                                color: "error.main",
                                                display: "block",
                                                fontSize: "0.65rem",
                                              }}
                                            >
                                              ⚠ {issue}
                                            </Typography>
                                          ))}
                                        </Box>
                                      )}
                                      {compat.warnings.length > 0 && (
                                        <Box sx={{ mt: 0.5 }}>
                                          {compat.warnings.map((warning: string, idx: number) => (
                                            <Typography
                                              key={idx}
                                              variant="caption"
                                              sx={{
                                                color: "warning.main",
                                                display: "block",
                                                fontSize: "0.65rem",
                                              }}
                                            >
                                              ⚠ {warning}
                                            </Typography>
                                          ))}
                                        </Box>
                                      )}
                                      {compat.is_compatible &&
                                        compat.issues.length === 0 &&
                                        compat.warnings.length === 0 && (
                                          <Typography
                                            variant="caption"
                                            sx={{
                                              color: "success.main",
                                              display: "block",
                                              fontSize: "0.65rem",
                                            }}
                                          >
                                            ✓ All compatibility checks passed
                                          </Typography>
                                        )}
                                    </Box>
                                  )}
                                </Box>
                              );
                            })}
                            <FormControlLabel
                              value="none"
                              control={<Radio size="small" />}
                              label={<Typography variant="caption">None</Typography>}
                            />
                          </RadioGroup>
                        </Box>
                      )}

                      {existingTables.g_tables && existingTables.g_tables.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="caption" sx={{ fontWeight: "bold" }}>
                            G (Gain) Tables:
                          </Typography>
                          <RadioGroup
                            value={calibParams.existing_g_table || "none"}
                            onChange={(e) => {
                              const newValue =
                                e.target.value === "none" ? undefined : e.target.value;
                              setCalibParams({
                                ...calibParams,
                                existing_g_table: newValue,
                              });

                              if (newValue && selectedMS) {
                                validateCalTable.mutate(
                                  {
                                    msPath: selectedMS,
                                    caltablePath: newValue,
                                  },
                                  {
                                    onSuccess: (result) => {
                                      setCompatibilityChecks((prev) => ({
                                        ...prev,
                                        [newValue]: result,
                                      }));
                                    },
                                  }
                                );
                              }
                            }}
                          >
                            {existingTables.g_tables.map((table) => {
                              const compat = compatibilityChecks[table.path];
                              const isSelected = calibParams.existing_g_table === table.path;

                              return (
                                <Box key={table.path}>
                                  <FormControlLabel
                                    value={table.path}
                                    control={<Radio size="small" />}
                                    label={
                                      <Box>
                                        <Typography variant="caption">
                                          {table.filename} ({(table.size_mb ?? 0).toFixed(1)} MB,{" "}
                                          {table.age_hours?.toFixed(1)}h ago)
                                        </Typography>
                                        {isSelected && compat && (
                                          <Box sx={{ mt: 0.5 }}>
                                            {compat.is_compatible ? (
                                              <Chip
                                                label="✓ Compatible"
                                                size="small"
                                                color="success"
                                                sx={{ height: 16, fontSize: "0.6rem" }}
                                              />
                                            ) : (
                                              <Chip
                                                label="✗ Incompatible"
                                                size="small"
                                                color="error"
                                                sx={{ height: 16, fontSize: "0.6rem" }}
                                              />
                                            )}
                                          </Box>
                                        )}
                                      </Box>
                                    }
                                  />
                                  {isSelected && compat && (
                                    <Box sx={{ ml: 4, mb: 1 }}>
                                      {compat.issues.length > 0 && (
                                        <Box sx={{ mt: 0.5 }}>
                                          {compat.issues.map((issue: string, idx: number) => (
                                            <Typography
                                              key={idx}
                                              variant="caption"
                                              sx={{
                                                color: "error.main",
                                                display: "block",
                                                fontSize: "0.65rem",
                                              }}
                                            >
                                              ⚠ {issue}
                                            </Typography>
                                          ))}
                                        </Box>
                                      )}
                                      {compat.warnings.length > 0 && (
                                        <Box sx={{ mt: 0.5 }}>
                                          {compat.warnings.map((warning: string, idx: number) => (
                                            <Typography
                                              key={idx}
                                              variant="caption"
                                              sx={{
                                                color: "warning.main",
                                                display: "block",
                                                fontSize: "0.65rem",
                                              }}
                                            >
                                              ⚠ {warning}
                                            </Typography>
                                          ))}
                                        </Box>
                                      )}
                                      {compat.is_compatible &&
                                        compat.issues.length === 0 &&
                                        compat.warnings.length === 0 && (
                                          <Typography
                                            variant="caption"
                                            sx={{
                                              color: "success.main",
                                              display: "block",
                                              fontSize: "0.65rem",
                                            }}
                                          >
                                            ✓ All compatibility checks passed
                                          </Typography>
                                        )}
                                    </Box>
                                  )}
                                </Box>
                              );
                            })}
                            <FormControlLabel
                              value="none"
                              control={<Radio size="small" />}
                              label={<Typography variant="caption">None</Typography>}
                            />
                          </RadioGroup>
                        </Box>
                      )}
                    </Box>
                  )}
                </Box>
              )}

            <Divider sx={{ my: 2 }} />

            <Accordion sx={{ mb: 2 }}>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="subtitle2">Advanced Options</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <ValidatedTextField
                  fullWidth
                  label="Gain Solution Interval"
                  value={calibParams.gain_solint || "inf"}
                  onChange={(e) =>
                    setCalibParams({
                      ...calibParams,
                      gain_solint: e.target.value,
                    })
                  }
                  sx={{ mb: 2 }}
                  size="small"
                  helperText="e.g., 'inf', '60s', '10min'"
                  validationRules={[
                    {
                      validate: (value: string) => {
                        if (!value) return false;
                        const lower = value.toLowerCase();
                        // Allow "inf" or time format like "60s", "10min", "1h", etc.
                        return (
                          lower === "inf" ||
                          /^\d+[smhd]$/i.test(value) ||
                          /^\d+\.\d+[smhd]$/i.test(value)
                        );
                      },
                      message: "Must be 'inf' or time format (e.g., '60s', '10min', '1h')",
                    },
                  ]}
                />
                <FormControl fullWidth sx={{ mb: 2 }} size="small">
                  <InputLabel>Gain Cal Mode</InputLabel>
                  <Select
                    value={calibParams.gain_calmode || "ap"}
                    onChange={(e) =>
                      setCalibParams({
                        ...calibParams,
                        gain_calmode: e.target.value as "ap" | "p" | "a",
                      })
                    }
                    label="Gain Cal Mode"
                  >
                    <MenuItem value="ap">Amp + Phase</MenuItem>
                    <MenuItem value="p">Phase only</MenuItem>
                    <MenuItem value="a">Amp only</MenuItem>
                  </Select>
                </FormControl>
                <ValidatedTextField
                  fullWidth
                  label="Minimum PB Response"
                  type="number"
                  value={String(calibParams.min_pb || 0.5)}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value);
                    if (!isNaN(val) && val >= 0 && val <= 1) {
                      setCalibParams({ ...calibParams, min_pb: val });
                    }
                  }}
                  sx={{ mb: 2 }}
                  size="small"
                  helperText="0.0 - 1.0 (higher = stricter field selection)"
                  inputProps={{ min: 0, max: 1, step: 0.1 }}
                  validationRules={[
                    validationRules.number("Must be a number"),
                    validationRules.range(0, 1, "Must be between 0.0 and 1.0"),
                  ]}
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={calibParams.do_flagging || false}
                      onChange={(e) =>
                        setCalibParams({
                          ...calibParams,
                          do_flagging: e.target.checked,
                        })
                      }
                    />
                  }
                  label="Enable pre-calibration flagging"
                />
              </AccordionDetails>
            </Accordion>

            {selectedMS && (
              <>
                <CalibrationSPWPanel
                  msPath={selectedMS}
                  onSPWChange={(_spwList: any) => {
                    // Handle SPW selection if needed
                  }}
                />
                <Box sx={{ mt: 2 }}>
                  <CalibrationQAPanel msPath={selectedMS || null} />
                </Box>
              </>
            )}

            <Tooltip
              title={
                !selectedMS
                  ? "Select a measurement set first"
                  : selectedMSList.length !== 1
                    ? "Only one MS can be calibrated at a time"
                    : !calibParams.solve_delay &&
                        !calibParams.solve_bandpass &&
                        !calibParams.solve_gains
                      ? "Select at least one calibration table to generate"
                      : calibrateMutation.isPending
                        ? "Calibration job in progress..."
                        : "Run calibration (Ctrl/Cmd + Enter)"
              }
            >
              <span>
                <Button
                  variant="contained"
                  startIcon={
                    calibrateMutation.isPending ? (
                      <CircularProgress size={20} color="inherit" />
                    ) : (
                      <PlayArrow />
                    )
                  }
                  onClick={handleCalibrateSubmit}
                  disabled={
                    !selectedMS ||
                    selectedMSList.length !== 1 ||
                    (!calibParams.solve_delay &&
                      !calibParams.solve_bandpass &&
                      !calibParams.solve_gains) ||
                    calibrateMutation.isPending
                  }
                  fullWidth
                  sx={{ mt: 2 }}
                >
                  {calibrateMutation.isPending ? "Running..." : "Run Calibration"}
                </Button>
              </span>
            </Tooltip>
          </Box>
        )}

        {/* Apply Tab */}
        {activeTab === 1 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" sx={{ mb: 2, color: "text.secondary" }}>
              Apply existing calibration tables to the selected MS:
            </Typography>
            <Box
              sx={{
                mb: 2,
                p: 1.5,
                bgcolor: alpha(theme.palette.background.paper, 0.5),
                borderRadius: 1,
                fontFamily: "monospace",
                fontSize: "0.75rem",
                color: theme.palette.text.primary,
              }}
            >
              <Box>
                Clears existing calibration, then applies K, BP, and G tables to CORRECTED_DATA
                column
              </Box>
            </Box>

            <Typography variant="subtitle2" gutterBottom>
              Calibration Tables
            </Typography>
            <TextField
              fullWidth
              label="Gaintables (comma-separated paths)"
              value={applyParams.gaintables?.join(",") || ""}
              onChange={(e) =>
                setApplyParams({
                  ...applyParams,
                  gaintables: e.target.value
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean),
                })
              }
              multiline
              rows={3}
              sx={{ mb: 2 }}
              size="small"
              helperText="Enter full paths to .kcal, .bpcal, .gpcal tables"
            />

            {/* Cal Table Browser */}
            {calTables && calTables.items.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Available Calibration Tables (click to add)
                </Typography>
                <Box
                  sx={{
                    maxHeight: 200,
                    overflow: "auto",
                    border: `1px solid ${theme.palette.divider}`,
                    borderRadius: 1,
                    p: 1,
                  }}
                >
                  {calTables.items.map((table) => (
                    <Box
                      key={table.path}
                      onClick={() => {
                        const current = applyParams.gaintables || [];
                        if (!current.includes(table.path)) {
                          setApplyParams({
                            ...applyParams,
                            gaintables: [...current, table.path],
                          });
                        }
                      }}
                      sx={{
                        p: 0.5,
                        mb: 0.5,
                        bgcolor: alpha(theme.palette.background.paper, 0.5),
                        borderRadius: 1,
                        cursor: "pointer",
                        fontSize: "0.75rem",
                        fontFamily: "monospace",
                        "&:hover": { bgcolor: alpha(theme.palette.action.hover, 0.1) },
                      }}
                    >
                      <Chip
                        label={table.table_type}
                        size="small"
                        sx={{ mr: 1, height: 18, fontSize: "0.65rem" }}
                      />
                      {table.filename} ({(table.size_mb ?? 0).toFixed(1)} MB)
                    </Box>
                  ))}
                </Box>
              </Box>
            )}

            <Tooltip
              title={
                !selectedMS
                  ? "Select a measurement set first"
                  : !applyParams.gaintables?.length
                    ? "Enter at least one calibration table path"
                    : applyMutation.isPending
                      ? "Apply calibration job in progress..."
                      : "Apply calibration tables (Ctrl/Cmd + Enter)"
              }
            >
              <span>
                <Button
                  variant="contained"
                  startIcon={
                    applyMutation.isPending ? (
                      <CircularProgress size={20} color="inherit" />
                    ) : (
                      <PlayArrow />
                    )
                  }
                  onClick={handleApplySubmit}
                  disabled={
                    !selectedMS || !applyParams.gaintables?.length || applyMutation.isPending
                  }
                  fullWidth
                >
                  {applyMutation.isPending ? "Running..." : "Apply Calibration"}
                </Button>
              </span>
            </Tooltip>
          </Box>
        )}
      </Paper>
    </Box>
  );
}
