/**
 * DSA Photometry Plugin for JS9
 * Calculates photometry statistics (peak flux, integrated flux, RMS noise) for circular regions
 */
import { useEffect, useRef, useState, useCallback } from "react";
import {
  Paper,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
} from "@mui/material";
import { logger } from "../../../utils/logger";
import { findDisplay, isJS9Available } from "../../../utils/js9";

declare global {
  interface Window {
    JS9: any;
  }
}

interface PhotometryStats {
  peakFlux: number | null;
  integratedFlux: number | null;
  rmsNoise: number | null;
  pixelCount: number;
  regionType: string | null;
}

interface PhotometryPluginProps {
  displayId?: string;
}

/**
 * JS9 Plugin Class for Photometry
 * Follows JS9 plugin registration pattern from https://js9.si.edu/js9/help/localtasks.html
 */
class DSAPhotometryPlugin {
  private displayId: string;
  private pluginName: string = "DSA Photometry";
  private statsCallback: ((stats: PhotometryStats | null) => void) | null = null;

  constructor(displayId: string) {
    this.displayId = displayId;
  }

  /**
   * Set callback for stats updates
   */
  setStatsCallback(callback: (stats: PhotometryStats | null) => void) {
    this.statsCallback = callback;
  }

  /**
   * Calculate photometry statistics for a circular region
   */
  calculatePhotometry(region: any, imageId: string): PhotometryStats | null {
    try {
      if (!window.JS9) {
        return null;
      }

      // Get image data - JS9.GetImageData returns raw pixel data
      let imageData: any = null;
      try {
        imageData = window.JS9.GetImageData?.(imageId);
      } catch (e) {
        logger.debug("GetImageData failed, trying alternative method:", e);
      }

      // Alternative: use GetVal for individual pixels if GetImageData not available
      if (!imageData || !imageData.data) {
        // Fallback: try to get image dimensions first
        const display = findDisplay(this.displayId);
        if (!display?.im) {
          return null;
        }
        // Try to get dimensions from image object
        const im = display.im;
        if (im.width && im.height) {
          imageData = { width: im.width, height: im.height, data: null };
        } else {
          return null;
        }
      }

      const width = imageData.width;
      const height = imageData.height;
      const pixels: number[] = [];

      // Extract region parameters
      // JS9 regions: circles use 'c' or 'circle', rectangles use 'r' or 'box'
      const regionType = region.shape || region.type || region.regtype || "circle";
      let regionPixels: { x: number; y: number }[] = [];

      if (regionType === "circle" || regionType === "c") {
        // Circle region: x, y, radius (in image coordinates)
        const x = Math.round(region.x || region.xcenter || region.xc || 0);
        const y = Math.round(region.y || region.ycenter || region.yc || 0);
        const radius = Math.abs(region.radius || region.r || 0);

        if (radius <= 0) {
          return null;
        }

        // Collect pixels within circle
        const r2 = radius * radius;
        for (
          let py = Math.max(0, Math.floor(y - radius));
          py <= Math.min(height - 1, Math.ceil(y + radius));
          py++
        ) {
          for (
            let px = Math.max(0, Math.floor(x - radius));
            px <= Math.min(width - 1, Math.ceil(x + radius));
            px++
          ) {
            const dx = px - x;
            const dy = py - y;
            const dist2 = dx * dx + dy * dy;
            if (dist2 <= r2) {
              regionPixels.push({ x: px, y: py });
            }
          }
        }
      } else if (regionType === "box" || regionType === "rectangle" || regionType === "r") {
        // Rectangle region
        const x = Math.round(region.x || region.xcenter || region.xc || 0);
        const y = Math.round(region.y || region.ycenter || region.yc || 0);
        const w = Math.abs(region.width || region.w || 0);
        const h = Math.abs(region.height || region.h || 0);

        if (w <= 0 || h <= 0) {
          return null;
        }

        const x1 = Math.max(0, Math.floor(x - w / 2));
        const x2 = Math.min(width - 1, Math.ceil(x + w / 2));
        const y1 = Math.max(0, Math.floor(y - h / 2));
        const y2 = Math.min(height - 1, Math.ceil(y + h / 2));

        for (let py = y1; py <= y2; py++) {
          for (let px = x1; px <= x2; px++) {
            regionPixels.push({ x: px, y: py });
          }
        }
      } else {
        // Unsupported region type
        logger.debug("Unsupported region type for photometry:", regionType);
        return null;
      }

      if (regionPixels.length === 0) {
        return null;
      }

      // Extract pixel values
      if (imageData.data && imageData.data.length > 0) {
        // Use GetImageData if available
        const data = imageData.data;
        for (const pixel of regionPixels) {
          const idx = pixel.y * width + pixel.x;
          if (idx >= 0 && idx < data.length) {
            const value = data[idx];
            if (!isNaN(value) && isFinite(value)) {
              pixels.push(value);
            }
          }
        }
      } else {
        // Fallback: use GetVal for each pixel
        if (typeof window.JS9.GetVal === "function") {
          for (const pixel of regionPixels) {
            try {
              const value = window.JS9.GetVal(imageId, pixel.x, pixel.y);
              if (value !== null && !isNaN(value) && isFinite(value)) {
                pixels.push(value);
              }
            } catch (e) {
              // Skip invalid pixels
            }
          }
        } else {
          logger.warn("JS9.GetVal not available for pixel extraction");
          return null;
        }
      }

      if (pixels.length === 0) {
        return null;
      }

      // Calculate statistics
      const peakFlux = Math.max(...pixels);
      const integratedFlux = pixels.reduce((sum, val) => sum + val, 0);

      // Calculate RMS noise (standard deviation)
      const mean = integratedFlux / pixels.length;
      const variance =
        pixels.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / pixels.length;
      const rmsNoise = Math.sqrt(variance);

      return {
        peakFlux,
        integratedFlux,
        rmsNoise,
        pixelCount: pixels.length,
        regionType,
      };
    } catch (error) {
      logger.error("Error calculating photometry:", error);
      return null;
    }
  }

