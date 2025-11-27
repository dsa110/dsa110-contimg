/**
 * Pipeline Control Tab
 *
 * Main execution interface for pipeline workflows:
 * - MS selection table
 * - Conversion workflow
 * - Calibration workflow
 * - Imaging workflow
 * - Live operations monitoring
 */
import { useState } from "react";
import { Box, Stack } from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import { logger } from "../../utils/logger";
import type { MSListEntry } from "../../api/types";
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
  const [msMetadata, setMsMetadata] = useState<MSListEntry | null>(null);

  const handleMSSelectionChange = (paths: string[]) => {
    const newSelectedMS = computeSelectedMS(paths, selectedMSList, selectedMS);
    setSelectedMSList(paths);
    setSelectedMS(newSelectedMS);

    if (!newSelectedMS) {
      setMsMetadata(null);
    }
  };

  const handleMSRowClick = (row: MSListEntry) => {
    setSelectedMS(row.path);
    setMsMetadata(row);
    logger.info("Selected MS for details:", { path: row.path });
  };

  return (
    <Stack spacing={3}>
      {/* Main layout: MS Table + Details Panel */}
      <Grid container spacing={3}>
        <Grid item xs={12} lg={8}>
          <MSTable
            selectedMS={selectedMS}
            selectedMSList={selectedMSList}
            onSelectionChange={handleMSSelectionChange}
            onRowClick={handleMSRowClick}
          />
        </Grid>
        <Grid item xs={12} lg={4}>
          {msMetadata ? (
            <MSDetailsPanel msPath={selectedMS} metadata={msMetadata} />
          ) : (
            <Box sx={{ p: 3, textAlign: "center", color: "text.secondary" }}>
              Select a measurement set to view details
            </Box>
          )}
        </Grid>
      </Grid>

      {/* Workflow Controls */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6} lg={4}>
          <ConversionWorkflow />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <CalibrationWorkflow selectedMS={selectedMS} selectedMSList={selectedMSList} />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <ImagingWorkflow selectedMS={selectedMS} />
        </Grid>
      </Grid>

      {/* Workflow Templates & Live Operations */}
      <Grid container spacing={3}>
        <Grid item xs={12} lg={6}>
          <WorkflowTemplates />
        </Grid>
        <Grid item xs={12} lg={6}>
          <LiveOperationsCard />
        </Grid>
      </Grid>
    </Stack>
  );
}
