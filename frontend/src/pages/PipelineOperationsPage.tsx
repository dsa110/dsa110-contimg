/**
 * Pipeline Operations Page
 * Consolidated view of Pipeline monitoring, Operations (DLQ), and Events
 */
import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Container,
  Typography,
  Paper,
  Box,
  Grid,
  Tabs,
  Tab,
  Card,
  CardContent,
  CardHeader,
  Stack,
} from "@mui/material";
import {
  AccountTree as PipelineIcon,
  ErrorOutline as OperationsIcon,
  EventNote as EventsIcon,
} from "@mui/icons-material";
import { useActivePipelineExecutions, usePipelineMetricsSummary } from "../api/queries";
import { useDLQStats } from "../api/queries";
import {
  ActiveExecutions,
  ExecutionHistory,
  StageMetrics,
  DependencyGraph,
} from "../components/Pipeline";
import { DeadLetterQueueTable, DeadLetterQueueStats } from "../components/DeadLetterQueue";
import { CircuitBreakerStatus } from "../components/CircuitBreaker/CircuitBreakerStatus";
import { EventStream, EventStats } from "../components/Events";
import { StatCard } from "../components/StatCard";
import UnifiedSearch from "../components/UnifiedSearch";

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
      id={`pipeline-ops-tabpanel-${index}`}
      aria-labelledby={`pipeline-ops-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export default function PipelineOperationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = parseInt(searchParams.get("tab") || "0", 10);
  const [tabValue, setTabValue] = useState(initialTab);
  const { data: metricsSummary, isLoading: metricsLoading } = usePipelineMetricsSummary();
  const { data: dlqStats } = useDLQStats();

  // Sync URL with tab changes
  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam !== null) {
      const tabNum = parseInt(tabParam, 10);
      if (!isNaN(tabNum) && tabNum !== tabValue) {
        setTabValue(tabNum);
      }
    }
  }, [searchParams, tabValue]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    setSearchParams({ tab: newValue.toString() }, { replace: true });
  };

  const getSuccessRateColor = (rate: number): "success" | "warning" | "error" => {
    if (rate >= 80) return "success";
    if (rate >= 50) return "warning";
    return "error";
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Stack spacing={2} sx={{ mb: 3 }}>
        <Typography variant="h1" component="h1">
          Pipeline Operations
        </Typography>
        <UnifiedSearch placeholder="Search executions, DLQ, events, circuit breakers..." />
      </Stack>

      <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 3 }}>
        <Tab label="Overview" icon={<PipelineIcon />} iconPosition="start" />
        <Tab label="Executions" icon={<PipelineIcon />} iconPosition="start" />
        <Tab label="Operations" icon={<OperationsIcon />} iconPosition="start" />
        <Tab label="Events" icon={<EventsIcon />} iconPosition="start" />
        <Tab label="Dependency Graph" />
      </Tabs>

      <TabPanel value={tabValue} index={0}>
        {/* Overview Tab - Combined summary */}
        <Grid container spacing={3} sx={{ mb: 3 }}>
          {/* Pipeline Summary */}
          {!metricsLoading && metricsSummary && (
            <>
              <Grid xs={12} md={6}>
                <StatCard
                  title="Success Rate"
                  value={`${(metricsSummary.success_rate * 100).toFixed(1)}%`}
                  size="large"
                  color={getSuccessRateColor(metricsSummary.success_rate * 100)}
                  alert={metricsSummary.success_rate < 0.5}
                  alertMessage={
                    metricsSummary.success_rate < 0.5 ? "Low success rate detected" : undefined
                  }
                />
              </Grid>
              <Grid xs={12} md={6}>
                <StatCard
                  title="Failed Jobs"
                  value={metricsSummary.failed_jobs}
                  size="large"
                  color="error"
                  alert={metricsSummary.failed_jobs > 0}
                />
              </Grid>
              <Grid xs={6} md={3}>
                <StatCard
                  title="Total Jobs"
                  value={metricsSummary.total_jobs}
                  icon={<PipelineIcon />}
                />
              </Grid>
              <Grid xs={6} md={3}>
                <StatCard
                  title="Running"
                  value={metricsSummary.running_jobs}
                  color="primary"
                  icon={<PipelineIcon />}
                />
              </Grid>
              <Grid xs={6} md={3}>
                <StatCard
                  title="Completed"
                  value={metricsSummary.completed_jobs}
                  color="success"
                  icon={<PipelineIcon />}
                />
              </Grid>
              <Grid xs={6} md={3}>
                <StatCard
                  title="Avg Duration"
                  value={
                    metricsSummary.avg_duration_minutes
                      ? `${metricsSummary.avg_duration_minutes.toFixed(1)} min`
                      : "N/A"
                  }
                  icon={<PipelineIcon />}
                />
              </Grid>
            </>
          )}

          {/* DLQ Summary */}
          {dlqStats && (
            <>
              <Grid xs={12} md={4}>
                <StatCard
                  title="DLQ Total"
                  value={dlqStats.total}
                  color={dlqStats.total > 0 ? "error" : "success"}
                  icon={<OperationsIcon />}
                />
              </Grid>
              <Grid xs={12} md={4}>
                <StatCard
                  title="DLQ Pending"
                  value={dlqStats.pending}
                  color={
                    dlqStats.pending > 5 ? "error" : dlqStats.pending > 0 ? "warning" : "success"
                  }
                  icon={<OperationsIcon />}
                />
              </Grid>
              <Grid xs={12} md={4}>
                <StatCard
                  title="DLQ Resolved"
                  value={dlqStats.resolved}
                  color="success"
                  icon={<OperationsIcon />}
                />
              </Grid>
            </>
          )}
        </Grid>

        {/* Recent Activity Timeline could go here */}
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        {/* Executions Tab - From Pipeline page */}
        <ActiveExecutions />
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        {/* Operations Tab - From Operations page */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Dead Letter Queue
          </Typography>
          <DeadLetterQueueStats />
          <Box sx={{ mt: 3 }}>
            <DeadLetterQueueTable limit={100} />
          </Box>
        </Paper>
        <Paper sx={{ mt: 3, p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Circuit Breakers
          </Typography>
          <CircuitBreakerStatus />
        </Paper>
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        {/* Events Tab - From Events page */}
        <EventStream />
      </TabPanel>

      <TabPanel value={tabValue} index={4}>
        {/* Dependency Graph Tab */}
        <DependencyGraph />
      </TabPanel>
    </Container>
  );
}
