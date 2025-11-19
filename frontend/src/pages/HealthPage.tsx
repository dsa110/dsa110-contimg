/**
 * Health Page
 * Deep diagnostics for pipeline and data quality monitoring
 */
import React, { useState } from "react";
import { Container, Typography, Box, Tabs, Tab } from "@mui/material";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import { SystemMonitoringTab } from "../components/health/SystemMonitoringTab";
import { QueueHealthTab } from "../components/health/QueueHealthTab";
import { OperationsHealthTab } from "../components/health/OperationsHealthTab";
import { QADiagnosticsTab } from "../components/health/QADiagnosticsTab";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

export default function HealthPage() {
  const [tabValue, setTabValue] = useState(0);

  return (
    <>
      <PageBreadcrumbs />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Typography variant="h3" gutterBottom sx={{ mb: 4 }}>
          System Health & Diagnostics
        </Typography>

        <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ mb: 3 }}>
          <Tab label="System Monitoring" />
          <Tab label="Queue Status" />
          <Tab label="Operations Health" />
          <Tab label="QA Diagnostics" />
        </Tabs>

        {/* System Monitoring Tab */}
        <TabPanel value={tabValue} index={0}>
          <SystemMonitoringTab />
        </TabPanel>

        {/* Queue Status Tab */}
        <TabPanel value={tabValue} index={1}>
          <QueueHealthTab />
        </TabPanel>

        {/* Operations Health Tab */}
        <TabPanel value={tabValue} index={2}>
          <OperationsHealthTab />
        </TabPanel>

        {/* QA Diagnostics Tab */}
        <TabPanel value={tabValue} index={3}>
          <QADiagnosticsTab />
        </TabPanel>
      </Container>
    </>
  );
}
