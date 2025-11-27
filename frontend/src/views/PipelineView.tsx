/**
 * PipelineView - Unified Pipeline Execution & Monitoring
 *
 * Consolidates all pipeline-related pages into a single, organized view:
 * - Overview: Quick status dashboard with workflow stages
 * - Control: Execute workflows (conversion, calibration, imaging)
 * - Streaming: Real-time data ingest management
 * - Calibration: Calibration workflow execution
 * - Operations: DLQ, circuit breakers, events
 * - Queue: Task queue management (Absurd)
 * - Health: System status and diagnostics
 */
import React, { useState, useEffect, lazy, Suspense } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Box,
  Tabs,
  Tab,
  Typography,
  CircularProgress,
  Paper,
  useTheme,
  alpha,
} from "@mui/material";
import {
  Dashboard,
  PlayCircle,
  Stream,
  Science,
  Build,
  Queue,
  MonitorHeart,
} from "@mui/icons-material";
import TabErrorBoundary from "../components/TabErrorBoundary";

// Lazy-load tab content components for code splitting
const OverviewTab = lazy(() => import("./pipeline/OverviewTab"));
const ControlTab = lazy(() => import("./pipeline/ControlTab"));
const StreamingTab = lazy(() => import("./pipeline/StreamingTab"));
const CalibrationTab = lazy(() => import("./pipeline/CalibrationTab"));
const OperationsTab = lazy(() => import("./pipeline/OperationsTab"));
const QueueTab = lazy(() => import("./pipeline/QueueTab"));
const HealthTab = lazy(() => import("./pipeline/HealthTab"));

/** Tab configuration for the pipeline view */
const TABS = [
  { id: "overview", label: "Overview", icon: <Dashboard />, component: OverviewTab },
  { id: "control", label: "Control", icon: <PlayCircle />, component: ControlTab },
  { id: "streaming", label: "Streaming", icon: <Stream />, component: StreamingTab },
  { id: "calibration", label: "Calibration", icon: <Science />, component: CalibrationTab },
  { id: "operations", label: "Operations", icon: <Build />, component: OperationsTab },
  { id: "queue", label: "Queue", icon: <Queue />, component: QueueTab },
  { id: "health", label: "Health", icon: <MonitorHeart />, component: HealthTab },
] as const;

type TabId = (typeof TABS)[number]["id"];

/** TabPanel wrapper component */
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
      id={`pipeline-tabpanel-${String(index)}`}
      aria-labelledby={`pipeline-tab-${String(index)}`}
      sx={{ py: 2 }}
    >
      {value === index && children}
    </Box>
  );
}

/** Loading fallback for lazy-loaded tabs */
function TabLoadingFallback() {
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: 300,
      }}
    >
      <CircularProgress />
    </Box>
  );
}

export default function PipelineView() {
  const theme = useTheme();
  const [searchParams, setSearchParams] = useSearchParams();

  // Get initial tab from URL or default to "overview"
  const initialTabId = searchParams.get("tab") as TabId | null;
  const initialTabIndex = initialTabId
    ? TABS.findIndex((t) => t.id === initialTabId)
    : 0;

  const [tabValue, setTabValue] = useState(initialTabIndex >= 0 ? initialTabIndex : 0);

  // Sync URL with tab changes
  useEffect(() => {
    const tab = TABS[tabValue];
    if (tab.id !== "overview") {
      setSearchParams({ tab: tab.id }, { replace: true });
    } else if (searchParams.has("tab")) {
      setSearchParams({}, { replace: true });
    }
  }, [tabValue, setSearchParams, searchParams]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Box sx={{ width: "100%", py: 2 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Pipeline
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Execute and monitor data processing workflows
        </Typography>
      </Box>

      {/* Tab Navigation */}
      <Paper
        elevation={0}
        sx={{
          borderBottom: 1,
          borderColor: "divider",
          bgcolor: alpha(theme.palette.background.paper, 0.5),
          borderRadius: 2,
          mb: 2,
        }}
      >
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          aria-label="Pipeline tabs"
          sx={{
            "& .MuiTab-root": {
              textTransform: "none",
              fontWeight: 500,
              fontSize: "0.95rem",
              minHeight: 56,
              px: 3,
            },
            "& .MuiTab-iconWrapper": {
              mr: 1,
            },
          }}
        >
          {TABS.map((tab, index) => (
            <Tab
              key={tab.id}
              icon={tab.icon}
              iconPosition="start"
              label={tab.label}
              id={`pipeline-tab-${String(index)}`}
              aria-controls={`pipeline-tabpanel-${String(index)}`}
            />
          ))}
        </Tabs>
      </Paper>

      {/* Tab Content */}
      {TABS.map((tab, index) => {
        const TabComponent = tab.component;
        return (
          <TabPanel key={tab.id} value={tabValue} index={index}>
            <TabErrorBoundary tabName={tab.label}>
              <Suspense fallback={<TabLoadingFallback />}>
                <TabComponent />
              </Suspense>
            </TabErrorBoundary>
          </TabPanel>
        );
      })}
    </Box>
  );
}
