/**
 * Pointing Visualization Component
 * Live sky map showing DSA-110 telescope pointing position and history
 */
import { useMemo, useEffect, useState } from "react";
import {
  Paper,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Chip,
  Stack,
  Tooltip,
  Grid,
} from "@mui/material";
import { RadioButtonChecked as PointIcon, Refresh as RefreshIcon } from "@mui/icons-material";
import { PlotlyLazy } from "./PlotlyLazy";
import type { Data, Layout } from "./PlotlyLazy";
import { usePointingMonitorStatus, usePointingHistory } from "../api/queries";

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
  enableSkyMapBackground = true, // Enable by default
}: PointingVisualizationProps) {
  const { data: monitorStatus, isLoading: statusLoading } = usePointingMonitorStatus();
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Calculate MJD range for history - use full range if historyDays is null/undefined or very large
  const { startMjd, endMjd, useFullRange } = useMemo(() => {
    if (!showHistory) return { startMjd: 0, endMjd: 0, useFullRange: false };

    // If historyDays is very large (>1000) or undefined, query full range
    // Use a wide range that should capture all data (MJD 0 to 100000 covers ~274 years)
    if (!historyDays || historyDays > 1000) {
      return { startMjd: 0, endMjd: 100000, useFullRange: true };
    }

    const now = new Date();
    const startDate = new Date(now.getTime() - historyDays * 24 * 60 * 60 * 1000);
    // Convert to MJD (Unix epoch to MJD offset is 40587)
    const startMjd = startDate.getTime() / 86400000 + 40587;
    const endMjd = now.getTime() / 86400000 + 40587;
    return { startMjd, endMjd, useFullRange: false };
  }, [showHistory, historyDays]);

  const { data: historyResponse, isLoading: historyLoading } = usePointingHistory(startMjd, endMjd);

  // Filter out synthetic/simulated data (backup filter - API also filters)
  // Synthetic data is identified by timestamps before MJD 60000 (approximately year 2023)
  // Real observations should be from recent dates
  const historyData = useMemo(() => {
    if (!historyResponse?.items) return [];
    // Filter out synthetic/simulated data (MJD < 60000 = before ~2023)
    // This is a backup filter - the API endpoint also filters synthetic data
    const MIN_VALID_MJD = 60000;
    return historyResponse.items.filter((item) => item.timestamp >= MIN_VALID_MJD);
  }, [historyResponse]);

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

  // Convert RA/Dec to Aitoff projection coordinates
  const aitoffProjection = useMemo(() => {
    return (ra: number, dec: number): [number, number] => {
      // Convert to radians
      const lambda = ((ra - 180) * Math.PI) / 180; // Longitude (RA centered at 180)
      const phi = (dec * Math.PI) / 180; // Latitude (Dec)

      // Aitoff projection formulas
      const alpha = Math.acos(Math.cos(phi) * Math.cos(lambda / 2));
      const sinc = alpha !== 0 ? Math.sin(alpha) / alpha : 1;
      const R = 180 / Math.PI; // Scale factor

      const x = ((2 * Math.cos(phi) * Math.sin(lambda / 2)) / sinc) * R;
      const y = (Math.sin(phi) / sinc) * R;

      return [x, y];
    };
  }, []);

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
        title: { text: "Time" },
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
        title: { text: "Time" },
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

  // Generate sky map background as heatmap data (instead of image overlay)
  const generateSkyMapHeatmap = useMemo(() => {
    if (!enableSkyMapBackground) return null;

    // Generate a grid of Aitoff coordinates for the heatmap
    const resolution = 90; // Grid resolution (balance between quality and performance)
    const xStep = 360 / resolution;
    const yStep = 180 / resolution;

    const x: number[] = [];
    const y: number[] = [];
    const z: number[][] = [];

    // Generate coordinate arrays and brightness values
    for (let i = 0; i <= resolution; i++) {
      const aitoffY = -90 + i * yStep;
      y.push(aitoffY);
      const row: number[] = [];

      for (let j = 0; j <= resolution; j++) {
        const aitoffX = -180 + j * xStep;
        if (i === 0) {
          x.push(aitoffX);
        }

        // Convert Aitoff coordinates back to approximate RA/Dec for brightness calculation
        // Inverse Aitoff: approximate conversion
        const ra_deg = aitoffX + 180;
        const dec_deg = aitoffY;

        // Galactic center is at RA ~266°, Dec ~-29°
        const gal_center_ra = 266.0;
        const gal_center_dec = -29.0;

        // Distance from galactic center (handle RA wrap-around)
        const ra_diff = ((ra_deg - gal_center_ra + 180) % 360) - 180;
        const dec_diff = dec_deg - gal_center_dec;
        const dist_from_center = Math.sqrt(ra_diff ** 2 + dec_diff ** 2);

        // Distance from galactic plane (simplified as a band)
        const plane_dec = -29.0 + 20 * Math.sin((ra_deg * Math.PI) / 180);
        const dist_from_plane = Math.abs(dec_deg - plane_dec);

        // Calculate brightness (matching backend logic)
        const center_brightness = Math.max(0, 1.0 - dist_from_center / 80.0);
        const plane_brightness = Math.max(0, 0.8 - dist_from_plane / 40.0);
        const brightness = 0.2 + center_brightness * 0.6 + plane_brightness * 0.4;
        const normalizedBrightness = Math.min(1.0, Math.pow(brightness, 0.8));

        row.push(normalizedBrightness);
      }
      z.push(row);
    }

    return { x, y, z };
  }, [enableSkyMapBackground]);

  // Prepare Aitoff projection sky map data
  const { skyMapData, skyMapLayout } = useMemo(() => {
    const data: Data[] = [];

    // Add sky map background as heatmap (if enabled)
    if (generateSkyMapHeatmap) {
      data.push({
        type: "heatmap",
        x: generateSkyMapHeatmap.x,
        y: generateSkyMapHeatmap.y,
        z: generateSkyMapHeatmap.z,
        colorscale: [
          [0, "rgb(20, 20, 20)"],
          [0.3, "rgb(40, 40, 60)"],
          [0.6, "rgb(80, 80, 120)"],
          [1, "rgb(150, 150, 200)"],
        ],
        showscale: false,
        hoverinfo: "skip" as any,
        opacity: 0.6,
      });
    }

    if (showHistory && historyData.length > 0) {
      // Project all points to Aitoff coordinates
      const projectedPoints = historyData.map((p) => {
        const [x, y] = aitoffProjection(p.ra_deg, p.dec_deg);
        return { x, y, ra: p.ra_deg, dec: p.dec_deg };
      });

      const xs = projectedPoints.map((p) => p.x);
      const ys = projectedPoints.map((p) => p.y);

      // Historical trail
      data.push({
        type: "scatter",
        mode: "lines",
        name: "Pointing History",
        x: xs,
        y: ys,
        line: {
          color: "rgba(144, 202, 249, 0.5)",
          width: 2,
        },
        hovertemplate: "RA: %{customdata[0]:.2f}°<br>Dec: %{customdata[1]:.2f}°<extra></extra>",
        customdata: historyData.map((p) => [p.ra_deg, p.dec_deg]),
      });

      // Sparse markers for performance
      const step = Math.max(1, Math.floor(historyData.length / 20));
      const sparseXs = xs.filter((_, i) => i % step === 0);
      const sparseYs = ys.filter((_, i) => i % step === 0);
      const sparseData = historyData.filter((_, i) => i % step === 0);

      data.push({
        type: "scatter",
        mode: "markers",
        name: "Historical Points",
        x: sparseXs,
        y: sparseYs,
        marker: {
          color: "rgba(144, 202, 249, 0.3)",
          size: 4,
        },
        hovertemplate: "RA: %{customdata[0]:.2f}°<br>Dec: %{customdata[1]:.2f}°<extra></extra>",
        customdata: sparseData.map((p) => [p.ra_deg, p.dec_deg]),
        showlegend: false,
      });
    }

    // Add current pointing position
    if (currentPointing) {
      const [x, y] = aitoffProjection(currentPointing.ra, currentPointing.dec);
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

    // Add coordinate grid lines for reference (sparse for performance)
    const gridLines: Data[] = [];
    // RA grid lines (every 60 degrees for performance)
    for (let ra = 0; ra < 360; ra += 60) {
      const decs = Array.from({ length: 91 }, (_, i) => -90 + i * 2); // Sparse sampling
      const ras = decs.map(() => ra);
      const projected = ras.map((r, i) => aitoffProjection(r, decs[i]));
      gridLines.push({
        type: "scatter",
        mode: "lines",
        x: projected.map((p) => p[0]),
        y: projected.map((p) => p[1]),
        line: { color: "rgba(128, 128, 128, 0.15)", width: 1, dash: "dot" },
        showlegend: false,
        hoverinfo: "skip" as any,
      });
    }
    // Dec grid lines (every 30 degrees)
    for (let dec = -90; dec <= 90; dec += 30) {
      const ras = Array.from({ length: 181 }, (_, i) => i * 2); // Sparse sampling
      const decs = ras.map(() => dec);
      const projected = ras.map((r, i) => aitoffProjection(r, decs[i]));
      gridLines.push({
        type: "scatter",
        mode: "lines",
        x: projected.map((p) => p[0]),
        y: projected.map((p) => p[1]),
        line: { color: "rgba(128, 128, 128, 0.15)", width: 1, dash: "dot" },
        showlegend: false,
        hoverinfo: "skip" as any,
      });
    }

    const layout: Partial<Layout> = {
      title: {
        text: "Sky Map (Aitoff Projection)",
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

    return { skyMapData: [...gridLines, ...data], skyMapLayout: layout };
  }, [currentPointing, historyData, showHistory, height, aitoffProjection, generateSkyMapHeatmap]);

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
        <Stack direction="row" spacing={1} alignItems="center">
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
            {useFullRange && actualDataRange
              ? ` (full range: ${actualDataRange.minMjd.toFixed(2)} - ${actualDataRange.maxMjd.toFixed(2)} MJD)`
              : ` from the last ${historyDays} days`}
          </Typography>
        </Box>
      )}
    </Paper>
  );
}
