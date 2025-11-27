/**
 * Pipeline Calibration Tab
 *
 * Calibration workflow execution:
 * - Configuration form
 * - Progress monitoring
 * - Results review
 * - Calibration tables list
 */
import React, { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { Box, Tabs, Tab, Paper, Typography, Stack } from "@mui/material";
import { useCalibrationStatus, useStartCalibration, useStopCalibration } from "../../api/queries";
import { CalibrationConfigForm } from "../../components/Calibration/CalibrationConfigForm";
import { CalibrationMonitor } from "../../components/Calibration/CalibrationMonitor";
import { CalibrationReview } from "../../components/Calibration/CalibrationReview";
import { CalibrationTablesList } from "../../components/Calibration/CalibrationTablesList";
import type { CalibrationConfig } from "../../api/types";

const STEPS = ["Configure", "Monitor", "Review"];

interface TabPanelProps {
  children: React.ReactNode;
  value: number;
  index: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return (
    <Box
      role="tabpanel"
      hidden={value !== index}
      id={`calibration-tabpanel-${String(index)}`}
      aria-labelledby={`calibration-tab-${String(index)}`}
      sx={{ py: 2 }}
    >
      {value === index && children}
    </Box>
  );
}

export default function CalibrationTab() {
  const location = useLocation();
  const [activeStep, setActiveStep] = useState(0);
  const [config, setConfig] = useState<Partial<CalibrationConfig>>({});

  const { data: status } = useCalibrationStatus();
  const startCalibration = useStartCalibration();
  const stopCalibration = useStopCalibration();

  // Check URL for pre-selected MS
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const msPath = searchParams.get("ms");
    if (msPath) {
      setConfig((prev) => ({ ...prev, msPath }));
    }
  }, [location]);

  // Auto-advance to monitor step when calibration starts
  useEffect(() => {
    if (status?.status === "running" && activeStep === 0) {
      setActiveStep(1);
    } else if (status?.status === "completed" && activeStep === 1) {
      setActiveStep(2);
    }
  }, [status, activeStep]);

  const handleStart = (newConfig: CalibrationConfig) => {
    setConfig(newConfig);
    startCalibration.mutate(newConfig);
    setActiveStep(1);
  };

  const handleStop = () => {
    stopCalibration.mutate();
  };

  const handleReset = () => {
    setActiveStep(0);
    setConfig({});
  };

  return (
    <Stack spacing={3}>
      {/* Workflow Steps */}
      <Paper sx={{ p: 2 }}>
        <Tabs
          value={activeStep}
          onChange={(_, newValue: number) => {
            setActiveStep(newValue);
          }}
          aria-label="Calibration workflow steps"
        >
          {STEPS.map((label, index) => (
            <Tab
              key={label}
              label={label}
              id={`calibration-tab-${String(index)}`}
              aria-controls={`calibration-tabpanel-${String(index)}`}
            />
          ))}
        </Tabs>

        <TabPanel value={activeStep} index={0}>
          <CalibrationConfigForm
            initialValues={config}
            onSubmit={handleStart}
            isSubmitting={startCalibration.isPending}
          />
        </TabPanel>

        <TabPanel value={activeStep} index={1}>
          <CalibrationMonitor
            status={status ?? null}
            onStop={handleStop}
            onComplete={() => {
              setActiveStep(2);
            }}
          />
        </TabPanel>

        <TabPanel value={activeStep} index={2}>
          <CalibrationReview status={status ?? null} onReset={handleReset} />
        </TabPanel>
      </Paper>

      {/* Calibration Tables List */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Available Calibration Tables
        </Typography>
        <CalibrationTablesList />
      </Paper>
    </Stack>
  );
}
