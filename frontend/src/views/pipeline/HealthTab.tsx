/**
 * Pipeline Health Tab
 *
 * System health and diagnostics:
 * - System monitoring
 * - Queue health
 * - Operations health
 * - QA diagnostics
 * - Database metrics
 */
import React, { useState } from "react";
import { Box, Tabs, Tab, Paper, Stack } from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import { SystemMonitoringTab } from "../../components/health/SystemMonitoringTab";
import { QueueHealthTab } from "../../components/health/QueueHealthTab";
import { OperationsHealthTab } from "../../components/health/OperationsHealthTab";
import { QADiagnosticsTab } from "../../components/health/QADiagnosticsTab";
import { StatCard } from "../../components/StatCard";
import { useSystemMetrics, useDatabaseMetrics, useDLQStats } from "../../api/queries";
import { DLQMetricsPanel } from "../../components/metrics/DLQMetricsPanel";
import { DatabaseMetricsPanel } from "../../components/metrics/DatabaseMetricsPanel";
import { CacheStats, CacheKeys, CachePerformance } from "../../components/Cache";
import type { SystemMetrics } from "../../api/types";

// Helper functions for disk metrics
function getDiskPercent(metrics: SystemMetrics | undefined): string {
  if (metrics == null) {
    return "0%";
  }
  const { disk_used, disk_total } = metrics;
  if (disk_used == null || disk_total == null || disk_total === 0) {
    return "0%";
  }
  const percent = (disk_used / disk_total) * 100;
  return `${percent.toFixed(1)}%`;
}

function getDiskColor(metrics: SystemMetrics | undefined): "success" | "warning" | "error" {
  if (metrics == null) {
    return "success";
  }
  const { disk_used, disk_total } = metrics;
  if (disk_used == null || disk_total == null || disk_total === 0) {
    return "success";
  }
  const percent = (disk_used / disk_total) * 100;
  return percent > 90 ? "error" : "success";
}

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
      id={`health-tabpanel-${String(index)}`}
      aria-labelledby={`health-tab-${String(index)}`}
      sx={{ py: 2 }}
    >
      {value === index && children}
    </Box>
  );
}

export default function HealthTab() {
  const [tabValue, setTabValue] = useState(0);
  const { data: systemMetrics, isLoading: metricsLoading } = useSystemMetrics();
  // Database metrics available for future use in sub-tabs
  useDatabaseMetrics();
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
            title="CPU Usage"
            value={metricsLoading ? "..." : `${systemMetrics?.cpu_percent?.toFixed(1) ?? "0"}%`}
            color={
              systemMetrics?.cpu_percent != null && systemMetrics.cpu_percent > 80 ? "error" : "success"
            }
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <StatCard
            title="Memory"
            value={metricsLoading ? "..." : `${systemMetrics?.mem_percent?.toFixed(1) ?? "0"}%`}
            color={
              systemMetrics?.mem_percent != null && systemMetrics.mem_percent > 80
                ? "error"
                : "success"
            }
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <StatCard
            title="Disk"
            value={metricsLoading ? "..." : getDiskPercent(systemMetrics)}
            color={getDiskColor(systemMetrics)}
          />
        </Grid>
        <Grid item xs={6} sm={3}>
          <StatCard
            title="DLQ Items"
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
          variant="scrollable"
          scrollButtons="auto"
          aria-label="Health sub-tabs"
        >
          <Tab label="System" />
          <Tab label="Queues" />
          <Tab label="Operations" />
          <Tab label="QA Diagnostics" />
          <Tab label="Database" />
          <Tab label="Cache" />
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        <SystemMonitoringTab />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <QueueHealthTab />
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <OperationsHealthTab />
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        <QADiagnosticsTab />
      </TabPanel>

      <TabPanel value={tabValue} index={4}>
        <Stack spacing={3}>
          <DLQMetricsPanel />
          <DatabaseMetricsPanel />
        </Stack>
      </TabPanel>

      <TabPanel value={tabValue} index={5}>
        <Stack spacing={3}>
          <CacheStats />
          <CachePerformance />
          <CacheKeys />
        </Stack>
      </TabPanel>
    </Box>
  );
}
