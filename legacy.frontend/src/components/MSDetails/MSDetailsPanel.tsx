/**
 * MS Details Panel
 * Collapsible panel containing MS inspection, comparison, and related products tabs
 */
import { useState, useEffect } from "react";
import { Box, Paper, Tabs, Tab, IconButton, Collapse, Typography } from "@mui/material";
import { ExpandMore, ExpandLess, Info, CompareArrows, Assessment } from "@mui/icons-material";
import { MSInspectionPanel } from "./MSInspectionPanel";
import { MSComparisonPanel } from "./MSComparisonPanel";
import { RelatedProductsPanel } from "./RelatedProductsPanel";
import type { MSMetadata, MSListEntry } from "../../api/types";

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

interface MSDetailsPanelProps {
  selectedMS: string;
  metadata: MSMetadata | undefined;
  onMSSelect: (ms: MSListEntry) => void;
  defaultExpanded?: boolean;
}

export function MSDetailsPanel({
  selectedMS,
  metadata,
  onMSSelect,
  defaultExpanded = false,
}: MSDetailsPanelProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [tabValue, setTabValue] = useState(0);

  // Auto-expand when MS is selected
  useEffect(() => {
    if (selectedMS && !expanded) {
      setExpanded(true);
    }
  }, [selectedMS, expanded]);

  // Load expanded state from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("msDetailsPanelExpanded");
    if (saved !== null) {
      setExpanded(saved === "true");
    }
  }, []);

  // Save expanded state to localStorage
  const handleToggle = () => {
    const newExpanded = !expanded;
    setExpanded(newExpanded);
    localStorage.setItem("msDetailsPanelExpanded", String(newExpanded));
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  if (!selectedMS && !expanded) {
    return null;
  }

  return (
    <Paper id="ms-details-panel" sx={{ mt: 2 }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          p: 2,
          borderBottom: expanded ? 1 : 0,
          borderColor: "divider",
          cursor: "pointer",
        }}
        onClick={handleToggle}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <IconButton
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              handleToggle();
            }}
          >
            {expanded ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
          <Typography variant="h6">MS Details</Typography>
          {selectedMS && (
            <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
              {selectedMS.split("/").pop()}
            </Typography>
          )}
        </Box>
        {!selectedMS && (
          <Typography variant="body2" color="text.secondary">
            Select an MS to view details
          </Typography>
        )}
      </Box>
      <Collapse in={expanded}>
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="MS Inspection" icon={<Info />} iconPosition="start" />
            <Tab label="MS Comparison" icon={<CompareArrows />} iconPosition="start" />
            <Tab label="Related Products" icon={<Assessment />} iconPosition="start" />
          </Tabs>
        </Box>

        <Box sx={{ p: 3 }}>
          <TabPanel value={tabValue} index={0}>
            <MSInspectionPanel msPath={selectedMS} metadata={metadata} />
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <MSComparisonPanel selectedMS={selectedMS} onMSSelect={onMSSelect} />
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <RelatedProductsPanel msPath={selectedMS} />
          </TabPanel>
        </Box>
      </Collapse>
    </Paper>
  );
}
