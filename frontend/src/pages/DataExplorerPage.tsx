/**
 * Data Explorer Page
 * Consolidated view of Data Browser, Mosaics, Sources, and Sky View
 */
import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Container, Typography, Box, Tabs, Tab, Button, Stack } from "@mui/material";
import {
  Storage as BrowserIcon,
  GridOn as MosaicsIcon,
  TableChart as SourcesIcon,
  Public as SkyIcon,
  ViewModule as WorkspaceIcon,
} from "@mui/icons-material";
import DataBrowserPage from "./DataBrowserPage";
import MosaicGalleryPage from "./MosaicGalleryPage";
import SourceMonitoringPage from "./SourceMonitoringPage";
import SkyViewPage from "./SkyViewPage";
import UnifiedWorkspace from "../components/UnifiedWorkspace";
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
      id={`data-explorer-tabpanel-${index}`}
      aria-labelledby={`data-explorer-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export default function DataExplorerPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = parseInt(searchParams.get("tab") || "0", 10);
  const [tabValue, setTabValue] = useState(initialTab);
  const [workspaceMode, setWorkspaceMode] = useState(false);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);

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

  const handleSourceSelect = (sourceId: string) => {
    setSelectedSource(sourceId);
    // Optionally switch to sky view when source is selected
    // setTabValue(3);
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Stack spacing={2} sx={{ mb: 3 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Typography variant="h1" component="h1">
            Data Explorer
          </Typography>
          <Button
            variant="outlined"
            startIcon={<WorkspaceIcon />}
            onClick={() => setWorkspaceMode(!workspaceMode)}
          >
            {workspaceMode ? "Tab View" : "Workspace View"}
          </Button>
        </Box>
        <UnifiedSearch placeholder="Search data, sources, mosaics, sky view..." />
      </Stack>

      {workspaceMode ? (
        <Box sx={{ height: "calc(100vh - 200px)", minHeight: "600px" }}>
          <UnifiedWorkspace
            views={[
              {
                id: "sources",
                title: "Sources",
                component: <SourceMonitoringPage />,
                closable: false,
              },
              {
                id: "sky",
                title: "Sky View",
                component: <SkyViewPage />,
                closable: false,
              },
              {
                id: "browser",
                title: "Data Browser",
                component: <DataBrowserPage />,
                closable: false,
              },
            ]}
            defaultLayout="split-horizontal"
          />
        </Box>
      ) : (
        <>
          <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 3 }}>
            <Tab label="Browser" icon={<BrowserIcon />} iconPosition="start" />
            <Tab label="Mosaics" icon={<MosaicsIcon />} iconPosition="start" />
            <Tab label="Sources" icon={<SourcesIcon />} iconPosition="start" />
            <Tab label="Sky View" icon={<SkyIcon />} iconPosition="start" />
          </Tabs>

          <TabPanel value={tabValue} index={0}>
            <Box sx={{ mt: -4 }}>
              <DataBrowserPage />
            </Box>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <Box sx={{ mt: -4 }}>
              <MosaicGalleryPage />
            </Box>
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <Box sx={{ mt: -4 }}>
              <SourceMonitoringPage />
            </Box>
          </TabPanel>

          <TabPanel value={tabValue} index={3}>
            <Box sx={{ mt: -4 }}>
              <SkyViewPage />
            </Box>
          </TabPanel>
        </>
      )}
    </Container>
  );
}
