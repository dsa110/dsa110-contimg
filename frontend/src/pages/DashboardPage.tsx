import React, { useState } from "react";
import { Container, Typography, Box, Alert, Stack, Button } from "@mui/material";
import { usePipelineStatus, useSystemMetrics, useHealthSummary } from "../api/queries";
import { useNavigate } from "react-router-dom";
import ESECandidatesPanel from "../components/ESECandidatesPanel";
import PointingVisualization from "../components/PointingVisualization";
import { env } from "../config/env";
import { SkeletonLoader } from "../components/SkeletonLoader";
import CollapsibleSection from "../components/CollapsibleSection";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import QueueDetailsPanel from "../components/QueueDetailsPanel";
import { CircuitBreakerStatus } from "../components/CircuitBreaker";
import { QueueDepthChart } from "../components/QueueDepthChart";
import { SystemHealthSection } from "../components/dashboard/SystemHealthSection";
import { PipelineStatusSection } from "../components/dashboard/PipelineStatusSection";
import { RecentObservationsTable } from "../components/dashboard/RecentObservationsTable";
import { AbsurdQueuesCard } from "../components/dashboard/AbsurdQueuesCard";
import { DASHBOARD_CONFIG } from "../config/dashboard";

type QueueStatusType = "total" | "pending" | "in_progress" | "completed" | "failed" | "collecting";

export default function DashboardPage() {
  const { data: status, isLoading: statusLoading, error: statusError } = usePipelineStatus();
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useSystemMetrics();
  const { data: healthSummary, isLoading: healthSummaryLoading } = useHealthSummary();
  const navigate = useNavigate();
  const [selectedQueueStatus, setSelectedQueueStatus] = useState<QueueStatusType>("in_progress");
  const { thresholds } = DASHBOARD_CONFIG;

  if (statusLoading || metricsLoading) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <SkeletonLoader variant="cards" rows={4} />
      </Container>
    );
  }

  if (statusError || metricsError) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert severity="error">
          Failed to connect to DSA-110 pipeline API.{" "}
          {env.VITE_API_URL ? `Using API URL: ${env.VITE_API_URL}` : "Using Vite proxy (/api)."} Is
          the backend running?
        </Alert>
      </Container>
    );
  }

  return (
    <>
      <PageBreadcrumbs />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="h3" component="h1" gutterBottom sx={{ fontWeight: 700, mb: 1 }}>
            DSA-110 Continuum Imaging Pipeline
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Real-time monitoring and control dashboard
          </Typography>
        </Box>

        <Stack spacing={3}>
          {/* Row 1: Pipeline Status + Queue Details + System Health */}
          <Box sx={{ width: "100%" }}>
            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={3}
              sx={{ alignItems: "stretch" }}
            >
              <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
                <PipelineStatusSection
                  status={status}
                  selectedQueueStatus={selectedQueueStatus}
                  onSelectQueueStatus={setSelectedQueueStatus}
                />
              </Box>

              {/* Queue Details Panel */}
              <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
                <CollapsibleSection title="Queue Details" defaultExpanded={true} variant="outlined">
                  <QueueDetailsPanel
                    selectedStatus={selectedQueueStatus}
                    queueGroups={status?.recent_groups || []}
                    isLoading={statusLoading}
                  />
                </CollapsibleSection>
              </Box>

              {/* System Health */}
              <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
                <SystemHealthSection
                  metrics={metrics}
                  healthSummary={healthSummary}
                  loading={healthSummaryLoading}
                />
              </Box>
            </Stack>
          </Box>

          {/* Row 2: Absurd Queues Card */}
          <Box sx={{ width: "100%" }}>
            <AbsurdQueuesCard />
          </Box>

          {/* ESE Candidates Panel */}
          <Box sx={{ width: "100%" }}>
            <ESECandidatesPanel />
          </Box>

          {/* Grafana-style Queue Depth Monitoring */}
          <Box sx={{ width: "100%" }}>
            <QueueDepthChart
              queueName="dsa110-pipeline"
              warningThreshold={thresholds.queueDepth.warning}
              criticalThreshold={thresholds.queueDepth.critical}
              updateInterval={15000}
            />
          </Box>

          {/* Diagnostics & Alerts */}
          <CollapsibleSection
            title="Diagnostics & Alerts"
            defaultExpanded={true}
            variant="outlined"
          >
            <Stack spacing={3} sx={{ mt: 2 }}>
              {/* Pointing Visualization */}
              <Box>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    mb: 2,
                  }}
                >
                  <Typography variant="h6">Pointing Visualization</Typography>
                  <Button variant="outlined" size="small" onClick={() => navigate("/observing")}>
                    Open Observing View
                  </Button>
                </Box>
                <PointingVisualization height={500} showHistory={true} />
              </Box>

              <Box>
                <CircuitBreakerStatus />
              </Box>

              <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
                <Button variant="outlined" onClick={() => navigate("/health")}>
                  View detailed diagnostics
                </Button>
              </Box>
            </Stack>
          </CollapsibleSection>

          {/* Recent Observations */}
          <RecentObservationsTable status={status} />

          {/* Status Summary */}
          <Alert severity="success">
            DSA-110 Frontend v0.2.0 - Enhanced dashboard with ESE monitoring, mosaic gallery, source
            tracking, and interactive visualizations now available!
          </Alert>
        </Stack>
      </Container>
    </>
  );
}
