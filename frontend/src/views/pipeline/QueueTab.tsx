/**
 * Pipeline Queue Tab
 *
 * Task queue management (Absurd):
 * - Task dashboard
 * - Workflow builder
 * - Queue metrics charts
 * - Worker management
 * - Schedule manager
 */
import React, { useState } from "react";
import { Box, Tabs, Tab, Paper } from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import { TaskDashboard } from "../../components/absurd/TaskDashboard";
import { WorkflowBuilder } from "../../components/absurd/WorkflowBuilder";
import { QueueMetricsCharts } from "../../components/absurd/QueueMetricsCharts";
import { WorkerManagement } from "../../components/absurd/WorkerManagement";
import { ScheduleManager } from "../../components/absurd/ScheduleManager";
import { MetricsTimeSeriesChart } from "../../components/absurd/MetricsTimeSeriesChart";
import { useAbsurdHealth, useQueueStats } from "../../api/absurdQueries";

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
      id={`queue-tabpanel-${String(index)}`}
      aria-labelledby={`queue-tab-${String(index)}`}
      sx={{ py: 2 }}
    >
      {value === index && children}
    </Box>
  );
}

export default function QueueTab() {
  const [tabValue, setTabValue] = useState(0);
  const { data: health, isLoading: healthLoading } = useAbsurdHealth();
  const { data: stats } = useQueueStats();

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Box>
      {/* Sub-tabs for queue management */}
      <Paper sx={{ mb: 2 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          aria-label="Queue management tabs"
        >
          <Tab label="Tasks" />
          <Tab label="Workflow Builder" />
          <Tab label="Metrics" />
          <Tab label="Workers" />
          <Tab label="Schedules" />
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        <TaskDashboard />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <WorkflowBuilder />
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <QueueMetricsCharts />
          </Grid>
          <Grid item xs={12}>
            <MetricsTimeSeriesChart queueName="dsa110-pipeline" />
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        <WorkerManagement />
      </TabPanel>

      <TabPanel value={tabValue} index={4}>
        <ScheduleManager queueName="dsa110-pipeline" />
      </TabPanel>
    </Box>
  );
}
