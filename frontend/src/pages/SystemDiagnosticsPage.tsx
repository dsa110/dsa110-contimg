/**
 * System Diagnostics Page
 * Consolidated view of System Health, QA Tools, and Cache Statistics
 */
import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Container, Typography, Box, Tabs, Tab, Stack } from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import {
  HealthAndSafety as HealthIcon,
  Assessment as QAIcon,
  Cached as CacheIcon,
  Dashboard as DashboardIcon,
  Storage as StorageIcon,
} from "@mui/icons-material";
import HealthPage from "./HealthPage";
import QAPage from "./QAPage";
import CachePage from "./CachePage";
import { StatCard } from "../components/StatCard";
import { useSystemMetrics, useDatabaseMetrics } from "../api/queries";
import { useDLQStats } from "../api/queries";
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
      id={`system-diagnostics-tabpanel-${index}`}
      aria-labelledby={`system-diagnostics-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export default function SystemDiagnosticsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = parseInt(searchParams.get("tab") || "0", 10);
  const [tabValue, setTabValue] = useState(initialTab);
  const { data: systemMetrics } = useSystemMetrics();
  const { data: databaseMetrics } = useDatabaseMetrics();

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

  const { data: dlqStats } = useDLQStats();

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    setSearchParams({ tab: newValue.toString() }, { replace: true });
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Stack spacing={2} sx={{ mb: 3 }}>
        <Typography variant="h1" component="h1">
          System Diagnostics
        </Typography>
        <UnifiedSearch placeholder="Search health metrics, QA reports, cache statistics..." />
      </Stack>

      <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 3 }}>
        <Tab label="Dashboard" icon={<DashboardIcon />} iconPosition="start" />
        <Tab label="System Health" icon={<HealthIcon />} iconPosition="start" />
        <Tab label="QA Tools" icon={<QAIcon />} iconPosition="start" />
        <Tab label="Cache" icon={<CacheIcon />} iconPosition="start" />
      </Tabs>

      <TabPanel value={tabValue} index={0}>
        {/* Combined Dashboard */}
        <Grid container spacing={3}>
          {systemMetrics && (
            <>
              <Grid item xs={12} md={4}>
                <StatCard
                  title="CPU Usage"
                  value={
                    systemMetrics.cpu_percent != null
                      ? `${systemMetrics.cpu_percent.toFixed(1)}%`
                      : "N/A"
                  }
                  color={
                    systemMetrics.cpu_percent != null
                      ? systemMetrics.cpu_percent > 70
                        ? "error"
                        : systemMetrics.cpu_percent > 50
                          ? "warning"
                          : "success"
                      : "default"
                  }
                  icon={<HealthIcon />}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <StatCard
                  title="Memory Usage"
                  value={
                    systemMetrics.mem_percent != null
                      ? `${systemMetrics.mem_percent.toFixed(1)}%`
                      : "N/A"
                  }
                  color={
                    systemMetrics.mem_percent != null
                      ? systemMetrics.mem_percent > 80
                        ? "error"
                        : systemMetrics.mem_percent > 60
                          ? "warning"
                          : "success"
                      : "default"
                  }
                  icon={<HealthIcon />}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <StatCard
                  title="Disk Usage"
                  value={
                    systemMetrics.disks?.[0]?.percent
                      ? `${systemMetrics.disks[0].percent.toFixed(1)}%`
                      : "N/A"
                  }
                  color={
                    systemMetrics.disks?.[0]?.percent
                      ? systemMetrics.disks[0].percent > 90
                        ? "error"
                        : systemMetrics.disks[0].percent > 75
                          ? "warning"
                          : "success"
                      : "default"
                  }
                  icon={<StorageIcon />}
                />
              </Grid>
            </>
          )}
          {dlqStats && (
            <>
              <Grid item xs={12} md={4}>
                <StatCard
                  title="DLQ Issues"
                  value={dlqStats.total}
                  color={dlqStats.total > 0 ? "error" : "success"}
                  icon={<HealthIcon />}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <StatCard
                  title="DLQ Pending"
                  value={dlqStats.pending}
                  color={
                    dlqStats.pending > 5 ? "error" : dlqStats.pending > 0 ? "warning" : "success"
                  }
                  icon={<HealthIcon />}
                />
              </Grid>
            </>
          )}
          {databaseMetrics && (
            <>
              <Grid item xs={12}>
                <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
                  Database Performance
                </Typography>
              </Grid>
              <Grid item xs={12} md={3}>
                <StatCard
                  title="Total Operations"
                  value={databaseMetrics.total_operations.toLocaleString()}
                  color="info"
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <StatCard
                  title="Error Rate"
                  value={
                    databaseMetrics.error_rate > 0
                      ? `${(databaseMetrics.error_rate * 100).toFixed(2)}%`
                      : "0%"
                  }
                  color={
                    databaseMetrics.error_rate > 0.01
                      ? "error"
                      : databaseMetrics.error_rate > 0.001
                        ? "warning"
                        : "success"
                  }
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <StatCard
                  title="Avg Duration"
                  value={`${(databaseMetrics.avg_duration * 1000).toFixed(1)}ms`}
                  color={
                    databaseMetrics.avg_duration > 0.1
                      ? "error"
                      : databaseMetrics.avg_duration > 0.05
                        ? "warning"
                        : "success"
                  }
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <StatCard
                  title="P95 Duration"
                  value={`${(databaseMetrics.p95_duration * 1000).toFixed(1)}ms`}
                  color={
                    databaseMetrics.p95_duration > 0.1
                      ? "error"
                      : databaseMetrics.p95_duration > 0.05
                        ? "warning"
                        : "success"
                  }
                />
              </Grid>
            </>
          )}
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Box sx={{ mt: -4 }}>
          <HealthPage />
        </Box>
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <Box sx={{ mt: -4 }}>
          <QAPage />
        </Box>
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        <Box sx={{ mt: -4 }}>
          <CachePage />
        </Box>
      </TabPanel>
    </Container>
  );
}
