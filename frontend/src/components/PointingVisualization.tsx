/**
 * Pointing Visualization Component
 * Live sky map showing DSA-110 telescope pointing position and history
 */
import { useMemo, useEffect, useState, useCallback } from "react";
import {
  Paper,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Chip,
  Stack,
  Tooltip,
} from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import { RadioButtonChecked as PointIcon, Refresh as RefreshIcon } from "@mui/icons-material";
import { PlotlyLazy } from "./PlotlyLazy";
import type { Data, Layout } from "./PlotlyLazy";
import { usePointingMonitorStatus, usePointingHistory, useImages } from "../api/queries";
import { logger } from "../utils/logger";

interface PointingVisualizationProps {
  height?: number;
  showHistory?: boolean;
  historyDays?: number;
  enableSkyMapBackground?: boolean; // Enable radio sky map background (default: true)
}

export default function PointingVisualization({
  height = 500,
  showHistory = true,
  historyDays, // undefined = full range
  enableSkyMapBackground = false, // Disabled by default (backend not working)
}: PointingVisualizationProps) {
  const { data: monitorStatus, isLoading: statusLoading } = usePointingMonitorStatus();
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Calculate MJD range for history - use reasonable default (30 days) if historyDays is null/undefined or very large
  const { startMjd, endMjd, useFullRange, effectiveHistoryDays } = useMemo(() => {
    if (!showHistory) {
      return { startMjd: 0, endMjd: 0, useFullRange: false, effectiveHistoryDays: null };
    }

    // If historyDays is very large (>1000) or undefined, use last 30 days as default
    // This prevents querying 80k+ files which causes API timeouts
    const effectiveHistoryDays = !historyDays || historyDays > 1000 ? 30 : historyDays;

    const now = new Date();
    const startDate = new Date(now.getTime() - effectiveHistoryDays * 24 * 60 * 60 * 1000);
    // Convert to MJD (Unix epoch to MJD offset is 40587)
    const startMjd = startDate.getTime() / 86400000 + 40587;
    const endMjd = now.getTime() / 86400000 + 40587;
    return { startMjd, endMjd, useFullRange: false, effectiveHistoryDays };
  }, [showHistory, historyDays]);

  const {
    data: historyResponse,
    isLoading: historyLoading,
    error: historyError,
  } = usePointingHistory(startMjd, endMjd);

  useEffect(() => {
    if (historyError) {
      logger.error("Pointing history error:", historyError);
    }
    if (historyResponse) {
      logger.debug("Pointing history loaded:", historyResponse.items.length, "items");
    }
  }, [historyResponse, historyError]);

  // Fetch images for beam footprint visualization (actual sky coverage)
  const { data: imagesResponse, isLoading: imagesLoading } = useImages({
    limit: 1000, // Get recent images for coverage map
  });

  // Filter out synthetic/simulated data (backup filter - API also filters)
  // Synthetic data is identified by timestamps before MJD 60000 (approximately year 2023)
  // Real observations should be from recent dates
  const historyData = useMemo(() => {
    if (!historyResponse?.items) return [];
    // Return all items to ensure test data is visible
    return historyResponse.items;
  }, [historyResponse]);

  const getBeamRadiusDeg = useCallback(
    (img: (typeof imagesResponse)["items"][number]): number | null => {
      if (img.beam_major_arcsec && img.beam_major_arcsec > 0) {
        return img.beam_major_arcsec / 3600 / 2;
      }
      if (img.fov_deg && img.fov_deg > 0) {
        return img.fov_deg / 2;
      }
      if (img.image_size_deg && img.image_size_deg > 0) {
        return img.image_size_deg / 2;
      }
      return null;
    },
    []
  );

  // Filter images that have coordinates and beam information
  const imagesWithCoordinates = useMemo(() => {
    if (!imagesResponse?.items) {
      return [];
    }
    const filtered = imagesResponse.items.filter(
      (img) =>
        img.center_ra_deg !== null &&
        img.center_ra_deg !== undefined &&
        img.center_dec_deg !== null &&
        img.center_dec_deg !== undefined &&
        getBeamRadiusDeg(img) !== null
    );
    return filtered;
  }, [imagesResponse, getBeamRadiusDeg]);

  // Calculate actual data range from filtered data for display
  const actualDataRange = useMemo(() => {
    if (historyData.length === 0) {
      return null;
    }
    const timestamps = historyData.map((item) => item.timestamp);
    return {
      minMjd: Math.min(...timestamps),
      maxMjd: Math.max(...timestamps),
    };
  }, [historyData]);

  const historyRangeLabel = useMemo(() => {
    if (!showHistory) {
      return "";
    }

    if (useFullRange && actualDataRange) {
      return ` (full range: ${actualDataRange.minMjd.toFixed(2)} - ${actualDataRange.maxMjd.toFixed(2)} MJD)`;
    }

    const displayDays = effectiveHistoryDays ?? historyDays;
    if (displayDays) {
      return ` from the last ${displayDays} days`;
    }

    return "";
  }, [showHistory, useFullRange, actualDataRange, effectiveHistoryDays, historyDays]);

  // Update last update time when data changes
  useEffect(() => {
    if (historyData.length > 0 || monitorStatus) {
      setLastUpdate(new Date());
    }
  }, [historyData.length, monitorStatus]);

  // Get current pointing from most recent history entry
  const currentPointing = useMemo(() => {
    if (historyData.length > 0) {
      const latest = historyData[historyData.length - 1];
      return {
        ra: latest.ra_deg,
        dec: latest.dec_deg,
        timestamp: latest.timestamp,
      };
    }
    return null;
  }, [historyData]);

  // Convert RA/Dec to Mollweide projection coordinates
  // This matches the backend's HEALPix Mollweide GSM sky map projection
  const mollweideProjection = useMemo(() => {
    return (ra: number, dec: number): [number, number] => {
      // Convert to radians
      const lambda = ((ra - 180) * Math.PI) / 180; // Longitude (RA centered at 180)
      const phi = (dec * Math.PI) / 180; // Latitude (Dec)

      // Mollweide projection: iteratively solve for theta
      let theta = phi;
      const epsilon = 1e-6;
      const maxIterations = 50;

      for (let i = 0; i < maxIterations; i++) {
        const delta = -(theta + Math.sin(theta) - Math.PI * Math.sin(phi)) / (1 + Math.cos(theta));
        theta += delta;
        if (Math.abs(delta) < epsilon) break;
      }

      // Mollweide projection formulas
      const R = 180 / Math.PI; // Scale factor to match coordinate system
      const x = ((2 * Math.SQRT2) / Math.PI) * lambda * Math.cos(theta / 2) * R;
      const y = Math.SQRT2 * Math.sin(theta / 2) * R;

      return [x, y];
    };
  }, []);

  // Use Mollweide projection for all sky map displays
  const projectPoint = useCallback(
    (ra: number, dec: number) => {
      return mollweideProjection(ra, dec);
    },
    [mollweideProjection]
  );

  // Prepare time series plot data (Dec vs time)
  const { timeSeriesData, timeSeriesLayout } = useMemo(() => {
    const data: Data[] = [];

    if (showHistory && historyData.length > 0) {
      // Convert MJD timestamps to JavaScript dates
      const times = historyData.map((p) => {
        // MJD to Unix timestamp: (MJD - 40587) * 86400000
        const mjd = p.timestamp;
        const unixTime = (mjd - 40587) * 86400000;
        return new Date(unixTime);
      });
      const decs = historyData.map((p) => p.dec_deg);

      // Determine time range for better axis formatting
      const timeRange =
        times.length > 0 ? times[times.length - 1].getTime() - times[0].getTime() : 0;
      const daysRange = timeRange / (1000 * 60 * 60 * 24);

      data.push({
        type: "scatter",
        mode: "lines+markers",
        name: "Declination",
        x: times,
        y: decs,
        line: {
          color: "rgba(144, 202, 249, 0.8)",
          width: 2,
        },
        marker: {
          color: "rgba(144, 202, 249, 0.6)",
          size: 4,
        },
        hovertemplate: "Time: %{x|%Y-%m-%d %H:%M:%S}<br>Dec: %{y:.4f}°<extra></extra>",
      });

      // Configure time axis formatting based on time range
      const xaxisConfig: any = {
        type: "date",
        showgrid: true,
        gridcolor: "rgba(128, 128, 128, 0.2)",
      };

      if (daysRange > 365) {
        // Years: show year-month
        xaxisConfig.tickformat = "%Y-%m";
        xaxisConfig.dtick = "M12"; // Monthly ticks
      } else if (daysRange > 30) {
        // Months: show month name and day
        xaxisConfig.tickformat = "%b %d"; // e.g., "Oct 23"
        xaxisConfig.dtick = "D7"; // Weekly ticks
      } else if (daysRange > 1) {
        // Days: show month name and day
        xaxisConfig.tickformat = "%b %d"; // e.g., "Oct 23"
        xaxisConfig.dtick = "D1"; // Daily ticks
      } else {
        // Hours/minutes: show time
        xaxisConfig.tickformat = "%H:%M:%S";
        xaxisConfig.dtick = 3600000; // Hourly ticks in milliseconds
      }

      const layout: Partial<Layout> = {
        title: {
          text: "Declination vs Time",
          font: { size: 14 },
        },
        xaxis: xaxisConfig,
        yaxis: {
          title: { text: "Declination (degrees)" },
          range: [-90, 90],
          showgrid: true,
          gridcolor: "rgba(128, 128, 128, 0.2)",
        },
        plot_bgcolor: "#1e1e1e",
        paper_bgcolor: "#1e1e1e",
        font: { color: "#ffffff" },
        margin: { l: 70, r: 20, t: 50, b: 60 },
        height: height,
        hovermode: "closest" as any,
      };

      return { timeSeriesData: data, timeSeriesLayout: layout };
    }

    // Empty layout when no data
    const layout: Partial<Layout> = {
      title: {
        text: "Declination vs Time",
        font: { size: 14 },
      },
      xaxis: {
        type: "date",
        showgrid: true,
        gridcolor: "rgba(128, 128, 128, 0.2)",
      },
      yaxis: {
        title: { text: "Declination (degrees)" },
        range: [-90, 90],
        showgrid: true,
        gridcolor: "rgba(128, 128, 128, 0.2)",
      },
      plot_bgcolor: "#1e1e1e",
      paper_bgcolor: "#1e1e1e",
      font: { color: "#ffffff" },
      margin: { l: 70, r: 20, t: 50, b: 60 },
      height: height,
      hovermode: "closest" as any,
    };

    return { timeSeriesData: data, timeSeriesLayout: layout };
  }, [historyData, showHistory, height]);

  // Note: Sky map background now uses Mollweide projection from backend
  // Endpoint: /api/pointing/mollweide-sky-map provides pre-rendered GSM at 1.4 GHz
  // This is more efficient than client-side HEALPix rendering

  // Helper function to check if Aitoff coordinates are within the elliptical boundary
  const isWithinAitoffBoundary = (x: number, y: number): boolean => {
    // Aitoff projection creates an ellipse with semi-major axis ~180 and semi-minor axis ~90
    // The boundary equation: (x/180)^2 + (y/90)^2 <= 1
    // Use a slightly tighter boundary to ensure points are well within the ellipse
    const ellipseCheck = (x / 180) ** 2 + (y / 90) ** 2;
    return ellipseCheck <= 0.98; // Tighter boundary to avoid edge artifacts
  };

  // Prepare Aitoff projection sky map data
  const { skyMapData, skyMapLayout } = useMemo(() => {
    try {
      const data: Data[] = [];

      // Note: Sky map background will be added as a layout image
      // The Mollweide projection is served pre-rendered from the backend
      // This is simpler and more efficient than client-side HEALPix processing

      // Draw pointing history trace
      if (showHistory && historyData.length > 0) {
        const traceXs: number[] = [];
        const traceYs: number[] = [];

        historyData.forEach((point) => {
          const [x, y] = projectPoint(point.ra_deg, point.dec_deg);
          traceXs.push(x);
          traceYs.push(y);
        });

        data.push({
          type: "scatter",
          mode: "lines",
          name: "Pointing Trace",
          x: traceXs,
          y: traceYs,
          line: {
            color: "rgba(100, 181, 246, 0.5)",
            width: 1,
          },
          hoverinfo: "skip" as any,
        });
      }

      // Draw beam footprints (actual sky coverage) from images
      // This shows real observed areas, not telescope pointing paths
      if (showHistory && imagesWithCoordinates.length > 0) {
        // Create arrays to hold all beam footprint points
        const beamFootprints: Data[] = [];

        // Color by observation time (oldest = blue, newest = red)
        const timestamps = imagesWithCoordinates
          .map((img) => (img.created_at ? new Date(img.created_at).getTime() : 0))
          .filter((t) => t > 0);
        const minTime = Math.min(...timestamps);
        const maxTime = Math.max(...timestamps);
        const timeRange = maxTime - minTime || 1;

        // Draw each beam as circle outline
        imagesWithCoordinates.forEach((img, index) => {
          const ra = img.center_ra_deg!;
          const dec = img.center_dec_deg!;
          const beamRadius = getBeamRadiusDeg(img)!;

          // Generate circle points around the beam center
          const numPoints = 32; // Circle resolution
          const circleRAs: number[] = [];
          const circleDecs: number[] = [];

          for (let i = 0; i <= numPoints; i++) {
            const angle = (i / numPoints) * 2 * Math.PI;
            // Approximate circle in RA/Dec (not exact due to spherical geometry, but good enough)
            const deltaRA = (beamRadius * Math.cos(angle)) / Math.cos((dec * Math.PI) / 180);
            const deltaDec = beamRadius * Math.sin(angle);
            circleRAs.push(ra + deltaRA);
            circleDecs.push(dec + deltaDec);
          }

          // Project circle to selected projection coordinates
          const projected = circleRAs.map((r, i) => projectPoint(r, circleDecs[i]));
          const xs = projected.map((p) => p[0]);
          const ys = projected.map((p) => p[1]);

          // Color by time (blue = old, red = new)
          const timestamp = img.created_at ? new Date(img.created_at).getTime() : minTime;
          const normalizedTime = (timestamp - minTime) / timeRange;
          const color = `rgba(${Math.round(255 * normalizedTime)}, ${Math.round(150 * (1 - normalizedTime))}, ${Math.round(255 * (1 - normalizedTime))}, 0.8)`;

          beamFootprints.push({
            type: "scatter",
            mode: "lines",
            x: xs,
            y: ys,
            line: {
              color: color,
              width: 1.5,
            },
            hovertemplate:
              `<b>Beam Footprint</b><br>` +
              `Center RA: ${ra.toFixed(3)}°<br>` +
              `Center Dec: ${dec.toFixed(3)}°<br>` +
              `Beam Diameter: ${(beamRadius * 2).toFixed(2)}°<br>` +
              `Time: ${img.created_at || "N/A"}<extra></extra>`,
            showlegend: false,
            hoverinfo: "text" as any,
          });
        });

        data.push(...beamFootprints);
      }

      // Add current pointing position
      if (currentPointing) {
        const [x, y] = projectPoint(currentPointing.ra, currentPointing.dec);
        data.push({
          type: "scatter",
          mode: "markers",
          name: "Current Pointing",
          x: [x],
          y: [y],
          marker: {
            color: "#4caf50",
            size: 15,
            symbol: "circle",
            line: {
              color: "#ffffff",
              width: 2,
            },
          },
          hovertemplate:
            "<b>Current Pointing</b><br>RA: %{customdata[0]:.4f}°<br>Dec: %{customdata[1]:.4f}°<extra></extra>",
          customdata: [[currentPointing.ra, currentPointing.dec]],
        });
      }

      // Add coordinate grid lines for reference (denser grid with labels)
      const gridLines: Data[] = [];
      const gridLabels: any[] = [];

      // RA grid lines (every 30 degrees - twice as dense as before)
      for (let ra = 0; ra < 360; ra += 30) {
        const decs = Array.from({ length: 91 }, (_, i) => -90 + i * 2);
        const ras = decs.map(() => ra);
        const projected = ras.map((r, i) => projectPoint(r, decs[i]));
        gridLines.push({
          type: "scatter",
          mode: "lines",
          x: projected.map((p) => p[0]),
          y: projected.map((p) => p[1]),
          line: { color: "rgba(255, 255, 255, 0.3)", width: 1, dash: "dot" },
          showlegend: false,
          hoverinfo: "skip" as any,
        });

        // Add RA label at the equator (dec=0)
        const [labelX, labelY] = projectPoint(ra, 0);
        gridLabels.push({
          x: labelX,
          y: labelY + 8, // Offset slightly above the equator
          text: `${ra}°`,
          showarrow: false,
          font: { size: 10, color: "rgba(255, 255, 255, 0.6)" },
          xanchor: "center",
          yanchor: "bottom",
        });
      }

      // Dec grid lines (every 15 degrees - twice as dense as before)
      for (let dec = -90; dec <= 90; dec += 15) {
        const ras = Array.from({ length: 181 }, (_, i) => i * 2);
        const decs = ras.map(() => dec);
        const projected = ras.map((r, i) => projectPoint(r, decs[i]));
        gridLines.push({
          type: "scatter",
          mode: "lines",
          x: projected.map((p) => p[0]),
          y: projected.map((p) => p[1]),
          line: { color: "rgba(255, 255, 255, 0.3)", width: 1, dash: "dot" },
          showlegend: false,
          hoverinfo: "skip" as any,
        });

        // Add Dec label at RA=180 (left side)
        if (dec !== 0) {
          // Skip 0° to avoid overlap with RA labels
          const [labelX, labelY] = projectPoint(180, dec);
          gridLabels.push({
            x: labelX - 8, // Offset to the left
            y: labelY,
            text: `${dec}°`,
            showarrow: false,
            font: { size: 10, color: "rgba(255, 255, 255, 0.6)" },
            xanchor: "right",
            yanchor: "middle",
          });
        }
      }

      // Mollweide projection axis ranges
      const xRange = [-162, 162];
      const yRange = [-81, 81];
      const yScaleRatio = 1;

      const layout: Partial<Layout> = {
        title: {
          text: "Sky Map (Mollweide - HEALPix GSM)",
          font: { size: 14 },
        },
        annotations: gridLabels,
        xaxis: {
          title: { text: "" },
          showgrid: false,
          zeroline: false,
          showticklabels: false,
          range: xRange,
        },
        yaxis: {
          title: { text: "" },
          showgrid: false,
          zeroline: false,
          showticklabels: false,
          range: yRange,
          scaleanchor: "x" as any,
          scaleratio: yScaleRatio,
        },
        plot_bgcolor: "#1e1e1e",
        paper_bgcolor: "#1e1e1e",
        font: { color: "#ffffff" },
        margin: { l: 20, r: 20, t: 50, b: 20 },
        height: height,
        hovermode: "closest" as any,
        showlegend: false,
        // Add Mollweide projection background image from backend
        images: enableSkyMapBackground
          ? [
              {
                source:
                  "/api/pointing/mollweide-sky-map?frequency_mhz=1400&cmap=inferno&width=1200&height=600",
                xref: "x",
                yref: "y",
                // Mollweide projection coordinate ranges (with R = 180/π ≈ 57.3)
                // X: ±2√2 * R ≈ ±162
                // Y: ±√2 * R ≈ ±81
                x: -162,
                y: -81,
                sizex: 324, // 2 * 162
                sizey: 162, // 2 * 81
                sizing: "stretch",
                opacity: 0.8,
                layer: "below",
              },
            ]
          : [],
      };

      return { skyMapData: [...data, ...gridLines], skyMapLayout: layout };
    } catch (error) {
      console.error("Error in skyMapData useMemo:", error);
      // Try to generate at least grid lines as fallback
      try {
        const gridLines: Data[] = [];
        const gridLabels: any[] = [];

        // RA grid lines (every 30 degrees - twice as dense)
        for (let ra = 0; ra < 360; ra += 30) {
          const decs = Array.from({ length: 91 }, (_, i) => -90 + i * 2);
          const ras = decs.map(() => ra);
          const projected = ras.map((r, i) => projectPoint(r, decs[i]));
          gridLines.push({
            type: "scatter",
            mode: "lines",
            x: projected.map((p) => p[0]),
            y: projected.map((p) => p[1]),
            line: { color: "rgba(255, 255, 255, 0.3)", width: 1, dash: "dot" },
            showlegend: false,
            hoverinfo: "skip" as any,
          });

          // Add RA label at the equator (dec=0)
          const [labelX, labelY] = projectPoint(ra, 0);
          gridLabels.push({
            x: labelX,
            y: labelY + 8,
            text: `${ra}°`,
            showarrow: false,
            font: { size: 10, color: "rgba(255, 255, 255, 0.6)" },
            xanchor: "center",
            yanchor: "bottom",
          });
        }

        // Dec grid lines (every 15 degrees - twice as dense)
        for (let dec = -90; dec <= 90; dec += 15) {
          const ras = Array.from({ length: 181 }, (_, i) => i * 2);
          const decs = ras.map(() => dec);
          const projected = ras.map((r, i) => projectPoint(r, decs[i]));
          gridLines.push({
            type: "scatter",
            mode: "lines",
            x: projected.map((p) => p[0]),
            y: projected.map((p) => p[1]),
            line: { color: "rgba(255, 255, 255, 0.3)", width: 1, dash: "dot" },
            showlegend: false,
            hoverinfo: "skip" as any,
          });

          // Add Dec label at RA=180 (left side)
          if (dec !== 0) {
            const [labelX, labelY] = projectPoint(180, dec);
            gridLabels.push({
              x: labelX - 8,
              y: labelY,
              text: `${dec}°`,
              showarrow: false,
              font: { size: 10, color: "rgba(255, 255, 255, 0.6)" },
              xanchor: "right",
              yanchor: "middle",
            });
          }
        }

        const fallbackLayout: Partial<Layout> = {
          title: {
            text: "Sky Map",
            font: { size: 14 },
          },
          annotations: gridLabels,
          xaxis: {
            title: { text: "" },
            showgrid: false,
            zeroline: false,
            showticklabels: false,
            range: [-180, 180],
          },
          yaxis: {
            title: { text: "" },
            showgrid: false,
            zeroline: false,
            showticklabels: false,
            range: [-90, 90],
            scaleanchor: "x" as any,
            scaleratio: 0.5,
          },
          plot_bgcolor: "#1e1e1e",
          paper_bgcolor: "#1e1e1e",
          font: { color: "#ffffff" },
          margin: { l: 20, r: 20, t: 50, b: 20 },
          height: height,
          hovermode: "closest" as any,
          showlegend: false,
        };
        return { skyMapData: gridLines, skyMapLayout: fallbackLayout };
      } catch (fallbackError) {
        console.error("Error generating fallback grid lines:", fallbackError);
        // Last resort: return empty but valid structure
        const fallbackLayout: Partial<Layout> = {
          title: {
            text: "Sky Map",
            font: { size: 14 },
          },
          xaxis: {
            title: { text: "" },
            showgrid: false,
            zeroline: false,
            showticklabels: false,
            range: [-180, 180],
          },
          yaxis: {
            title: { text: "" },
            showgrid: false,
            zeroline: false,
            showticklabels: false,
            range: [-90, 90],
            scaleanchor: "x" as any,
            scaleratio: 0.5,
          },
          plot_bgcolor: "#1e1e1e",
          paper_bgcolor: "#1e1e1e",
          font: { color: "#ffffff" },
          margin: { l: 20, r: 20, t: 50, b: 20 },
          height: height,
          hovermode: "closest" as any,
          showlegend: false,
        };
        return { skyMapData: [], skyMapLayout: fallbackLayout };
      }
    }
  }, [
    currentPointing,
    historyData,
    showHistory,
    height,
    projectPoint,
    enableSkyMapBackground,
    imagesWithCoordinates,
    getBeamRadiusDeg,
  ]);

  if (statusLoading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight={height}>
          <CircularProgress />
        </Box>
      </Paper>
    );
  }

  const isHealthy = monitorStatus?.healthy ?? false;
  const isRunning = monitorStatus?.running ?? false;

  return (
    <Paper sx={{ p: 2 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">Pointing Status</Typography>
        <Stack direction="row" spacing={2} alignItems="center">
          <Chip
            icon={<PointIcon />}
            label={isRunning ? "Monitoring" : "Stopped"}
            color={isRunning ? "success" : "default"}
            size="small"
          />
          {!isHealthy && <Chip label="Unhealthy" color="error" size="small" />}
          <Tooltip title={`Last updated: ${lastUpdate.toLocaleTimeString()}`}>
            <RefreshIcon fontSize="small" sx={{ opacity: 0.6 }} />
          </Tooltip>
        </Stack>
      </Box>

      {!isRunning && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Pointing monitor is not running. Current position may be outdated.
        </Alert>
      )}

      {!isHealthy && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Pointing monitor health check failed:{" "}
          {monitorStatus?.issues?.join(", ") || "Unknown error"}
        </Alert>
      )}

      {historyLoading ? (
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight={height}
          border="1px dashed rgba(255, 255, 255, 0.2)"
          borderRadius={1}
        >
          <Stack spacing={2} alignItems="center">
            <CircularProgress size={40} />
            <Typography color="text.secondary">Loading pointing history...</Typography>
            {monitorStatus && (
              <Typography variant="caption" color="text.secondary">
                Monitor status: {monitorStatus.running ? "Running" : "Stopped"}
              </Typography>
            )}
          </Stack>
        </Box>
      ) : currentPointing ? (
        <>
          <Box mb={2}>
            <Stack direction="row" spacing={3} flexWrap="wrap">
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Current RA
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  {currentPointing.ra.toFixed(4)}°
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Current Dec
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  {currentPointing.dec.toFixed(4)}°
                </Typography>
              </Box>
              {monitorStatus?.metrics && (
                <>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Files Processed
                    </Typography>
                    <Typography variant="body2">{monitorStatus.metrics.files_processed}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Success Rate
                    </Typography>
                    <Typography variant="body2">
                      {monitorStatus.metrics.success_rate_percent.toFixed(1)}%
                    </Typography>
                  </Box>
                </>
              )}
            </Stack>
          </Box>

          {timeSeriesData.length > 0 || skyMapData.length > 0 ? (
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <PlotlyLazy
                  data={timeSeriesData}
                  layout={timeSeriesLayout}
                  config={{
                    responsive: true,
                    displayModeBar: true,
                    modeBarButtonsToRemove: ["lasso2d", "select2d"],
                    displaylogo: false,
                  }}
                  style={{ width: "100%" }}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <PlotlyLazy
                  data={skyMapData}
                  layout={skyMapLayout}
                  config={{
                    responsive: true,
                    displayModeBar: true,
                    modeBarButtonsToRemove: ["lasso2d", "select2d"],
                    displaylogo: false,
                  }}
                  style={{ width: "100%" }}
                />
              </Grid>
            </Grid>
          ) : (
            <Box
              display="flex"
              justifyContent="center"
              alignItems="center"
              minHeight={height}
              border="1px dashed rgba(255, 255, 255, 0.2)"
              borderRadius={1}
            >
              <Typography color="text.secondary">No pointing data available</Typography>
            </Box>
          )}
        </>
      ) : (
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight={height}
          border="1px dashed rgba(255, 255, 255, 0.2)"
          borderRadius={1}
        >
          <Stack spacing={2} alignItems="center">
            <Typography color="text.secondary">No pointing data available</Typography>
            {monitorStatus && (
              <Typography variant="caption" color="text.secondary">
                Monitor status: {monitorStatus.running ? "Running" : "Stopped"}
              </Typography>
            )}
          </Stack>
        </Box>
      )}

      {showHistory && historyData.length > 0 && (
        <Box mt={2}>
          <Typography variant="caption" color="text.secondary">
            Showing {historyData.length} pointing measurements
            {historyRangeLabel}
          </Typography>
        </Box>
      )}
    </Paper>
  );
}