  /**
   * Handle region change events
   */
  private handleRegionChange = (im: any, reg: any) => {
    if (!im || !reg) {
      this.statsCallback?.(null);
      return;
    }

    const imageId = im.id || im;
    const stats = this.calculatePhotometry(reg, imageId);
    this.statsCallback?.(stats);
  };

  /**
   * Initialize plugin and register callbacks
   */
  init() {
    try {
      if (!window.JS9) {
        logger.warn("JS9 not available for plugin initialization");
        return;
      }

      // Register plugin with JS9
      // JS9.RegisterPlugin(class, name, constructor, {callbacks})
      if (typeof window.JS9.RegisterPlugin === "function") {
        window.JS9.RegisterPlugin(
          DSAPhotometryPlugin,
          this.pluginName,
          (displayId: string) => new DSAPhotometryPlugin(displayId),
          {
            onregionschange: this.handleRegionChange,
          }
        );
        logger.debug("DSA Photometry plugin registered");
      } else {
        // Fallback: manually set up callbacks if RegisterPlugin not available
        logger.debug("JS9.RegisterPlugin not available, using manual callback setup");
        this.setupManualCallbacks();
      }
    } catch (error) {
      logger.error("Error initializing photometry plugin:", error);
    }
  }

  /**
   * Manual callback setup if RegisterPlugin not available
   */
  private setupManualCallbacks() {
    // Set up interval to check for region changes
    // Note: JS9 doesn't have region events, so polling is necessary
    const checkInterval = setInterval(() => {
      if (!isJS9Available()) {
        clearInterval(checkInterval);
        return;
      }

      try {
        const display = findDisplay(this.displayId);

        if (display && display.im) {
          // Check for regions
          const regions = window.JS9.GetRegions(display.im.id);
          if (regions && regions.length > 0) {
            // Use the first circular region
            const circleRegion = regions.find(
              (r: any) => r.shape === "circle" || r.type === "circle" || r.type === "c"
            );
            if (circleRegion) {
              this.handleRegionChange(display.im, circleRegion);
            }
          }
        }
      } catch (error) {
        logger.debug("Error checking regions:", error);
      }
    }, 500); // Check every 500ms

    // Store interval for cleanup
    (this as any).checkInterval = checkInterval;
  }

  /**
   * Cleanup
   */
  destroy() {
    if ((this as any).checkInterval) {
      clearInterval((this as any).checkInterval);
    }
  }
}

/**
 * React component wrapper for the photometry plugin
 */
