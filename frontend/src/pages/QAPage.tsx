/**
 * QA Page - Unified QA visualization with toggle between Tab and CARTA views
 * Merges QAVisualizationPage and QACartaPage functionality
 */
import { useState, useEffect, useRef } from "react";
import { Box, Typography, Tabs, Tab, Paper, ToggleButton, ToggleButtonGroup, Alert } from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import {
  Folder,
  Image as ImageIcon,
  TableChart,
  NoteAdd,
  CompareArrows,
  ViewModule as CartaIcon,
  ViewList as TabIcon,
} from "@mui/icons-material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "golden-layout/dist/css/goldenlayout-base.css";
import "golden-layout/dist/css/themes/goldenlayout-dark-theme.css";
import "./QACartaPage.css"; // Custom theme overrides to match MUI dark theme
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import DirectoryBrowser from "../components/QA/DirectoryBrowser";
import FITSViewer from "../components/QA/FITSViewer";
import CasaTableViewer from "../components/QA/CasaTableViewer";
import ImageComparisonTool from "../components/ImageComparisonTool";
import QANotebookGenerator from "../components/QA/QANotebookGenerator";
import { logger } from "../utils/logger";

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

// Widget component registry for Golden Layout
const WIDGET_COMPONENTS: Record<string, React.ComponentType<any>> = {
  DirectoryBrowser,
  FITSViewer,
  CasaTableViewer,
};

// Create a QueryClient for Golden Layout components
const widgetQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
      staleTime: 30000,
    },
  },
});

// React wrapper for Golden Layout components
function WidgetWrapper({
  componentName,
  props,
  onFileSelect,
}: {
  componentName: string;
  props?: any;
  onFileSelect?: (path: string, type: string) => void;
}) {
  const Component = WIDGET_COMPONENTS[componentName];
  if (!Component) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="error">Unknown widget: {componentName}</Typography>
      </Box>
    );
  }

  const componentContent =
    componentName === "DirectoryBrowser" && onFileSelect ? (
      <Component {...props} onSelectFile={onFileSelect} />
    ) : (
      <Component {...props} />
    );

  return <QueryClientProvider client={widgetQueryClient}>{componentContent}</QueryClientProvider>;
}

