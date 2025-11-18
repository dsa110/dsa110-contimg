/**
 * Calibration Workflow Page
 * Dedicated page for CASA-style calibration workflow:
 * 1. Inspect data quality
 * 2. Generate calibration tables
 * 3. Inspect calibration solutions
 * 4. Apply calibration
 * 5. Verify calibrated data
 */
import React, { useState } from "react";
import {
  Container,
  Typography,
  Box,
  Paper,
  Grid,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Button,
  Alert,
  Tabs,
  Tab,
  Stack,
} from "@mui/material";
import {
  CheckCircle,
  Visibility,
  Build,
  PlayArrow,
  Assessment,
  Settings,
} from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { useMSList, useMSMetadata, useCalibrationQA, useBandpassPlots } from "../api/queries";
import MSTable from "../components/MSTable";
import CalibrationQAPanel from "../components/CalibrationQAPanel";
import { CalibrationSPWPanel } from "../components/CalibrationSPWPanel";
import { CalibrationWorkflow } from "../components/workflows/CalibrationWorkflow";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import type { MSListEntry } from "../api/types";

const CALIBRATION_STEPS = [
  {
    label: "Select MS",
    description: "Choose a Measurement Set to calibrate",
    icon: <Visibility />,
  },
  {
    label: "Inspect Data Quality",
    description: "Review data quality metrics and flagging statistics",
    icon: <Assessment />,
  },
  {
    label: "Generate Calibration Tables",
    description: "Run gaincal, bandpass, and delay calibration",
    icon: <Build />,
  },
  {
    label: "Inspect Solutions",
    description: "Review calibration solutions and bandpass plots",
    icon: <CheckCircle />,
  },
  {
    label: "Apply Calibration",
    description: "Apply calibration tables to the MS",
    icon: <PlayArrow />,
  },
  {
    label: "Verify Calibrated Data",
    description: "Compare before/after calibration quality",
    icon: <Assessment />,
  },
];

