/**
 * Pipeline Control Tab
 *
 * Main execution interface for pipeline workflows:
 * - MS selection table with filtering
 * - Conversion workflow
 * - Calibration workflow
 * - Imaging workflow
 * - Live operations monitoring
 */
import { useState } from "react";
import { Stack, Paper, Typography, Tabs, Tab } from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import { logger } from "../../utils/logger";
import type { MSListEntry } from "../../api/types";
import { useMSList, useMSMetadata, useJobs } from "../../api/queries";
import MSTable from "../../components/MSTable";
import { computeSelectedMS } from "../../utils/selectionLogic";
import { ConversionWorkflow } from "../../components/workflows/ConversionWorkflow";
import { CalibrationWorkflow } from "../../components/workflows/CalibrationWorkflow";
import { ImagingWorkflow } from "../../components/workflows/ImagingWorkflow";
import { WorkflowTemplates } from "../../components/workflows/WorkflowTemplates";
import { MSDetailsPanel } from "../../components/MSDetails";
import { LiveOperationsCard } from "../../components/Pipeline";

export default function ControlTab() {
  const [selectedMS, setSelectedMS] = useState("");
  const [selectedMSList, setSelectedMSList] = useState<string[]>([]);
  const [workflowTab, setWorkflowTab] = useState(0);

  // Queries
  const { data: msList, refetch: refetchMS } = useMSList({
    scan: String(true),
    scan_dir: "/stage/dsa110-contimg/ms",
  });
  const { data: msMetadata } = useMSMetadata(selectedMS || null);
  const { refetch: refetchJobs } = useJobs();

  const handleMSSelectionChange = (paths: string[]) => {
    const newSelectedMS = computeSelectedMS(paths, selectedMSList, selectedMS);
    setSelectedMSList(paths);
    setSelectedMS(newSelectedMS);
  };

  const handleMSClick = (ms: MSListEntry) => {
    setSelectedMS(ms.path);
    setSelectedMSList((prev) => {
      if (!prev.includes(ms.path)) {
        return [...prev, ms.path];
      }
      return prev;
    });
    logger.info("Selected MS for details:", { path: ms.path });
  };

  const handleMSSelectFromDetails = (ms: MSListEntry) => {
    setSelectedMS(ms.path);
    setSelectedMSList((prev) => {
      if (!prev.includes(ms.path)) {
        return [...prev, ms.path];
      }
      return prev;
    });
  };

  const handleJobCreated = (_jobId: number) => {
    void refetchJobs();
  };

  return (
    <Stack spacing={3}>
      {/* MS Selection & Details */}
      <Grid container spacing={3}>
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Measurement Sets
            </Typography>
            <MSTable
              data={msList?.items ?? []}
              total={msList?.total}
              filtered={msList?.filtered?.length}
              selected={selectedMSList}
              onSelectionChange={handleMSSelectionChange}
              onMSClick={handleMSClick}
              onRefresh={() => void refetchMS()}
            />
          </Paper>
        </Grid>
        <Grid item xs={12} lg={4}>
          <MSDetailsPanel
            selectedMS={selectedMS}
            metadata={msMetadata}
            onMSSelect={handleMSSelectFromDetails}
          />
        </Grid>
      </Grid>

      {/* Workflow Controls */}
      <Paper sx={{ p: 2 }}>
        <Tabs
          value={workflowTab}
          onChange={(_, val: number) => setWorkflowTab(val)}
          sx={{ mb: 2, borderBottom: 1, borderColor: "divider" }}
        >
          <Tab label="Templates" />
          <Tab label="Convert" />
          <Tab label="Calibrate" />
          <Tab label="Image" />
        </Tabs>

        {/* Templates Tab */}
        {workflowTab === 0 && (
          <WorkflowTemplates
            onTemplateSelect={(template) => {
              if (template.category === "calibration") {
                setWorkflowTab(2);
              } else if (template.category === "imaging") {
                setWorkflowTab(3);
              }
            }}
          />
        )}

        {/* Convert Tab */}
        {workflowTab === 1 && (
          <ConversionWorkflow
            selectedMS={selectedMS}
            onJobCreated={handleJobCreated}
            onRefreshJobs={() => void refetchJobs()}
          />
        )}

        {/* Calibrate Tab */}
        {workflowTab === 2 && (
          <CalibrationWorkflow
            selectedMS={selectedMS}
            selectedMSList={selectedMSList}
            onJobCreated={handleJobCreated}
            onRefreshJobs={() => void refetchJobs()}
          />
        )}

        {/* Image Tab */}
        {workflowTab === 3 && (
          <ImagingWorkflow
            selectedMS={selectedMS}
            onJobCreated={handleJobCreated}
            onRefreshJobs={() => void refetchJobs()}
          />
        )}
      </Paper>

      {/* Live Operations */}
      <LiveOperationsCard />
    </Stack>
  );
}
