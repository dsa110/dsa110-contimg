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
} from "@mui/material";
import { RadioButtonChecked as PointIcon, Refresh as RefreshIcon } from "@mui/icons-material";
import { PlotlyLazy } from "./PlotlyLazy";
import type { Data, Layout } from "./PlotlyLazy";
import { usePointingMonitorStatus, usePointingHistory } from "../api/queries";

interface PointingVisualizationProps {
  height?: number;
  showHistory?: boolean;
  historyDays?: number;
}

export default function PointingVisualization({
  height = 500,
  showHistory = true,
  historyDays = 7,
}: PointingVisualizationProps) {
  const { data: monitorStatus, isLoading: statusLoading } = usePointingMonitorStatus();
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Calculate MJD range for history
  const { startMjd, endMjd } = useMemo(() => {
    if (!showHistory) return { startMjd: 0, endMjd: 0 };
    const now = new Date();
    const startDate = new Date(now.getTime() - historyDays * 24 * 60 * 60 * 1000);
    // Convert to MJD (Unix epoch to MJD offset is 40587)
    const startMjd = startDate.getTime() / 86400000 + 40587;
    const endMjd = now.getTime() / 86400000 + 40587;
    return { startMjd, endMjd };
  }, [showHistory, historyDays]);

  const { data: historyResponse, isLoading: historyLoading } = usePointingHistory(startMjd, endMjd);

  const historyData = historyResponse?.items || [];

  // Update last update time when data changes
  useEffect(() => {
    if (historyData.length > 0 || monitorStatus) {
      setLastUpdate(new Date());
    }
  }, [historyData, monitorStatus]);

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

  // Prepare plot data
  const { plotData, layout } = useMemo(() => {
    const data: Data[] = [];

    // Add historical trail
    if (showHistory && historyData.length > 0) {
      const ras = historyData.map((p) => p.ra_deg);
      const decs = historyData.map((p) => p.dec_deg);

      // Use degrees directly for more intuitive display
      data.push({
        type: "scatter",
        mode: "lines",
        name: "Pointing History",
        x: ras,
        y: decs,
        line: {
          color: "rgba(144, 202, 249, 0.5)",
          width: 2,
        },
        hovertemplate: "RA: %{x:.2f}°<br>Dec: %{y:.2f}°<extra></extra>",
      });

      // Add trail markers (sparse for performance)
      const step = Math.max(1, Math.floor(historyData.length / 20));
      const sparseRas = ras.filter((_, i) => i % step === 0);
      const sparseDecs = decs.filter((_, i) => i % step === 0);

      data.push({
        type: "scatter",
        mode: "markers",
        name: "Historical Points",
        x: sparseRas,
        y: sparseDecs,
        marker: {
          color: "rgba(144, 202, 249, 0.3)",
          size: 4,
        },
        hovertemplate: "RA: %{x:.2f}°<br>Dec: %{y:.2f}°<extra></extra>",
        showlegend: false,
      });
    }

    // Add current pointing position
    if (currentPointing) {
      data.push({
        type: "scatter",
        mode: "markers",
        name: "Current Pointing",
        x: [currentPointing.ra],
        y: [currentPointing.dec],
        marker: {
          color: "#4caf50",
          size: 15,
          symbol: "circle",
          line: {
            color: "#ffffff",
            width: 2,
          },
        },
        hovertemplate: "<b>Current Pointing</b><br>RA: %{x:.4f}°<br>Dec: %{y:.4f}°<extra></extra>",
      });
    }

    // Create layout with degrees
    const plotLayout: Partial<Layout> = {
      title: {
        text: "Telescope Pointing",
        font: { size: 16 },
      },
      xaxis: {
        title: { text: "Right Ascension (degrees)" },
        range: [0, 360],
        showgrid: true,
        gridcolor: "rgba(128, 128, 128, 0.2)",
        tickmode: "linear",
        tick0: 0,
        dtick: 30,
      },
      yaxis: {
        title: { text: "Declination (degrees)" },
        range: [-90, 90],
        showgrid: true,
        gridcolor: "rgba(128, 128, 128, 0.2)",
        tickmode: "linear",
        tick0: -90,
        dtick: 30,
      },
      plot_bgcolor: "#1e1e1e",
      paper_bgcolor: "#1e1e1e",
      font: { color: "#ffffff" },
      legend: {
        x: 0.02,
        y: 0.98,
        bgcolor: "rgba(0, 0, 0, 0.5)",
        bordercolor: "rgba(255, 255, 255, 0.2)",
        borderwidth: 1,
      },
      margin: { l: 80, r: 20, t: 60, b: 60 },
      height,
      hovermode: "closest" as any,
    };

    return { plotData: data, layout: plotLayout };
  }, [currentPointing, historyData, showHistory, height]);

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

      {currentPointing ? (
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

          {plotData.length > 0 ? (
            <PlotlyLazy
              data={plotData}
              layout={layout}
              config={{
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ["lasso2d", "select2d"],
                displaylogo: false,
              }}
              style={{ width: "100%" }}
            />
          ) : (
            <Box
              display="flex"
              justifyContent="center"
              alignItems="center"
              minHeight={height}
              border="1px dashed rgba(255, 255, 255, 0.2)"
              borderRadius={1}
            >
              <Typography color="text.secondary">
                {historyLoading ? "Loading pointing history..." : "No pointing data available"}
              </Typography>
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
            <CircularProgress size={40} />
            <Typography color="text.secondary">Waiting for pointing data...</Typography>
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
            Showing {historyData.length} pointing measurements from the last {historyDays} days
          </Typography>
        </Box>
      )}
    </Paper>
  );
}
