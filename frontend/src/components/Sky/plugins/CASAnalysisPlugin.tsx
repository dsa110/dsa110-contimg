/**
 * DSA CASA Analysis Plugin for JS9
 * Integrates server-side CASA analysis tasks (imstat, imfit, imview, specflux, imval) into JS9 viewer
 * Reference: https://js9.si.edu/js9/help/localtasks.html
 */
import { useEffect, useRef, useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Chip,
  IconButton,
  Tooltip,
  TextField,
  Switch,
  FormControlLabel,
} from "@mui/material";
import {
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
} from "@mui/icons-material";
import { apiClient } from "../../../api/client";
import { logger } from "../../../utils/logger";
import { isJS9Available } from "../../../utils/js9";
import ContourOverlay from "./ContourOverlay";

declare global {
  interface Window {
    JS9: any;
  }
}

interface CASAnalysisResult {
  success: boolean;
  task: string;
  result?: any;
  error?: string;
  execution_time_sec?: number;
}

interface CASAnalysisPluginProps {
  displayId?: string;
  imagePath: string | null;
}

interface RegionInfo {
  shape: string;
  x?: number;
  y?: number;
  r?: number;
  width?: number;
  height?: number;
}

/**
 * JS9 Plugin Class for CASA Analysis
 * Follows JS9 plugin registration pattern from https://js9.si.edu/js9/help/localtasks.html
 */
class DSACASAnalysisPlugin {
  private displayId: string;
  private pluginName: string = "DSA CASA Analysis";
  private resultCallback: ((result: CASAnalysisResult | null) => void) | null = null;
  private currentImagePath: string | null = null;
  private regionCallback: ((region: RegionInfo | null) => void) | null = null;

  constructor(displayId: string) {
    this.displayId = displayId;
  }

  /**
   * Set callback for analysis results
   */
  setResultCallback(callback: (result: CASAnalysisResult | null) => void) {
    this.resultCallback = callback;
  }

  /**
   * Set callback for region updates
   */
  setRegionCallback(callback: (region: RegionInfo | null) => void) {
    this.regionCallback = callback;
  }

  /**
   * Set current image path
   */
  setImagePath(imagePath: string | null) {
    this.currentImagePath = imagePath;
  }

  /**
   * Get current image path from JS9 display
   */
  getCurrentImagePath(): string | null {
    if (!window.JS9) return null;

    try {
      const display = window.JS9.displays?.find((d: any) => {
        const divId = d.id || d.display || d.divID;
        return divId === this.displayId;
      });

      if (display && display.im) {
        const imageId = display.im.id;
        const imageInfo = window.JS9.GetImageData?.(imageId);
        if (imageInfo && imageInfo.file) {
          return imageInfo.file;
        }
        const fitsHeader = window.JS9.GetFITSheader?.(imageId);
        if (fitsHeader && fitsHeader.FILENAME) {
          return fitsHeader.FILENAME;
        }
      }
    } catch (error) {
      logger.warn("Error getting image path from JS9:", error);
    }

    return this.currentImagePath;
  }

  /**
   * Get current region from JS9 display
   */
  getCurrentRegion(): RegionInfo | null {
    if (!window.JS9) return null;

    try {
      const display = window.JS9.displays?.find((d: any) => {
        const divId = d.id || d.display || d.divID;
        return divId === this.displayId;
      });

      if (display && display.im) {
        const imageId = display.im.id;
        const regions = window.JS9.GetRegions?.(imageId);
        if (regions && regions.length > 0) {
          const region = regions[regions.length - 1];
          return {
            shape: region.shape || region.type || "circle",
            x: region.x || region.xcen,
            y: region.y || region.ycen,
            r: region.r || region.radius,
            width: region.width,
            height: region.height,
          };
        }
      }
    } catch (error) {
      logger.warn("Error getting region from JS9:", error);
    }

    return null;
  }

  /**
   * Update region callback
   */
  updateRegion() {
    if (this.regionCallback) {
      this.regionCallback(this.getCurrentRegion());
    }
  }

