/**
 * Control Page - Manual job execution interface
 * Refactored to use workflow components for better maintainability
 */
import React, { useState, useEffect } from "react";
import { Box, Paper, Typography, Tabs, Tab } from "@mui/material";
import {
  useMSList,
  useJobs,
  useMSMetadata,
  useCalibratorMatches,
  usePipelineMetricsSummary,
  useActivePipelineExecutions,
} from "../api/queries";
import type { MSListEntry } from "../api/types";
import MSTable from "../components/MSTable";
import { computeSelectedMS } from "../utils/selectionLogic";
import { JobManagement } from "../components/workflows/JobManagement";
import { ConversionWorkflow } from "../components/workflows/ConversionWorkflow";
import { CalibrationWorkflow } from "../components/workflows/CalibrationWorkflow";
import { ImagingWorkflow } from "../components/workflows/ImagingWorkflow";
import { WorkflowTemplates } from "../components/workflows/WorkflowTemplates";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import { MSDetailsPanel } from "../components/MSDetails";
import { LiveOperationsCard } from "../components/Pipeline";
import { useNavigate } from "react-router-dom";

export default function ControlPage() {
  const [selectedMS, setSelectedMS] = useState("");
  const [selectedMSList, setSelectedMSList] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const navigate = useNavigate();

  // Queries
  const { data: msList, refetch: refetchMS } = useMSList({
    scan: String(true),
    scan_dir: "/stage/dsa110-contimg/ms",
  });
  const { data: msMetadata } = useMSMetadata(selectedMS);
  const {
    data: calMatches,
    isLoading: calMatchesLoading,
    error: calMatchesError,
  } = useCalibratorMatches(selectedMS);
  const { refetch: refetchJobs } = useJobs();
  const { data: pipelineSummary, isLoading: pipelineSummaryLoading } = usePipelineMetricsSummary();
  const { data: activeExecutions, isLoading: activeExecutionsLoading } =
    useActivePipelineExecutions();

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Ctrl/Cmd + R to refresh (but prevent page reload)
      if ((e.ctrlKey || e.metaKey) && e.key === "r" && !e.shiftKey) {
        const target = e.target as HTMLElement;
        if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
          return; // Allow normal refresh
        }
        e.preventDefault();
        refetchMS();
        refetchJobs();
      }
    };

    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, [refetchMS, refetchJobs]);

  // Job creation callback
  const handleJobCreated = (jobId: number) => {
    setSelectedJobId(jobId);
    refetchJobs();
  };

  return (
    <>
      <PageBreadcrumbs />
      <Box sx={{ p: 3 }}>
        <Typography variant="h2" component="h2" gutterBottom>
          Control Panel
        </Typography>

        <Box sx={{ display: "flex", flexDirection: { xs: "column", lg: "row" }, gap: 2 }}>
          {/* Left column - MS selection and workflows */}
          <Box sx={{ flex: 1 }}>
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Measurement Sets
              </Typography>
              <MSTable
                data={msList?.items || []}
                total={msList?.total}
                filtered={msList?.filtered?.length}
                selected={selectedMSList}
                onSelectionChange={(paths: string[]) => {
                  const prevList = selectedMSList;
                  setSelectedMSList(paths);
                  const newSelectedMS = computeSelectedMS(paths, prevList, selectedMS);
                  setSelectedMS(newSelectedMS);
                }}
                onMSClick={(ms: MSListEntry) => {
                  setSelectedMS(ms.path);
                  setSelectedMSList((prev) => {
                    if (!prev.includes(ms.path)) {
                      return [...prev, ms.path];
                    }
                    return prev;
                  });
                  // Scroll to MS details panel when MS is selected
                  setTimeout(() => {
                    const detailsPanel = document.getElementById("ms-details-panel");
                    if (detailsPanel) {
                      detailsPanel.scrollIntoView({
                        behavior: "smooth",
                        block: "nearest",
                      });
                    }
                  }, 100);
                }}
                onRefresh={refetchMS}
              />

              {/* MS Details Panel - Inspection, Comparison, Related Products */}
              <MSDetailsPanel
                selectedMS={selectedMS}
                metadata={msMetadata}
                onMSSelect={(ms) => {
                  setSelectedMS(ms.path);
                  setSelectedMSList((prev) => {
                    if (!prev.includes(ms.path)) {
                      return [...prev, ms.path];
                    }
                    return prev;
                  });
                }}
              />
              {/* Legacy MS Metadata Panel removed - replaced by MSDetailsPanel above */}
            </Paper>

            {/* Workflow Tabs */}
            <Paper sx={{ p: 2 }}>
              <Tabs value={activeTab} onChange={(_, val) => setActiveTab(val)}>
                <Tab label="Templates" />
                <Tab label="Convert" />
                <Tab label="Calibrate" />
                <Tab label="Image" />
              </Tabs>

              {/* Templates Tab */}
              {activeTab === 0 && (
                <WorkflowTemplates
                  onTemplateSelect={(template) => {
                    // Navigate to appropriate workflow based on template
                    if (template.category === "calibration") {
                      setActiveTab(2); // Calibrate tab
                    } else if (template.category === "imaging") {
                      setActiveTab(3); // Image tab
                    } else if (template.category === "mosaic") {
                      // Could navigate to mosaics page
                    }
                  }}
                />
              )}

              {/* Convert Tab */}
              {activeTab === 1 && (
                <ConversionWorkflow
                  selectedMS={selectedMS}
                  onJobCreated={handleJobCreated}
                  onRefreshJobs={refetchJobs}
                />
              )}

              {/* Calibrate Tab (includes Apply sub-tab) */}
              {activeTab === 2 && (
                <CalibrationWorkflow
                  selectedMS={selectedMS}
                  selectedMSList={selectedMSList}
                  onJobCreated={handleJobCreated}
                  onRefreshJobs={refetchJobs}
                />
              )}

              {/* Image Tab */}
              {activeTab === 3 && (
                <ImagingWorkflow
                  selectedMS={selectedMS}
                  onJobCreated={handleJobCreated}
                  onRefreshJobs={refetchJobs}
                />
              )}
            </Paper>
          </Box>

          <Box
            sx={{
              width: { xs: "100%", lg: 360 },
              display: "flex",
              flexDirection: "column",
              gap: 2,
            }}
          >
            <LiveOperationsCard
              summary={pipelineSummary}
              isSummaryLoading={pipelineSummaryLoading}
              executions={activeExecutions}
              isExecutionsLoading={activeExecutionsLoading}
              onOpenPipeline={() => navigate("/pipeline")}
            />
            <JobManagement selectedJobId={selectedJobId} onJobSelect={setSelectedJobId} />
          </Box>
        </Box>
      </Box>
    </>
  );
}