export default function CalibrationWorkflowPage() {
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState(0);
  const [selectedMS, setSelectedMS] = useState<string>("");
  const [tabValue, setTabValue] = useState(0);

  const { data: msList, refetch: refetchMS } = useMSList({
    scan: String(true),
    scan_dir: "/stage/dsa110-contimg/ms",
  });
  const { data: msMetadata } = useMSMetadata(selectedMS);
  const { data: _calibrationQA } = useCalibrationQA(selectedMS);
  const { data: bandpassPlots } = useBandpassPlots(selectedMS);

  const handleStepChange = (step: number) => {
    if (step <= activeStep || (step === 1 && selectedMS)) {
      setActiveStep(step);
    }
  };

  const handleMSSelect = (ms: MSListEntry) => {
    setSelectedMS(ms.path);
    if (activeStep === 0) {
      setActiveStep(1);
    }
  };

  const handleNext = () => {
    if (activeStep < CALIBRATION_STEPS.length - 1) {
      setActiveStep(activeStep + 1);
    }
  };

  const _handleBack = () => {
    if (activeStep > 0) {
      setActiveStep(activeStep - 1);
    }
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <>
      <PageBreadcrumbs />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="h3" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
            Calibration Workflow
          </Typography>
          <Typography variant="body1" color="text.secondary">
            CASA-style calibration workflow: Inspect → Generate → Inspect → Apply → Verify
          </Typography>
        </Box>

        {/* Workflow Stepper */}
        <Paper sx={{ mb: 3 }}>
          <Box sx={{ p: 3 }}>
            <Stepper activeStep={activeStep} orientation="vertical">
              {CALIBRATION_STEPS.map((step, index) => (
                <Step key={step.label} completed={index < activeStep}>
                  <StepLabel
                    StepIconComponent={({ active, completed }) => (
                      <Box
                        sx={{
                          width: 40,
                          height: 40,
                          borderRadius: "50%",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          bgcolor: completed
                            ? "success.main"
                            : active
                              ? "primary.main"
                              : "action.disabledBackground",
                          color: completed || active ? "white" : "action.disabled",
                        }}
                      >
                        {completed ? <CheckCircle /> : step.icon}
                      </Box>
                    )}
                    onClick={() => handleStepChange(index)}
                    sx={{ cursor: index <= activeStep ? "pointer" : "default" }}
                  >
                    <Typography variant="h6">{step.label}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {step.description}
                    </Typography>
                  </StepLabel>
                  <StepContent>
                    <Box sx={{ mb: 2 }}>
                      {index === 0 && (
                        <Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Select a Measurement Set from the list below:
                          </Typography>
                          <MSTable
                            data={msList?.items || []}
                            total={msList?.total}
                            filtered={msList?.filtered?.length}
                            selected={selectedMS ? [selectedMS] : []}
                            onSelectionChange={(paths) => {
                              if (paths.length > 0) {
                                setSelectedMS(paths[0]);
                                handleNext();
                              }
                            }}
                            onMSClick={handleMSSelect}
                            onRefresh={refetchMS}
                          />
                          {selectedMS && (
                            <Alert severity="success" sx={{ mt: 2 }}>
                              Selected: <strong>{selectedMS.split("/").pop()}</strong>
                            </Alert>
                          )}
                        </Box>
                      )}

                      {index === 1 && selectedMS && (
                        <Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Review data quality metrics for the selected MS:
                          </Typography>
                          {msMetadata && (
                            <Grid container spacing={2}>
                              <Grid
                                size={{
                                  xs: 12,
                                  md: 6,
                                }}
                              >
                                <Paper sx={{ p: 2 }}>
                                  <Typography variant="subtitle2" gutterBottom>
                                    Time Range
                                  </Typography>
                                  <Typography variant="body2">
                                    {msMetadata.start_time} → {msMetadata.end_time}
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    Duration: {msMetadata.duration_sec?.toFixed(1)}s
                                  </Typography>
                                </Paper>
                              </Grid>
                              <Grid
                                size={{
                                  xs: 12,
                                  md: 6,
                                }}
                              >
                                <Paper sx={{ p: 2 }}>
                                  <Typography variant="subtitle2" gutterBottom>
                                    Frequency Coverage
                                  </Typography>
                                  <Typography variant="body2">
                                    {msMetadata.freq_min_ghz?.toFixed(3)} -{" "}
                                    {msMetadata.freq_max_ghz?.toFixed(3)} GHz
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary">
                                    {msMetadata.num_channels} channels
                                  </Typography>
                                </Paper>
                              </Grid>
                              <Grid size={12}>
                                <Paper sx={{ p: 2 }}>
                                  <Typography variant="subtitle2" gutterBottom>
                                    Flagging Statistics
                                  </Typography>
                                  {msMetadata.flagging_stats && (
                                    <Typography variant="body2">
                                      Total flagged:{" "}
                                      {(
                                        (msMetadata.flagging_stats.total_fraction ?? 0) * 100
                                      ).toFixed(1)}
                                      %
                                    </Typography>
                                  )}
                                </Paper>
                              </Grid>
                            </Grid>
                          )}
                          <Button variant="contained" onClick={handleNext} sx={{ mt: 2 }}>
                            Continue to Generate Calibration
                          </Button>
                        </Box>
                      )}

                      {index === 2 && selectedMS && (
                        <Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Configure and generate calibration tables:
                          </Typography>
                          <CalibrationWorkflow
                            selectedMS={selectedMS}
                            selectedMSList={[selectedMS]}
                            onJobCreated={(jobId) => {
                              // Navigate to job or show success
                              navigate(`/control?job=${jobId}`);
                            }}
                            onRefreshJobs={() => {}}
                          />
                        </Box>
                      )}

                      {index === 3 && selectedMS && (
                        <Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Inspect calibration solutions and quality:
                          </Typography>
                          <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 2 }}>
                            <Tab label="Quality Assessment" />
                            <Tab label="SPW Statistics" />
                            <Tab label="Bandpass Plots" />
                          </Tabs>
                          {tabValue === 0 && <CalibrationQAPanel msPath={selectedMS} />}
                          {tabValue === 1 && <CalibrationSPWPanel msPath={selectedMS} />}
                          {tabValue === 2 && (
                            <Box>
                              {bandpassPlots ? (
                                <Alert severity="info">
                                  Bandpass plots would be displayed here
                                </Alert>
                              ) : (
                                <Alert severity="warning">
                                  No bandpass plots available. Generate calibration tables first.
                                </Alert>
                              )}
                            </Box>
                          )}
                          <Button variant="contained" onClick={handleNext} sx={{ mt: 2 }}>
                            Continue to Apply Calibration
                          </Button>
                        </Box>
                      )}

                      {index === 4 && selectedMS && (
                        <Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Apply calibration tables to the MS:
                          </Typography>
                          <Alert severity="info" sx={{ mb: 2 }}>
                            Use the Apply Calibration section in the Control Panel to apply
                            calibration tables.
                          </Alert>
                          <Button
                            variant="contained"
                            onClick={() => {
                              navigate("/control");
                              // Could pass selectedMS as state
                            }}
                          >
                            Go to Control Panel
                          </Button>
                        </Box>
                      )}

                      {index === 5 && selectedMS && (
                        <Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Compare before/after calibration quality:
                          </Typography>
                          <CalibrationQAPanel msPath={selectedMS} />
                          <Alert severity="success" sx={{ mt: 2 }}>
                            Calibration workflow complete! Review the quality metrics above.
                          </Alert>
                        </Box>
                      )}
                    </Box>
                  </StepContent>
                </Step>
              ))}
            </Stepper>
          </Box>
        </Paper>

        {/* Quick Actions */}
        <Paper sx={{ p: 2 }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Typography variant="subtitle2">Quick Actions:</Typography>
            <Button
              variant="outlined"
              size="small"
              startIcon={<Settings />}
              onClick={() => navigate("/control")}
            >
              Control Panel
            </Button>
            <Button
              variant="outlined"
              size="small"
              startIcon={<Assessment />}
              onClick={() => navigate("/qa")}
            >
              QA Tools
            </Button>
            {selectedMS && (
              <Button
                variant="outlined"
                size="small"
                startIcon={<Visibility />}
                onClick={() => navigate(`/data/ms/${encodeURIComponent(selectedMS)}`)}
              >
                View MS Details
              </Button>
            )}
          </Stack>
        </Paper>
      </Container>
    </>
  );
}