export default function QAPage() {
  const [viewMode, setViewMode] = useState<"tabs" | "carta">("tabs");
  const [tabValue, setTabValue] = useState(0);
  const [selectedFITSPath, setSelectedFITSPath] = useState<string | null>(null);
  const [selectedTablePath, setSelectedTablePath] = useState<string | null>(null);
  
  // Golden Layout state
  const layoutRef = useRef<HTMLDivElement>(null);
  const goldenLayoutRef = useRef<any>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fitsViewerContainerRef = useRef<any>(null);
  const casaTableViewerContainerRef = useRef<any>(null);

  const handleFileSelect = (path: string, type: string) => {
    if (type === "fits") {
      setSelectedFITSPath(path);
      if (viewMode === "tabs") {
        setTabValue(1); // Switch to FITS viewer tab
      } else {
        // Update Golden Layout FITS viewer
        if (fitsViewerContainerRef.current) {
          fitsViewerContainerRef.current.extendState({ fitsPath: path });
        }
      }
    } else if (type === "casatable") {
      setSelectedTablePath(path);
      if (viewMode === "tabs") {
        setTabValue(2); // Switch to CASA table viewer tab
      } else {
        // Update Golden Layout CASA table viewer
        if (casaTableViewerContainerRef.current) {
          casaTableViewerContainerRef.current.extendState({ tablePath: path });
        }
      }
    }
  };

  const handleDirectorySelect = (_path: string) => {
    // Could navigate directory browser or update context
  };

  // Initialize Golden Layout when switching to CARTA mode
  useEffect(() => {
    if (viewMode !== "carta" || !layoutRef.current || isInitialized) return;

    import("golden-layout")
      .then((module) => {
        const GoldenLayout = (module as any).GoldenLayout;
        const ComponentContainer = (module as any).ComponentContainer;

        if (!GoldenLayout || !ComponentContainer) {
          throw new Error("GoldenLayout or ComponentContainer not found");
        }

        try {
          const config: any = {
            root: {
              type: "row",
              content: [
                {
                  type: "component",
                  componentType: "DirectoryBrowser",
                  title: "File Browser",
                  width: 25,
                  componentState: {
                    initialPath: "/data/dsa110-contimg/state",
                  },
                },
                {
                  type: "column",
                  width: 75,
                  content: [
                    {
                      type: "component",
                      componentType: "FITSViewer",
                      title: "FITS Viewer",
                      height: 50,
                      componentState: {
                        fitsPath: selectedFITSPath,
                      },
                    },
                    {
                      type: "component",
                      componentType: "CasaTableViewer",
                      title: "CASA Table Viewer",
                      height: 50,
                      componentState: {
                        tablePath: selectedTablePath,
                      },
                    },
                  ],
                },
              ],
            },
          };

          logger.debug("Golden Layout config:", JSON.stringify(config, null, 2));

          const componentFactory = (componentName: string) => {
            return (container: any, componentState: any) => {
              const root = document.createElement("div");
              root.style.height = "100%";
              root.style.overflow = "auto";
              container.getElement().append(root);

              import("react-dom/client").then(({ createRoot }) => {
                const reactRoot = createRoot(root);
                if (componentName === "DirectoryBrowser") {
                  reactRoot.render(
                    <WidgetWrapper
                      componentName="DirectoryBrowser"
                      props={componentState}
                      onFileSelect={handleFileSelect}
                    />
                  );
                } else if (componentName === "FITSViewer") {
                  fitsViewerContainerRef.current = container;
                  reactRoot.render(
                    <WidgetWrapper
                      componentName="FITSViewer"
                      props={{
                        ...componentState,
                        fitsPath: componentState.fitsPath || selectedFITSPath,
                      }}
                    />
                  );
                } else if (componentName === "CasaTableViewer") {
                  casaTableViewerContainerRef.current = container;
                  reactRoot.render(
                    <WidgetWrapper
                      componentName="CasaTableViewer"
                      props={{
                        ...componentState,
                        tablePath: componentState.tablePath || selectedTablePath,
                      }}
                    />
                  );
                }
              });
            };
          };

          logger.debug("Creating empty layout...");
          const layout = new GoldenLayout(layoutRef.current!);

          logger.debug("Registering components...");
          layout.registerComponentFactoryFunction(
            "DirectoryBrowser",
            componentFactory("DirectoryBrowser")
          );
          layout.registerComponentFactoryFunction("FITSViewer", componentFactory("FITSViewer"));
          layout.registerComponentFactoryFunction(
            "CasaTableViewer",
            componentFactory("CasaTableViewer")
          );

          logger.debug("Loading config...");
          if (typeof (layout as any).loadLayout === "function") {
            (layout as any).loadLayout(config);
          } else if (typeof (layout as any).loadState === "function") {
            (layout as any).loadState(config);
          } else if (typeof (layout as any).load === "function") {
            (layout as any).load(config);
          }

          goldenLayoutRef.current = layout;
          setIsInitialized(true);
          setError(null);
        } catch (initError) {
          logger.error("Failed to initialize Golden Layout:", initError);
          setError(
            `Initialization error: ${initError instanceof Error ? initError.message : String(initError)}`
          );
        }
      })
      .catch((importError) => {
        logger.error("Failed to import Golden Layout:", importError);
        setError(
          `Import error: ${importError instanceof Error ? importError.message : String(importError)}`
        );
      });

    return () => {
      if (goldenLayoutRef.current) {
        try {
          goldenLayoutRef.current.destroy();
        } catch (e) {
          logger.error("Error destroying Golden Layout:", e);
        }
        goldenLayoutRef.current = null;
        setIsInitialized(false);
      }
    };
  }, [viewMode, isInitialized, selectedFITSPath, selectedTablePath]);

  return (
    <>
      <PageBreadcrumbs />
      <Box sx={{ p: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
          <Box>
            <Typography variant="h2" component="h2" gutterBottom>
              QA Tools
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Explore QA data, view FITS files, browse CASA tables, and generate QA notebooks
            </Typography>
          </Box>
          <ToggleButtonGroup
            value={viewMode}
            exclusive
            onChange={(_, newMode) => {
              if (newMode !== null) {
                setViewMode(newMode);
                setIsInitialized(false); // Reset Golden Layout when switching
              }
            }}
            aria-label="view mode"
          >
            <ToggleButton value="tabs" aria-label="tab view">
              <TabIcon sx={{ mr: 1 }} />
              Tab View
            </ToggleButton>
            <ToggleButton value="carta" aria-label="carta view">
              <CartaIcon sx={{ mr: 1 }} />
              CARTA View
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {viewMode === "tabs" ? (
          <>
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
          </>
        ) : (
          <Box sx={{ height: "calc(100vh - 200px)", width: "100%" }}>
            <Box sx={{ p: 2, borderBottom: 1, borderColor: "divider", mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                QA Visualization (CARTA Style)
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Drag panels to rearrange, resize, and customize your workspace
              </Typography>
            </Box>
            {error && (
              <Alert severity="error" sx={{ m: 2 }}>
                <strong>Error loading Golden Layout:</strong> {error}
                <br />
                Check browser console for details.
              </Alert>
            )}
            <Box
              ref={layoutRef}
              sx={{
                height: "calc(100% - 100px)",
                width: "100%",
                position: "relative",
              }}
            />
          </Box>
        )}
      </Box>
    </>
  );
}

