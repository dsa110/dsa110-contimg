/**
 * Pipeline Operations Tab
 *
 * Operations monitoring and management:
 * - Dead Letter Queue (DLQ) management
 * - Circuit breaker status
 * - Event stream
 * - Pipeline metrics
 */
import React, { useState } from "react";
import { Box, Tabs, Tab, Paper } from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import { usePipelineMetricsSummary, useDLQStats } from "../../api/queries";
import { DeadLetterQueueTable, DeadLetterQueueStats } from "../../components/DeadLetterQueue";
import { CircuitBreakerStatus } from "../../components/CircuitBreaker/CircuitBreakerStatus";
import { EventStream } from "../../components/Events";
import { StatCard } from "../../components/StatCard";
import { ActiveExecutions, DependencyGraph } from "../../components/Pipeline";

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
      id={`operations-tabpanel-${String(index)}`}
      aria-labelledby={`operations-tab-${String(index)}`}
      sx={{ py: 2 }}
    >
      {value === index && children}
    </Box>
  );
}

export default function OperationsTab() {
  const [tabValue, setTabValue] = useState(0);
  const { data: metricsSummary, isLoading: metricsLoading } = usePipelineMetricsSummary();
  const { data: dlqStats } = useDLQStats();

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Box>
      {/* Metrics Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} sm={3}>
          <StatCard
            title="Running"
            value={metricsLoading ? "..." : String(metricsSummary?.running_jobs ?? 0)}
            color="primary"
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <StatCard
            title="Completed"
            value={metricsLoading ? "..." : String(metricsSummary?.completed_jobs ?? 0)}
            color="success"
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <StatCard
            title="Failed"
            value={metricsLoading ? "..." : String(metricsSummary?.failed_jobs ?? 0)}
            color="error"
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <StatCard
            title="DLQ Pending"
            value={String(dlqStats?.pending ?? 0)}
            color={dlqStats?.pending != null && dlqStats.pending > 0 ? "warning" : "success"}
          />
        </Grid>
      </Grid>

      {/* Sub-tabs */}
      <Paper sx={{ mb: 2 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          aria-label="Operations sub-tabs"
        >
          <Tab label="Dead Letter Queue" />
          <Tab label="Circuit Breakers" />
          <Tab label="Events" />
          <Tab label="Pipeline Graph" />
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        <DeadLetterQueueStats />
        <Box sx={{ mt: 2 }}>
          <DeadLetterQueueTable />
        </Box>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <CircuitBreakerStatus />
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <EventStream />
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        <Grid container spacing={3}>
          <Grid item xs={12} lg={6}>
            <ActiveExecutions />
          </Grid>
          <Grid item xs={12} lg={6}>
            <DependencyGraph />
          </Grid>
        </Grid>
      </TabPanel>
    </Box>
  );
}