  /**
   * Execute CASA analysis task
   */
  async executeAnalysis(
    task: string,
    region?: RegionInfo | null,
    parameters?: Record<string, any>
  ): Promise<void> {
    if (!this.resultCallback) {
      logger.warn("No result callback set for CASA analysis");
      return;
    }

    const imagePath = this.getCurrentImagePath();
    if (!imagePath) {
      this.resultCallback({
        success: false,
        task,
        error: "No image loaded in JS9 viewer",
      });
      return;
    }

    const activeRegion = region || this.getCurrentRegion();

    try {
      this.resultCallback({
        success: false,
        task,
        error: undefined,
      });

      const response = await apiClient.post<CASAnalysisResult>("/api/visualization/js9/analysis", {
        task,
        image_path: imagePath,
        region: activeRegion || undefined,
        parameters: parameters || {},
      });

      this.resultCallback(response.data);
      return response.data;
    } catch (error: any) {
      logger.error("Error executing CASA analysis:", error);
      this.resultCallback({
        success: false,
        task,
        error: error.response?.data?.detail || error.message || "Unknown error",
      });
    }
  }

  /**
   * Initialize plugin and register with JS9
   */
  init() {
    try {
      if (!window.JS9) {
        logger.warn("JS9 not available for plugin initialization");
        return;
      }

      if (typeof window.JS9.AddAnalysis === "function") {
        const tasks = [
          { name: "Image Statistics", task: "imstat" },
          { name: "Source Fitting", task: "imfit" },
          { name: "Contour Generation", task: "imview" },
          { name: "Spectral Flux", task: "specflux" },
          { name: "Pixel Extraction", task: "imval" },
          { name: "Image Header", task: "imhead" },
          { name: "Image Math", task: "immath" },
        ];

        tasks.forEach(({ name, task }) => {
          window.JS9.AddAnalysis({
            name: `CASA: ${name}`,
            menu: "Analysis",
            callback: () => {
              this.executeAnalysis(task);
            },
          });
        });

        logger.debug("DSA CASA Analysis plugin registered with JS9");
      }
    } catch (error) {
      logger.error("Error initializing CASA analysis plugin:", error);
    }
  }

  destroy() {
    // Cleanup if needed
  }
}

/**
 * React component wrapper for the CASA analysis plugin
 */
