import React, { useState, useEffect } from "react";
import {
  Container,
  Typography,
  Box,
  Paper,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  CircularProgress,
  Tabs,
  Tab,
} from "@mui/material";
import { useLocation } from "react-router-dom";
import { useCalibrationStatus, useStartCalibration, useStopCalibration } from "../api/queries";
import { CalibrationConfigForm } from "../components/Calibration/CalibrationConfigForm";
import { CalibrationMonitor } from "../components/Calibration/CalibrationMonitor";
import { CalibrationReview } from "../components/Calibration/CalibrationReview";
import { CalibrationTablesList } from "../components/Calibration/CalibrationTablesList";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import type { CalibrationConfig } from "../api/types";

const steps = [
  {
    label: "Configure Calibration",
    description: "Select measurement sets and calibration parameters",
  },
  {
    label: "Run Calibration",
    description: "Monitor calibration progress",
  },
  {
    label: "Review Results",
    description: "Review calibration tables and QA metrics",
  },
];

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`calibration-tabpanel-${index}`}
      aria-labelledby={`calibration-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export default function CalibrationWorkflowPage() {
  const location = useLocation();
  const [tabValue, setTabValue] = useState(0);
  const [activeStep, setActiveStep] = useState(0);
  const [config, setConfig] = useState<CalibrationConfig | null>(null);
  const [initialValues, setInitialValues] = useState<Partial<CalibrationConfig>>({});

  const { data: status, isLoading: statusLoading } = useCalibrationStatus();
  const startCalibration = useStartCalibration();
  const stopCalibration = useStopCalibration();

  // Handle template parameters from navigation state
  useEffect(() => {
    if (location.state?.template && location.state?.parameters) {
      const params = location.state.parameters;
      // Map template parameters to config form values
      // This mapping depends on how parameters are named in templates vs config form
      setInitialValues({
        // Example mapping - adjust based on actual parameter names
        msPath: params.ms_path || "",
        calibrator: params.calibrator || "",
        refAnt: params.refant || "",
      });
    }
  }, [location.state]);

  // Automatically advance to monitor step if running
  useEffect(() => {
    if (status?.status === "running" && activeStep === 0) {
      setActiveStep(1);
    }
  }, [status, activeStep]);

  const handleConfigSubmit = (newConfig: CalibrationConfig) => {
    setConfig(newConfig);
    startCalibration.mutate(newConfig);
    setActiveStep(1);
  };

  const handleStop = () => {
    stopCalibration.mutate();
  };

  const handleReset = () => {
    setActiveStep(0);
    setConfig(null);
  };

  const handleReview = () => {
    setActiveStep(2);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  if (statusLoading) {
    return (
      <Container maxWidth="xl" sx={{ py: 4, display: "flex", justifyContent: "center" }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <PageBreadcrumbs />
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Calibration
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Manage calibration workflows and view existing calibration products
        </Typography>
      </Box>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="calibration tabs">
          <Tab label="New Calibration" />
          <Tab label="Existing Tables" />
        </Tabs>

        <Box sx={{ p: 3 }}>
          <TabPanel value={tabValue} index={0}>
            <Stepper activeStep={activeStep} orientation="vertical">
              {steps.map((step, index) => (
                <Step key={step.label}>
                  <StepLabel>{step.label}</StepLabel>
                  <StepContent>
                    <Typography color="text.secondary" sx={{ mb: 2 }}>
                      {step.description}
                    </Typography>

                    {index === 0 && (
                      <CalibrationConfigForm
                        onSubmit={handleConfigSubmit}
                        isSubmitting={startCalibration.isPending}
                        initialValues={initialValues}
                      />
                    )}

                    {index === 1 && (
                      <CalibrationMonitor
                        status={status}
                        onStop={handleStop}
                        onComplete={handleReview}
                      />
                    )}

                    {index === 2 && <CalibrationReview status={status} onReset={handleReset} />}
                  </StepContent>
                </Step>
              ))}
            </Stepper>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <CalibrationTablesList />
          </TabPanel>
        </Box>
      </Paper>
    </Container>
  );
}
