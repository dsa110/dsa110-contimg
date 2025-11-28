import React, { useState } from "react";
import { Box, Typography, Tabs, Tab, Paper, Button } from "@mui/material";
import { CacheStats, CacheKeys, CachePerformance } from "../components/Cache";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { ConfirmationDialog } from "../components/ConfirmationDialog";
import PageBreadcrumbs from "../components/PageBreadcrumbs";

function TabPanel(props: { children?: React.ReactNode; index: number; value: number }) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`cache-tabpanel-${index}`}
      aria-labelledby={`cache-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `cache-tab-${index}`,
    "aria-controls": `cache-tabpanel-${index}`,
  };
}

export default function CachePage() {
  const [value, setValue] = useState(0);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const queryClient = useQueryClient();

  const clearCacheMutation = useMutation({
    mutationFn: async () => {
      await apiClient.delete("/cache/clear");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cache"] });
      setClearDialogOpen(false);
    },
  });

  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    setValue(newValue);
  };

  const handleClearCache = () => {
    clearCacheMutation.mutate();
  };

  return (
    <>
      <PageBreadcrumbs />
      <Box sx={{ width: "100%" }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h4" component="h1">
            Cache Statistics
          </Typography>
          <Button variant="outlined" color="error" onClick={() => setClearDialogOpen(true)}>
            Clear All Cache
          </Button>
        </Box>

        <Paper sx={{ mb: 3 }}>
          <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
            <Tabs value={value} onChange={handleChange} aria-label="cache monitoring tabs">
              <Tab label="Statistics" {...a11yProps(0)} />
              <Tab label="Keys" {...a11yProps(1)} />
              <Tab label="Performance" {...a11yProps(2)} />
            </Tabs>
          </Box>

          <TabPanel value={value} index={0}>
            <CacheStats />
          </TabPanel>
          <TabPanel value={value} index={1}>
            <CacheKeys />
          </TabPanel>
          <TabPanel value={value} index={2}>
            <CachePerformance />
          </TabPanel>
        </Paper>

        {/* Clear Cache Confirmation Dialog */}
        <ConfirmationDialog
          open={clearDialogOpen}
          onClose={() => setClearDialogOpen(false)}
          onConfirm={handleClearCache}
          title="Clear All Cache"
          message="Are you sure you want to clear all cache? This action cannot be undone."
          severity="error"
          confirmText="Clear All"
          loading={clearCacheMutation.isPending}
        />
      </Box>
    </>
  );
}