export default function CASAnalysisPlugin({
  displayId = "skyViewDisplay",
  imagePath,
}: CASAnalysisPluginProps) {
  const pluginRef = useRef<DSACASAnalysisPlugin | null>(null);
  const [result, setResult] = useState<CASAnalysisResult | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<string>("imstat");
  const [loading, setLoading] = useState(false);
  const [currentRegion, setCurrentRegion] = useState<RegionInfo | null>(null);
  const [useRegion, setUseRegion] = useState(true);
  const [regionPolling, setRegionPolling] = useState(false);
  const [showContours, setShowContours] = useState(false);
  const [contourData, setContourData] = useState<any>(null);
  const [selectedRegions, setSelectedRegions] = useState<RegionInfo[]>([]);
  const [batchMode, setBatchMode] = useState(false);
  const [batchResults, setBatchResults] = useState<CASAnalysisResult[]>([]);
  const [batchLoading, setBatchLoading] = useState(false);

  useEffect(() => {
    if (!isJS9Available()) {
      const checkJS9 = setInterval(() => {
        if (isJS9Available()) {
          clearInterval(checkJS9);
          initializePlugin();
        }
      }, 100);

      const timeout = setTimeout(() => {
        clearInterval(checkJS9);
        if (!isJS9Available()) {
          logger.warn("JS9 not available after timeout");
        }
      }, 10000);

      return () => {
        clearInterval(checkJS9);
        clearTimeout(timeout);
      };
    } else {
      initializePlugin();
    }

    return () => {
      if (pluginRef.current) {
        pluginRef.current.destroy();
      }
    };
  }, []);

  useEffect(() => {
    if (pluginRef.current) {
      pluginRef.current.setImagePath(imagePath);
    }
  }, [imagePath]);

  useEffect(() => {
    if (regionPolling && pluginRef.current) {
      const interval = setInterval(() => {
        pluginRef.current?.updateRegion();
      }, 500);
      return () => clearInterval(interval);
    }
  }, [regionPolling]);

  const initializePlugin = () => {
    try {
      if (!window.JS9) return;

      const display = window.JS9.displays?.find((d: any) => {
        const divId = d.id || d.display || d.divID;
        return divId === displayId;
      });

      if (!display) {
        logger.debug("JS9 display not found, waiting...");
        setTimeout(initializePlugin, 500);
        return;
      }

      pluginRef.current = new DSACASAnalysisPlugin(displayId);
      pluginRef.current.setResultCallback((analysisResult) => {
        setResult(analysisResult);
        if (analysisResult) {
          setDialogOpen(true);
          setLoading(analysisResult.error === undefined && !analysisResult.success);

          // If imview task and successful, extract contour data
          if (analysisResult.success && analysisResult.task === "imview" && analysisResult.result) {
            if (analysisResult.result.contour_paths) {
              setContourData(analysisResult.result);
              setShowContours(true);
            }
          }
        }
      });
      pluginRef.current.setRegionCallback((region) => {
        setCurrentRegion(region);
      });
      pluginRef.current.setImagePath(imagePath);
      pluginRef.current.init();
      pluginRef.current.updateRegion();
    } catch (error) {
      logger.error("Error initializing CASA analysis plugin:", error);
    }
  };

  const handleExecute = async () => {
    if (!pluginRef.current) return;

    setLoading(true);
    setResult(null);
    setDialogOpen(true);

    await pluginRef.current.executeAnalysis(selectedTask, useRegion ? currentRegion : null);
  };

  const handleClose = () => {
    setDialogOpen(false);
    setResult(null);
    setLoading(false);
  };

  const handleRefreshRegion = () => {
    pluginRef.current?.updateRegion();
  };

  const exportToJSON = () => {
    if (!result || !result.result) return;

    const dataStr = JSON.stringify(result, null, 2);
    const dataBlob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `casa_analysis_${result.task}_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportToCSV = () => {
    if (!result || !result.result) return;

    let csv = "";
    const data = result.result;

    // Try to convert result to CSV format
    if (data.DATA && typeof data.DATA === "object") {
      // imstat format
      const stats = data.DATA;
      csv = "Statistic,Value\n";
      for (const [key, value] of Object.entries(stats)) {
        csv += `${key},${value}\n`;
      }
    } else if (Array.isArray(data.values)) {
      // imval format
      csv = "Index,Value\n";
      data.values.forEach((val: any, idx: number) => {
        csv += `${idx},${val}\n`;
      });
    } else {
      // Generic format
      csv = "Key,Value\n";
      const flatten = (obj: any, prefix = "") => {
        for (const [key, value] of Object.entries(obj)) {
          const newKey = prefix ? `${prefix}.${key}` : key;
          if (typeof value === "object" && value !== null && !Array.isArray(value)) {
            flatten(value, newKey);
          } else {
            csv += `${newKey},${value}\n`;
          }
        }
      };
      flatten(data);
    }

    const dataBlob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `casa_analysis_${result.task}_${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const formatResult = (result: any): string => {
    if (typeof result === "string") {
      return result;
    }
    if (typeof result === "object") {
      return JSON.stringify(result, null, 2);
    }
    return String(result);
  };

  const renderResult = () => {
    if (!result) return null;

    if (result.error === undefined && !result.success) {
      return (
        <Box display="flex" justifyContent="center" alignItems="center" p={3}>
          <CircularProgress />
          <Typography variant="body2" sx={{ ml: 2 }}>
            Executing CASA task...
          </Typography>
        </Box>
      );
    }

    if (result.error) {
      return (
        <Alert severity="error" sx={{ mt: 2 }}>
          <Typography variant="subtitle2">Error</Typography>
          <Typography variant="body2">{result.error}</Typography>
        </Alert>
      );
    }

    if (result.result) {
      const data = result.result;
      const isCached = result.execution_time_sec !== undefined && result.execution_time_sec < 0.01;

      // Render table for imstat results
      if (data.DATA && typeof data.DATA === "object" && selectedTask === "imstat") {
        const stats = data.DATA;
        return (
          <Box sx={{ mt: 2 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
              <Typography variant="subtitle2">Image Statistics</Typography>
              {isCached && (
                <Chip
                  icon={<CheckCircleIcon />}
                  label="Cached"
                  size="small"
                  color="success"
                  variant="outlined"
                />
              )}
            </Box>
            {result.execution_time_sec !== undefined && result.execution_time_sec >= 0.01 && (
              <Typography variant="caption" color="text.secondary" gutterBottom>
                Execution time: {result.execution_time_sec}s
              </Typography>
            )}
            <TableContainer component={Paper} sx={{ mt: 2, maxHeight: 400 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell>
                      <strong>Statistic</strong>
                    </TableCell>
                    <TableCell align="right">
                      <strong>Value</strong>
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.entries(stats).map(([key, value]) => (
                    <TableRow key={key}>
                      <TableCell>{key}</TableCell>
                      <TableCell align="right">
                        {typeof value === "number" ? value.toLocaleString() : String(value)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        );
      }

      // Default JSON display
      return (
        <Box sx={{ mt: 2 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="subtitle2">Results ({result.task})</Typography>
            {isCached && (
              <Chip
                icon={<CheckCircleIcon />}
                label="Cached"
                size="small"
                color="success"
                variant="outlined"
              />
            )}
          </Box>
          {result.execution_time_sec !== undefined && result.execution_time_sec >= 0.01 && (
            <Typography variant="caption" color="text.secondary" gutterBottom>
              Execution time: {result.execution_time_sec}s
            </Typography>
          )}
          <Paper sx={{ mt: 2, p: 2, maxHeight: 400, overflow: "auto" }}>
            <pre style={{ margin: 0, fontSize: "0.875rem" }}>{formatResult(result.result)}</pre>
          </Paper>
        </Box>
      );
    }

    return null;
  };

  const handleBatchAnalysis = async () => {
    if (!pluginRef.current || selectedRegions.length === 0) return;

    setBatchLoading(true);
    setBatchResults([]);
    setDialogOpen(true);

    const results: CASAnalysisResult[] = [];

    try {
      // Process regions in parallel batches for performance
      const batchSize = 5; // Process 5 regions at a time
      for (let i = 0; i < selectedRegions.length; i += batchSize) {
        const batch = selectedRegions.slice(i, i + batchSize);
        const batchPromises = batch.map((region) =>
          pluginRef.current!.executeAnalysis(selectedTask, region)
        );
        const batchResults = await Promise.all(batchPromises);
        results.push(...batchResults.filter((r) => r !== null && r !== undefined));

        // Update UI with progress
        setBatchResults([...results]);
      }
      setBatchResults(results);
    } catch (error) {
      logger.error("Error in batch analysis:", error);
    } finally {
      setBatchLoading(false);
    }
  };

  const getAllRegions = (): RegionInfo[] => {
    if (!window.JS9) return [];
    try {
      const display = window.JS9.displays?.find((d: any) => {
        const divId = d.id || d.display || d.divID;
        return divId === displayId;
      });
      if (!display?.im) return [];

      const regions = window.JS9.GetRegions(display.im.id);
      if (!regions || !Array.isArray(regions)) return [];

      return regions.map((r: any) => ({
        shape: r.shape || "circle",
        x: r.x,
        y: r.y,
        r: r.r,
        width: r.width,
        height: r.height,
      }));
    } catch (e) {
      logger.error("Error getting all regions:", e);
      return [];
    }
  };

  return (
    <>
      {/* Contour Overlay */}
      {showContours && contourData && (
        <ContourOverlay
          displayId={displayId}
          contourData={contourData}
          visible={showContours}
          color="cyan"
          lineWidth={1}
          opacity={0.7}
        />
      )}

      <Box sx={{ mb: 2 }}>
        <Box display="flex" gap={1} flexWrap="wrap" alignItems="center" mb={1}>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel id="casa-task-label">CASA Task</InputLabel>
            <Select
              value={selectedTask}
              labelId="casa-task-label"
              onChange={(e) => setSelectedTask(e.target.value)}
            >
              <MenuItem value="imstat">Image Statistics</MenuItem>
              <MenuItem value="imfit">Source Fitting</MenuItem>
              <MenuItem value="imview">Contour Generation</MenuItem>
              <MenuItem value="specflux">Spectral Flux</MenuItem>
              <MenuItem value="imval">Pixel Extraction</MenuItem>
              <MenuItem value="imhead">Image Header</MenuItem>
              <MenuItem value="immath">Image Math</MenuItem>
            </Select>
          </FormControl>

          <FormControlLabel
            control={
              <Switch
                checked={useRegion}
                onChange={(e) => setUseRegion(e.target.checked)}
                size="small"
              />
            }
            label="Use Region"
          />

          {currentRegion && (
            <Chip label={`${currentRegion.shape} region`} size="small" variant="outlined" />
          )}

          <Tooltip title="Refresh region from JS9">
            <IconButton size="small" onClick={handleRefreshRegion}>
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Button
            variant="contained"
            onClick={handleExecute}
            disabled={!imagePath || loading}
            size="small"
          >
            Run Analysis
          </Button>

          {selectedTask === "imview" && result?.success && contourData && (
            <FormControlLabel
              control={
                <Switch
                  checked={showContours}
                  onChange={(e) => setShowContours(e.target.checked)}
                  size="small"
                />
              }
              label="Show Contours"
            />
          )}

          <FormControlLabel
            control={
              <Switch
                checked={batchMode}
                onChange={(e) => {
                  setBatchMode(e.target.checked);
                  if (e.target.checked) {
                    setSelectedRegions(getAllRegions());
                  } else {
                    setSelectedRegions([]);
                  }
                }}
                size="small"
              />
            }
            label="Batch Mode"
          />

          {batchMode && (
            <Button
              variant="outlined"
              onClick={handleBatchAnalysis}
              disabled={!imagePath || batchLoading || selectedRegions.length === 0}
              size="small"
            >
              Analyze {selectedRegions.length} Regions
            </Button>
          )}
        </Box>

        {currentRegion && useRegion && (
          <Box sx={{ mt: 1, fontSize: "0.75rem", color: "text.secondary" }}>
            Region: {currentRegion.shape} at ({currentRegion.x?.toFixed(1)},{" "}
            {currentRegion.y?.toFixed(1)}){currentRegion.r && `, r=${currentRegion.r.toFixed(1)}`}
          </Box>
        )}
      </Box>

      <Dialog open={dialogOpen} onClose={handleClose} maxWidth="md" fullWidth>
        <DialogTitle>
          CASA Analysis Results
          {result && result.success && (
            <Box display="flex" gap={1} mt={1}>
              <Button
                startIcon={<DownloadIcon />}
                onClick={exportToJSON}
                size="small"
                variant="outlined"
              >
                Export JSON
              </Button>
              <Button
                startIcon={<DownloadIcon />}
                onClick={exportToCSV}
                size="small"
                variant="outlined"
              >
                Export CSV
              </Button>
            </Box>
          )}
        </DialogTitle>
        <DialogContent>
          {batchMode && batchLoading && (
            <Box display="flex" flexDirection="column" alignItems="center" p={3}>
              <CircularProgress />
              <Typography variant="body2" sx={{ mt: 2 }}>
                Processing {batchResults.length} of {selectedRegions.length} regions...
              </Typography>
            </Box>
          )}
          {batchMode && batchResults.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Batch Results ({batchResults.length} regions)
              </Typography>
              <TableContainer component={Paper} sx={{ mt: 1, maxHeight: 400 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>
                        <strong>Region</strong>
                      </TableCell>
                      <TableCell>
                        <strong>Status</strong>
                      </TableCell>
                      <TableCell align="right">
                        <strong>Time (s)</strong>
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {batchResults.map((result, idx) => (
                      <TableRow key={idx}>
                        <TableCell>Region {idx + 1}</TableCell>
                        <TableCell>
                          {result.success ? (
                            <Chip label="Success" size="small" color="success" />
                          ) : (
                            <Chip label="Error" size="small" color="error" />
                          )}
                        </TableCell>
                        <TableCell align="right">
                          {result.execution_time_sec?.toFixed(3) || "-"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}
          {!batchMode && loading && (
            <Box display="flex" justifyContent="center" alignItems="center" p={3}>
              <CircularProgress />
              <Typography variant="body2" sx={{ ml: 2 }}>
                Executing CASA task...
              </Typography>
            </Box>
          )}
          {!batchMode && renderResult()}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