export default function PhotometryPlugin({ displayId = "skyViewDisplay" }: PhotometryPluginProps) {
  const pluginRef = useRef<DSAPhotometryPlugin | null>(null);
  const [stats, setStats] = useState<PhotometryStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isJS9Available()) {
      // Wait for JS9 to be available
      const checkJS9 = setInterval(() => {
        if (isJS9Available()) {
          clearInterval(checkJS9);
          initializePlugin();
        }
      }, 100);

      const timeout = setTimeout(() => {
        clearInterval(checkJS9);
        if (!isJS9Available()) {
          setError("JS9 not available");
        }
      }, 10000);

      return () => {
        clearInterval(checkJS9);
        clearTimeout(timeout);
      };
    } else {
      initializePlugin();
    }

    function initializePlugin() {
      try {
        // Create plugin instance
        const plugin = new DSAPhotometryPlugin(displayId);
        plugin.setStatsCallback((newStats) => {
          setStats(newStats);
          setError(null);
        });
        plugin.init();
        pluginRef.current = plugin;
      } catch (err: any) {
        logger.error("Error initializing photometry plugin:", err);
        setError(err.message || "Failed to initialize plugin");
      }
    }

    return () => {
      if (pluginRef.current) {
        pluginRef.current.destroy();
      }
    };
  }, [displayId]);

  // Poll for region changes (JS9 doesn't have region events, so polling is necessary)
  const lastRegionHashRef = useRef<string>("");
  const hasStatsRef = useRef<boolean>(false);

  const checkRegions = useCallback(() => {
    if (!isJS9Available() || !pluginRef.current) return;

    try {
      const display = findDisplay(displayId);

      if (!display || !display.im) {
        if (hasStatsRef.current) {
          setStats(null);
          hasStatsRef.current = false;
          lastRegionHashRef.current = "";
        }
        return;
      }

      // Get regions for this image
      let regions: any[] = [];
      try {
        if (typeof window.JS9.GetRegions === "function") {
          regions = window.JS9.GetRegions(display.im.id) || [];
        }
      } catch (e) {
        logger.debug("Error getting regions:", e);
      }

      // Find circular regions (prioritize circles for photometry)
      const circleRegion = regions.find((r: any) => {
        const shape = r.shape || r.type || r.regtype || "";
        return shape === "circle" || shape === "c";
      });

      // Create hash of region to detect changes
      const regionHash = circleRegion
        ? `${circleRegion.x || 0}_${circleRegion.y || 0}_${circleRegion.radius || circleRegion.r || 0}`
        : "";

      // Only update if region changed
      if (regionHash !== lastRegionHashRef.current) {
        lastRegionHashRef.current = regionHash;

        if (circleRegion && pluginRef.current) {
          // Trigger calculation
          const calculatedStats = pluginRef.current.calculatePhotometry(
            circleRegion,
            display.im.id
          );
          if (calculatedStats) {
            setStats(calculatedStats);
            setError(null);
            hasStatsRef.current = true;
          } else {
            setStats(null);
            hasStatsRef.current = false;
          }
        } else {
          setStats(null);
          hasStatsRef.current = false;
        }
      }
    } catch (err) {
      logger.debug("Error checking regions:", err);
    }
  }, [displayId]);

  useEffect(() => {
    if (!isJS9Available() || !pluginRef.current) return;

    // Poll every 500ms for region changes (JS9 doesn't have region events)
    const pollInterval = setInterval(checkRegions, 500);

    // Also check immediately
    checkRegions();

    return () => {
      clearInterval(pollInterval);
    };
  }, [checkRegions]);

  const formatValue = (value: number | null): string => {
    if (value === null || isNaN(value)) return "N/A";
    return value.toExponential(3);
  };

  return (
    <Paper sx={{ p: 2, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        DSA Photometry
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {stats ? (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>
                  <strong>Parameter</strong>
                </TableCell>
                <TableCell align="right">
                  <strong>Value</strong>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>Region Type</TableCell>
                <TableCell align="right">{stats.regionType || "N/A"}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Pixel Count</TableCell>
                <TableCell align="right">{stats.pixelCount}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Peak Flux (Jy/pixel)</TableCell>
                <TableCell align="right">{formatValue(stats.peakFlux)}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Integrated Flux (Jy)</TableCell>
                <TableCell align="right">{formatValue(stats.integratedFlux)}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>RMS Noise (Jy)</TableCell>
                <TableCell align="right">{formatValue(stats.rmsNoise)}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Box sx={{ textAlign: "center", py: 3 }}>
          <Typography variant="body2" color="text.secondary">
            Draw a circular region on the image to calculate photometry
          </Typography>
        </Box>
      )}
    </Paper>
  );
}
