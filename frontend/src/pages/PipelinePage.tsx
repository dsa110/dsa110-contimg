import React, { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Container,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import { useActivePipelineExecutions, usePipelineMetricsSummary } from "../api/queries";
import ActiveExecutions from "../components/Pipeline/ActiveExecutions";
import ExecutionHistory from "../components/Pipeline/ExecutionHistory";
import StageMetrics from "../components/Pipeline/StageMetrics";
import DependencyGraph from "../components/Pipeline/DependencyGraph";

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
      id={`pipeline-tabpanel-${index}`}
      aria-labelledby={`pipeline-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export default function PipelinePage() {
  const [tabValue, setTabValue] = useState(0);
  const { data: metricsSummary, isLoading: metricsLoading } = usePipelineMetricsSummary();

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Pipeline Monitoring
      </Typography>

      {/* Metrics Summary Card */}
      {!metricsLoading && metricsSummary && (
        <Card sx={{ mb: 3 }}>
          <CardHeader title="Pipeline Summary" />
          <CardContent>
            <Box sx={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Total Jobs
                </Typography>
                <Typography variant="h5">{metricsSummary.total_jobs}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Running
                </Typography>
                <Typography variant="h5" color="primary">
                  {metricsSummary.running_jobs}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Completed
                </Typography>
                <Typography variant="h5" color="success.main">
                  {metricsSummary.completed_jobs}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Failed
                </Typography>
                <Typography variant="h5" color="error.main">
                  {metricsSummary.failed_jobs}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Success Rate
                </Typography>
                <Typography variant="h5">
                  {(metricsSummary.success_rate * 100).toFixed(1)}%
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Avg Duration
                </Typography>
                <Typography variant="h5">
                  {metricsSummary.average_duration_seconds > 0
                    ? `${(metricsSummary.average_duration_seconds / 60).toFixed(1)} min`
                    : "N/A"}
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="pipeline tabs">
            <Tab
              label="Active Executions"
              id="pipeline-tab-0"
              aria-controls="pipeline-tabpanel-0"
            />
            <Tab
              label="Execution History"
              id="pipeline-tab-1"
              aria-controls="pipeline-tabpanel-1"
            />
            <Tab label="Stage Metrics" id="pipeline-tab-2" aria-controls="pipeline-tabpanel-2" />
            <Tab label="Dependency Graph" id="pipeline-tab-3" aria-controls="pipeline-tabpanel-3" />
          </Tabs>
        </Box>

        <TabPanel value={tabValue} index={0}>
          <ActiveExecutions />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <ExecutionHistory />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <StageMetrics />
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <DependencyGraph />
        </TabPanel>
      </Card>
    </Container>
  );
}
