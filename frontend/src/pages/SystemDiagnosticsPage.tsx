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
} from "@mui/icons-material";
import HealthPage from "./HealthPage";
import QAVisualizationPage from "./QAVisualizationPage";
import CachePage from "./CachePage";
import { StatCard } from "../components/StatCard";
import { useSystemMetrics } from "../api/queries";
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
                    systemMetrics.disk_total && systemMetrics.disk_used
                      ? `${((systemMetrics.disk_used / systemMetrics.disk_total) * 100).toFixed(1)}%`
                      : "N/A"
                  }
                  color={
                    systemMetrics.disk_total && systemMetrics.disk_used
                      ? (systemMetrics.disk_used / systemMetrics.disk_total) * 100 > 90
                        ? "error"
                        : (systemMetrics.disk_used / systemMetrics.disk_total) * 100 > 75
                          ? "warning"
                          : "success"
                      : "default"
                  }
                  icon={<HealthIcon />}
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
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Box sx={{ mt: -4 }}>
          <HealthPage />
        </Box>
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <Box sx={{ mt: -4 }}>
          <QAVisualizationPage />
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
