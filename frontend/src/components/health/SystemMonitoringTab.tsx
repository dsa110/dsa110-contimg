import React, { useMemo } from "react";
import {
  Box,
  CircularProgress,
  Grid,
  Card,
  CardHeader,
  CardContent,
  Stack,
  Typography,
} from "@mui/material";
import { useSystemMetrics } from "../../api/queries";
import { useMetricHistory } from "../../hooks/useMetricHistory";
import { StatusIndicator } from "../StatusIndicator";
import { MetricWithSparkline } from "../Sparkline";
import { PlotlyLazy } from "../PlotlyLazy";
import type { Data, Layout } from "../PlotlyLazy";
import { SystemMetricsPanel } from "../metrics/SystemMetricsPanel";

export const SystemMonitoringTab: React.FC = () => {
  const { data: metrics, isLoading: metricsLoading } = useSystemMetrics();

  // Track metric history for sparklines
  const cpuHistory = useMetricHistory(metrics?.cpu_percent);
  const memHistory = useMetricHistory(metrics?.mem_percent);

  // Use new disks array format - track both / (SSD) and /data/ (HDD)
  const ssdDisk = metrics?.disks?.find((d) => d.mount_point.startsWith("/ (SSD)"));
  const hddDisk = metrics?.disks?.find((d) => d.mount_point.startsWith("/data/"));
  const ssdDiskHistory = useMetricHistory(ssdDisk?.percent);
  const hddDiskHistory = useMetricHistory(hddDisk?.percent);

  const loadHistory = useMetricHistory(metrics?.load_1);

  // Prepare system metrics plot data
  const metricsPlotData = useMemo(() => {
    if (!metrics) return { data: [], layout: {} };

    const data: Data[] = [
      {
        type: "scatter",
        mode: "lines",
        name: "CPU %",
        x: [new Date()],
        y: [metrics.cpu_percent],
        line: { color: "#90caf9" },
      },
      {
        type: "scatter",
        mode: "lines",
        name: "Memory %",
        x: [new Date()],
        y: [metrics.mem_percent],
        line: { color: "#a5d6a7" },
      },
    ];

    const layout: Partial<Layout> = {
      title: "System Resource Usage",
      xaxis: { title: "Time" },
      yaxis: { title: "Usage (%)", range: [0, 100] },
      hovermode: "closest",
      template: "plotly_dark",
    };

    return { data, layout };
  }, [metrics]);

  if (metricsLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Grid container spacing={3}>
      {/* Current Metrics */}
      <Grid size={12}>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatusIndicator
              value={metrics?.cpu_percent || 0}
              thresholds={{ good: 70, warning: 50 }}
              label="CPU Usage"
              unit="%"
              size="medium"
              showTrend={cpuHistory.length > 1}
              previousValue={cpuHistory.length > 1 ? cpuHistory[cpuHistory.length - 2] : undefined}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatusIndicator
              value={metrics?.mem_percent || 0}
              thresholds={{ good: 80, warning: 60 }}
              label="Memory Usage"
              unit="%"
              size="medium"
              showTrend={memHistory.length > 1}
              previousValue={memHistory.length > 1 ? memHistory[memHistory.length - 2] : undefined}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatusIndicator
              value={ssdDisk?.percent ?? 0}
              thresholds={{ good: 75, warning: 90 }}
              label="SSD (root)"
              unit="%"
              size="medium"
              showTrend={ssdDiskHistory.length > 1}
              previousValue={
                ssdDiskHistory.length > 1 ? ssdDiskHistory[ssdDiskHistory.length - 2] : undefined
              }
            />
          </Grid>
          <Grid
            size={{ xs: 12, sm: 6, md: 3 }}
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <StatusIndicator
              value={hddDisk?.percent ?? 0}
              thresholds={{ good: 75, warning: 90 }}
              label="HDD (/data/)"
              unit="%"
              size="medium"
              showTrend={hddDiskHistory.length > 1}
              previousValue={
                hddDiskHistory.length > 1 ? hddDiskHistory[hddDiskHistory.length - 2] : undefined
              }
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <MetricWithSparkline
              label="Load Average (1m)"
              value={metrics?.load_1?.toFixed(2) || "N/A"}
              color="info"
              size="medium"
              sparklineData={loadHistory.length > 1 ? loadHistory : undefined}
            />
          </Grid>
        </Grid>
      </Grid>

      {/* Metrics Plot */}
      {metricsPlotData.data.length > 0 && (
        <Grid size={12}>
          <Card>
            <CardHeader title="Resource Usage Over Time" />
            <CardContent>
              <PlotlyLazy
                data={metricsPlotData.data}
                layout={metricsPlotData.layout}
                style={{ width: "100%", height: "400px" }}
              />
            </CardContent>
          </Card>
        </Grid>
      )}

      {/* Grafana-style System Metrics Panel */}
      <Grid size={12}>
        <SystemMetricsPanel />
      </Grid>

      {/* Detailed Metrics */}
      <Grid size={{ xs: 12, md: 6 }}>
        <Card>
          <CardHeader title="Memory Details" />
          <CardContent>
            <Stack spacing={2}>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Total Memory
                </Typography>
                <Typography variant="h6">
                  {metrics?.mem_total
                    ? `${(metrics.mem_total / 1024 / 1024 / 1024).toFixed(2)} GB`
                    : "N/A"}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Used Memory
                </Typography>
                <Typography variant="h6">
                  {metrics?.mem_used
                    ? `${(metrics.mem_used / 1024 / 1024 / 1024).toFixed(2)} GB`
                    : "N/A"}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Load Averages
                </Typography>
                <Typography variant="body1">1m: {metrics?.load_1?.toFixed(2) || "N/A"}</Typography>
                <Typography variant="body1">5m: {metrics?.load_5?.toFixed(2) || "N/A"}</Typography>
                <Typography variant="body1">
                  15m: {metrics?.load_15?.toFixed(2) || "N/A"}
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Grid>

      <Grid size={{ xs: 12, md: 6 }}>
        <Card>
          <CardHeader title="Disk Details - SSD (root)" />
          <CardContent>
            <Stack spacing={2}>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Total Space
                </Typography>
                <Typography variant="h6">
                  {ssdDisk?.total ? `${(ssdDisk.total / 1024 / 1024 / 1024).toFixed(2)} GB` : "N/A"}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Used Space
                </Typography>
                <Typography variant="h6">
                  {ssdDisk?.used ? `${(ssdDisk.used / 1024 / 1024 / 1024).toFixed(2)} GB` : "N/A"}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Available Space
                </Typography>
                <Typography variant="h6">
                  {ssdDisk?.free ? `${(ssdDisk.free / 1024 / 1024 / 1024).toFixed(2)} GB` : "N/A"}
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>
        <Card sx={{ mt: 2 }}>
          <CardHeader title="Disk Details - HDD (/data/)" />
          <CardContent>
            <Stack spacing={2}>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Total Space
                </Typography>
                <Typography variant="h6">
                  {hddDisk?.total ? `${(hddDisk.total / 1024 / 1024 / 1024).toFixed(2)} GB` : "N/A"}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Used Space
                </Typography>
                <Typography variant="h6">
                  {hddDisk?.used ? `${(hddDisk.used / 1024 / 1024 / 1024).toFixed(2)} GB` : "N/A"}
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Available Space
                </Typography>
                <Typography variant="h6">
                  {hddDisk?.free ? `${(hddDisk.free / 1024 / 1024 / 1024).toFixed(2)} GB` : "N/A"}
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};
