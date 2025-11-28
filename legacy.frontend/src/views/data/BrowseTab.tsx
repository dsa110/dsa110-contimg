/**
 * Data Browse Tab
 *
 * File and data list browser:
 * - Data instances list with filtering
 * - File browser
 * - Batch job monitor
 */
import React, { useState } from "react";
import { Box, Tabs, Tab, Paper } from "@mui/material";
import { usePipelineStatus } from "../../api/queries";
import { DataList } from "../../components/DataBrowser/DataList";
import { FileBrowser } from "../../components/DataBrowser/FileBrowser";
import { BatchJobMonitor } from "../../components/DataBrowser/BatchJobMonitor";

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
      id={`browse-tabpanel-${String(index)}`}
      aria-labelledby={`browse-tab-${String(index)}`}
      sx={{ py: 2 }}
    >
      {value === index && children}
    </Box>
  );
}

export default function BrowseTab() {
  const [tabValue, setTabValue] = useState(0);
  // Pipeline status is available if needed for future use
  usePipelineStatus();

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Box>
      <Paper sx={{ mb: 2 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          aria-label="Data browser tabs"
        >
          <Tab label="Data Products" />
          <Tab label="File Browser" />
          <Tab label="Batch Jobs" />
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        <DataList />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <FileBrowser />
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <BatchJobMonitor />
      </TabPanel>
    </Box>
  );
}
