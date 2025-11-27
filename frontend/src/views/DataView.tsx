/**
 * DataView - Unified Data Browsing & Analysis
 *
 * Consolidates all data-related pages into a single, organized view:
 * - Browse: File/data list browser with filtering
 * - Sources: Source catalog with variability monitoring
 * - Mosaics: Mosaic gallery and viewer
 * - Sky: Sky visualization with JS9
 * - CARTA: Advanced radio astronomy visualization
 * - QA: Quality assurance tools and inspection
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
  Storage,
  TableChart,
  Image,
  Public,
  Visibility,
  Science,
} from "@mui/icons-material";

// Lazy-load tab content components for code splitting
const BrowseTab = lazy(() => import("./data/BrowseTab"));
const SourcesTab = lazy(() => import("./data/SourcesTab"));
const MosaicsTab = lazy(() => import("./data/MosaicsTab"));
const SkyTab = lazy(() => import("./data/SkyTab"));
const CARTATab = lazy(() => import("./data/CARTATab"));
const QATab = lazy(() => import("./data/QATab"));

/** Tab configuration for the data view */
const TABS = [
  { id: "browse", label: "Browse", icon: <Storage />, component: BrowseTab },
  { id: "sources", label: "Sources", icon: <TableChart />, component: SourcesTab },
  { id: "mosaics", label: "Mosaics", icon: <Image />, component: MosaicsTab },
  { id: "sky", label: "Sky View", icon: <Public />, component: SkyTab },
  { id: "carta", label: "CARTA", icon: <Visibility />, component: CARTATab },
  { id: "qa", label: "QA Tools", icon: <Science />, component: QATab },
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
      id={`data-tabpanel-${index}`}
      aria-labelledby={`data-tab-${index}`}
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

export default function DataView() {
  const theme = useTheme();
  const [searchParams, setSearchParams] = useSearchParams();

  // Get initial tab from URL or default to "browse"
  const initialTabId = searchParams.get("tab") as TabId | null;
  const initialTabIndex = initialTabId
    ? TABS.findIndex((t) => t.id === initialTabId)
    : 0;

  const [tabValue, setTabValue] = useState(initialTabIndex >= 0 ? initialTabIndex : 0);

  // Sync URL with tab changes
  useEffect(() => {
    const tab = TABS[tabValue];
    if (tab && tab.id !== "browse") {
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
          Data
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Browse, analyze, and visualize data products
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
          aria-label="Data tabs"
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
              id={`data-tab-${index}`}
              aria-controls={`data-tabpanel-${index}`}
            />
          ))}
        </Tabs>
      </Paper>

      {/* Tab Content */}
      {TABS.map((tab, index) => {
        const TabComponent = tab.component;
        return (
          <TabPanel key={tab.id} value={tabValue} index={index}>
            <Suspense fallback={<TabLoadingFallback />}>
              <TabComponent />
            </Suspense>
          </TabPanel>
        );
      })}
    </Box>
  );
}
