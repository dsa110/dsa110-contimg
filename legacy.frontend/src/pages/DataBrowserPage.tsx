import React, { useState } from "react";
import { Container, Typography, Box, Card, CardContent, Tabs, Tab, Alert } from "@mui/material";
import { usePipelineStatus } from "../api/queries";
import { DataList } from "../components/DataBrowser/DataList";
import { FileBrowser } from "../components/DataBrowser/FileBrowser";
import { BatchJobMonitor } from "../components/DataBrowser/BatchJobMonitor";
import QAPage from "../pages/QAPage";
import CARTAPage from "../pages/CARTAPage";
import PageBreadcrumbs from "../components/PageBreadcrumbs";

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
      id={`data-browser-tabpanel-${index}`}
      aria-labelledby={`data-browser-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export default function DataBrowserPage() {
  const [tabValue, setTabValue] = useState(0);
  const { error: statusError } = usePipelineStatus();

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <PageBreadcrumbs />
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Data Browser
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Browse, search, and manage telescope data products
        </Typography>
      </Box>

      {statusError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Error connecting to pipeline API. Some features may be unavailable.
        </Alert>
      )}

      <Card sx={{ mb: 3 }}>
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs
            value={tabValue}
            onChange={handleTabChange}
            aria-label="data browser tabs"
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab label="Data Products" />
            <Tab label="File System" />
            <Tab label="Batch Jobs" />
            <Tab label="QA Tools" />
            <Tab label="CARTA" />
          </Tabs>
        </Box>
        <CardContent>
          <TabPanel value={tabValue} index={0}>
            <DataList />
          </TabPanel>
          <TabPanel value={tabValue} index={1}>
            <FileBrowser />
          </TabPanel>
          <TabPanel value={tabValue} index={2}>
            <BatchJobMonitor />
          </TabPanel>
          <TabPanel value={tabValue} index={3}>
            <QAPage embedded={true} />
          </TabPanel>
          <TabPanel value={tabValue} index={4}>
            <CARTAPage embedded={true} />
          </TabPanel>
        </CardContent>
      </Card>
    </Container>
  );
}
