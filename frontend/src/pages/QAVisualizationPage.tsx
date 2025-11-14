/**
 * QA Visualization Page - Main page for QA data visualization and exploration
 */
import { useState } from "react";
import { Box, Typography, Tabs, Tab, Paper, Grid } from "@mui/material";
import {
  Folder,
  Image as ImageIcon,
  TableChart,
  NoteAdd,
  CompareArrows,
} from "@mui/icons-material";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import DirectoryBrowser from "../components/QA/DirectoryBrowser";
import FITSViewer from "../components/QA/FITSViewer";
import CasaTableViewer from "../components/QA/CasaTableViewer";
import ImageComparisonTool from "../components/ImageComparisonTool";
import QANotebookGenerator from "../components/QA/QANotebookGenerator";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index } = props;
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ p: 2 }}>{children}</Box>}
    </div>
  );
}

export default function QAVisualizationPage() {
  const [tabValue, setTabValue] = useState(0);
  const [selectedFITSPath, setSelectedFITSPath] = useState<string | null>(null);
  const [selectedTablePath, setSelectedTablePath] = useState<string | null>(null);

  const handleFileSelect = (path: string, type: string) => {
    if (type === "fits") {
      setSelectedFITSPath(path);
      setTabValue(1); // Switch to FITS viewer tab
    } else if (type === "casatable") {
      setSelectedTablePath(path);
      setTabValue(2); // Switch to CASA table viewer tab
    }
  };

  const handleDirectorySelect = (_path: string) => {
    // Could navigate directory browser or update context
  };

  return (
    <>
      <PageBreadcrumbs />
      <Box sx={{ p: 3 }}>
        <Typography variant="h2" component="h2" gutterBottom>
          QA Visualization
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Explore QA data, view FITS files, browse CASA tables, and generate QA notebooks
        </Typography>

        <Paper sx={{ mb: 2 }}>
          <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
            <Tab
              icon={<Folder />}
              iconPosition="start"
              label="Directory Browser"
              sx={{ textTransform: "none" }}
            />
            <Tab
              icon={<ImageIcon />}
              iconPosition="start"
              label="FITS Viewer"
              sx={{ textTransform: "none" }}
            />
            <Tab
              icon={<TableChart />}
              iconPosition="start"
              label="CASA Table Viewer"
              sx={{ textTransform: "none" }}
            />
            <Tab
              icon={<NoteAdd />}
              iconPosition="start"
              label="Notebook Generator"
              sx={{ textTransform: "none" }}
            />
            <Tab
              icon={<CompareArrows />}
              iconPosition="start"
              label="Image Comparison"
              sx={{ textTransform: "none" }}
            />
          </Tabs>
        </Paper>

        <TabPanel value={tabValue} index={0}>
          <DirectoryBrowser
            onSelectFile={handleFileSelect}
            onSelectDirectory={handleDirectorySelect}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4} {...({} as any)}>
              <DirectoryBrowser
                initialPath="/data/dsa110-contimg/state/images"
                onSelectFile={(path, type) => {
                  if (type === "fits") {
                    setSelectedFITSPath(path);
                  }
                }}
              />
            </Grid>
            <Grid item xs={12} md={8} {...({} as any)}>
              <FITSViewer fitsPath={selectedFITSPath} />
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4} {...({} as any)}>
              <DirectoryBrowser
                initialPath="/data/dsa110-contimg/state/ms"
                onSelectFile={(path, type) => {
                  if (type === "casatable") {
                    setSelectedTablePath(path);
                  }
                }}
              />
            </Grid>
            <Grid item xs={12} md={8} {...({} as any)}>
              <CasaTableViewer tablePath={selectedTablePath} />
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <QANotebookGenerator />
        </TabPanel>
        <TabPanel value={tabValue} index={4}>
          <ImageComparisonTool />
        </TabPanel>
      </Box>
    </>
  );
}
