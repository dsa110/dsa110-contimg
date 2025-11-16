import React, { useState } from "react";
import { Box, Typography, Tabs, Tab, Paper } from "@mui/material";
import { EventStream, EventStats } from "../components/Events";
import PageBreadcrumbs from "../components/PageBreadcrumbs";

function TabPanel(props: { children?: React.ReactNode; index: number; value: number }) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`events-tabpanel-${index}`}
      aria-labelledby={`events-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `events-tab-${index}`,
    "aria-controls": `events-tabpanel-${index}`,
  };
}

export default function EventsPage() {
  const [value, setValue] = useState(0);

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    setValue(newValue);
  };

  return (
    <>
      <PageBreadcrumbs />
      <Box sx={{ width: "100%" }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Event Bus Monitor
        </Typography>

        <Paper sx={{ mb: 3 }}>
          <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
            <Tabs value={value} onChange={handleChange} aria-label="event monitoring tabs">
              <Tab label="Event Stream" {...a11yProps(0)} />
              <Tab label="Statistics" {...a11yProps(1)} />
            </Tabs>
          </Box>

          <TabPanel value={value} index={0}>
            <EventStream />
          </TabPanel>
          <TabPanel value={value} index={1}>
            <EventStats />
          </TabPanel>
        </Paper>
      </Box>
    </>
  );
}
