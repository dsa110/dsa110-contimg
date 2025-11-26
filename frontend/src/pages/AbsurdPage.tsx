/**
 * Absurd Workflow Page
 * Dedicated page for Absurd pipeline automation and task orchestration
 *
 * This page provides first-class access to:
 * - Task queue monitoring and management (TaskDashboard)
 * - Visual workflow builder for multi-stage pipelines (WorkflowBuilder)
 * - Real-time queue health and statistics
 * - Scheduled task management
 * - DAG-based workflow visualization
 * - Historical metrics with time-series charts
 */

import { useState } from "react";
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  Alert,
  AlertTitle,
  Button,
  Chip,
  Stack,
} from "@mui/material";
import {
  Dashboard as DashboardIcon,
  AccountTree as WorkflowIcon,
  OpenInNew,
  Info as InfoIcon,
  Group as WorkersIcon,
  Schedule as ScheduleIcon,
  Timeline as MetricsIcon,
} from "@mui/icons-material";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import { TaskDashboard } from "../components/absurd/TaskDashboard";
import { WorkflowBuilder } from "../components/absurd/WorkflowBuilder";
import { QueueMetricsCharts } from "../components/absurd/QueueMetricsCharts";
import { WorkerManagement } from "../components/absurd/WorkerManagement";
import { ScheduleManager } from "../components/absurd/ScheduleManager";
import { MetricsTimeSeriesChart } from "../components/absurd/MetricsTimeSeriesChart";
import { useAbsurdHealth, useQueueStats } from "../api/absurdQueries";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index } = props;
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

export default function AbsurdPage() {
  const [tabValue, setTabValue] = useState(0);
  const { data: health } = useAbsurdHealth();
  const { data: stats } = useQueueStats("dsa110-pipeline");

  // Determine queue health status
  const getHealthStatus = () => {
    if (!health || !stats) return { color: "default" as const, label: "Unknown" };

    const failureRate = stats.failed / (stats.completed + stats.failed || 1);
    const queueBacklog = stats.pending + stats.claimed;

    if (failureRate > 0.2 || stats.failed > 10) {
      return { color: "error" as const, label: "Degraded" };
    }
    if (queueBacklog > 50 || failureRate > 0.1) {
      return { color: "warning" as const, label: "Busy" };
    }
    return { color: "success" as const, label: "Healthy" };
  };

  const healthStatus = getHealthStatus();

  return (
    <>
      <PageBreadcrumbs />
      <Box sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ mb: 3 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              mb: 2,
            }}
          >
            <Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1 }}>
                <Typography variant="h2" component="h1">
                  Absurd Pipeline Automation
                </Typography>
                <Chip
                  label={healthStatus.label}
                  color={healthStatus.color}
                  size="small"
                  sx={{ fontWeight: 600 }}
                />
              </Box>
              <Typography variant="body1" color="text.secondary">
                Distributed task orchestration for multi-stage radio astronomy pipelines
              </Typography>
            </Box>
            <Button
              variant="outlined"
              startIcon={<OpenInNew />}
              href="https://github.com/absurd-queue/absurd"
              target="_blank"
              rel="noopener noreferrer"
            >
              Documentation
            </Button>
          </Box>

          {/* Quick stats banner */}
          {stats && (
            <Paper sx={{ p: 2, bgcolor: "background.default" }}>
              <Stack direction="row" spacing={3} flexWrap="wrap">
                <Box>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Active Tasks
                  </Typography>
                  <Typography variant="h6" color="primary.main">
                    {stats.claimed}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Pending
                  </Typography>
                  <Typography variant="h6">{stats.pending}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Completed
                  </Typography>
                  <Typography variant="h6" color="success.main">
                    {stats.completed}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Failed
                  </Typography>
                  <Typography variant="h6" color="error.main">
                    {stats.failed}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Retry Queue
                  </Typography>
                  <Typography variant="h6" color="warning.main">
                    {stats.cancelled}
                  </Typography>
                </Box>
              </Stack>
            </Paper>
          )}
        </Box>

        {/* Info alert for new users */}
        {tabValue === 0 && (
          <Alert severity="info" icon={<InfoIcon />} sx={{ mb: 3 }}>
            <AlertTitle>About Absurd Task Orchestration</AlertTitle>
            Absurd is a distributed task queue system that powers the DSA-110 imaging pipeline. Use
            the <strong>Task Dashboard</strong> to monitor running jobs and queue health. Switch to
            the <strong>Workflow Builder</strong> tab to create custom multi-stage pipelines with
            dependencies and priority controls.
          </Alert>
        )}

        {/* Tabs */}
        <Paper sx={{ mb: 2 }}>
          <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
            <Tab
              icon={<DashboardIcon />}
              iconPosition="start"
              label="Task Dashboard"
              sx={{ textTransform: "none" }}
            />
            <Tab
              icon={<WorkflowIcon />}
              iconPosition="start"
              label="Workflow Builder"
              sx={{ textTransform: "none" }}
            />
            <Tab
              icon={<WorkersIcon />}
              iconPosition="start"
              label="Workers"
              sx={{ textTransform: "none" }}
            />
            <Tab
              icon={<ScheduleIcon />}
              iconPosition="start"
              label="Schedules"
              sx={{ textTransform: "none" }}
            />
            <Tab
              icon={<MetricsIcon />}
              iconPosition="start"
              label="Metrics"
              sx={{ textTransform: "none" }}
            />
          </Tabs>
        </Paper>

        {/* Tab content */}
        <TabPanel value={tabValue} index={0}>
          {/* Enhanced Metrics Charts */}
          {stats && <QueueMetricsCharts queueName="dsa110-pipeline" />}

          {/* Task Dashboard */}
          <Box sx={{ mt: 3 }}>
            <TaskDashboard queueName="dsa110-pipeline" />
          </Box>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <WorkflowBuilder
            queueName="dsa110-pipeline"
            onWorkflowSubmitted={(taskIds) => {
              console.log("Workflow submitted with task IDs:", taskIds);
              // Switch to dashboard tab to see submitted tasks
              setTabValue(0);
            }}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <WorkerManagement showMetrics={true} showWorkerList={true} />
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <ScheduleManager queueName="dsa110-pipeline" />
        </TabPanel>

        <TabPanel value={tabValue} index={4}>
          <MetricsTimeSeriesChart queueName="dsa110-pipeline" />
        </TabPanel>
      </Box>
    </>
  );
}
