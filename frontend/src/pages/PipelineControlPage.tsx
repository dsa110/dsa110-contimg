/**
 * Pipeline Control Page
 * Consolidated view of Control Panel, Streaming Service, and Observing
 */
import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Container, Typography, Box, Tabs, Tab, Stack, Alert, Link } from "@mui/material";
import {
  Settings as ControlIcon,
  Task as AbsurdIcon,
  Visibility as ObservingIcon,
} from "@mui/icons-material";
import ControlPage from "./ControlPage";
import { TaskDashboard } from "../components/absurd/TaskDashboard";
import ObservingPage from "./ObservingPage";
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
      id={`pipeline-control-tabpanel-${index}`}
      aria-labelledby={`pipeline-control-tab-${index}`}
      {...other}
    >
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

export default function PipelineControlPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = parseInt(searchParams.get("tab") || "0", 10);
  const [tabValue, setTabValue] = useState(initialTab);

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

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Stack spacing={2} sx={{ mb: 3 }}>
        <Typography variant="h1" component="h1">
          Pipeline Control
        </Typography>
        <UnifiedSearch placeholder="Search workflows, streaming, observing, MS files..." />
      </Stack>

      <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 3 }}>
        <Tab label="Measurement Sets & Workflows" icon={<ControlIcon />} iconPosition="start" />
        <Tab label="Custom DAG (Absurd)" icon={<AbsurdIcon />} iconPosition="start" />
        <Tab label="Observing" icon={<ObservingIcon />} iconPosition="start" />
      </Tabs>

      <TabPanel value={tabValue} index={0}>
        <Box sx={{ mt: -4 }}>
          <ControlPage />
        </Box>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Box sx={{ mt: -4 }}>
          <Alert severity="info" sx={{ mb: 2 }}>
            This tab provides quick access to Absurd task monitoring. For the full Absurd experience
            including workflow builder and advanced orchestration, visit the{" "}
            <Link href="/absurd" underline="hover" sx={{ fontWeight: 600 }}>
              dedicated Absurd page
            </Link>
            .
          </Alert>
          <TaskDashboard queueName="dsa110-pipeline" />
        </Box>
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <Box sx={{ mt: -4 }}>
          <ObservingPage />
        </Box>
      </TabPanel>
    </Container>
  );
}
